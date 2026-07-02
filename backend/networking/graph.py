"""Graph traversal utilities over the networking relationship tables.

Pure ORM, no I/O. Functions return plain dicts/lists so they can be reused by
both REST views and agent tools without serialiser leakage."""

from __future__ import annotations

from collections import defaultdict

from django.db.models import Q

from jobs.models import Company

from .models import (
    Contact,
    ContactEmployment,
    ContactRelationship,
    ContactRelationshipKind,
    CompanyRelationship,
)


# ---------------------------------------------------------------------------
# Inference: derive colleague edges from overlapping employments
# ---------------------------------------------------------------------------

def infer_colleague_relationships(*, user, contact: Contact) -> int:
    """For each employment on `contact`, find other contacts of the same user
    whose employment at the same company overlaps. Create symmetric
    `colleague` ContactRelationship rows (inferred=True). Idempotent."""

    created = 0
    employments = list(ContactEmployment.objects.filter(contact=contact))
    if not employments:
        return 0

    company_ids = {e.company_id for e in employments}
    candidates = (
        ContactEmployment.objects
        .filter(company_id__in=company_ids, contact__user=user)
        .exclude(contact_id=contact.id)
        .select_related('contact')
    )

    for mine in employments:
        for theirs in candidates:
            if theirs.company_id != mine.company_id:
                continue
            if not mine.overlaps(theirs):
                continue
            for a, b in ((contact, theirs.contact), (theirs.contact, contact)):
                _, was_created = ContactRelationship.objects.get_or_create(
                    user=user,
                    from_contact=a,
                    to_contact=b,
                    kind=ContactRelationshipKind.COLLEAGUE,
                    defaults={'inferred': True, 'strength': 3,
                              'notes': f'Overlapping employment at company {mine.company_id}'},
                )
                if was_created:
                    created += 1
    return created


# ---------------------------------------------------------------------------
# Warm-intro ranking
# ---------------------------------------------------------------------------

def warm_intros_to_company(*, user, company: Company, max_hops: int = 2,
                           limit: int = 25) -> list[dict]:
    """Rank user's contacts who could warm-intro to anyone at `company`.

    Hop 1: contact has any employment at the target company.
    Hop 2: contact has a ContactRelationship to another contact that has an
           employment at the target company.

    Returns a list of dicts shaped for both REST and agent-tool consumers:
        {contact_id, name, title, score, hop, path, reason}
    """

    user_contacts = Contact.objects.filter(user=user)
    # Hop 1
    hop1_employments = (
        ContactEmployment.objects
        .filter(contact__in=user_contacts, company=company)
        .select_related('contact')
        .order_by('-is_current', '-started_at')
    )

    results: dict[int, dict] = {}
    for emp in hop1_employments:
        c = emp.contact
        reason_bits = [f'works at {company.name}' if emp.is_current
                       else f'previously worked at {company.name}']
        score = 60 + (20 if emp.is_current else 0) + min(c.relationship_strength, 5) * 4
        results[c.id] = {
            'contact_id': c.id,
            'name': c.name,
            'title': c.title or (emp.title or ''),
            'score': min(score, 100),
            'hop': 1,
            'path': [c.id],
            'reason': '; '.join(reason_bits),
        }

    if max_hops >= 2:
        # Build a map: contact_id -> [hop-1 contact_id, ...]
        rels = ContactRelationship.objects.filter(
            user=user,
            to_contact__in=[item['contact_id'] for item in results.values()],
        ).select_related('from_contact', 'to_contact')
        for rel in rels:
            from_id = rel.from_contact_id
            if from_id in results:
                continue  # already a direct (hop-1) intro
            hop1 = results.get(rel.to_contact_id)
            if not hop1:
                continue
            entry = results.setdefault(from_id, {
                'contact_id': from_id,
                'name': rel.from_contact.name,
                'title': rel.from_contact.title,
                'score': 0,
                'hop': 2,
                'path': [from_id, rel.to_contact_id],
                'reason': '',
            })
            # Don't downgrade a direct intro that was previously set; we already
            # skip with the continue above.
            score = 35 + min(rel.strength, 5) * 4 + min(rel.from_contact.relationship_strength, 5) * 2
            if score > entry['score']:
                entry['score'] = min(score, 100)
                entry['path'] = [from_id, rel.to_contact_id]
                entry['reason'] = (f'{rel.from_contact.name} → {rel.to_contact.name} '
                                   f'({rel.get_kind_display().lower()}) at {company.name}')

    ranked = sorted(results.values(), key=lambda d: (d['hop'], -d['score']))
    return ranked[:limit]


# ---------------------------------------------------------------------------
# Neighborhood (for React-Flow viz)
# ---------------------------------------------------------------------------

_MAX_NODES = 200


def _user_node(user) -> dict:
    return {'id': f'user:{user.id}', 'type': 'user',
            'data': {'label': user.get_username() or user.email or 'You'}}


def _contact_node(c: Contact) -> dict:
    return {'id': f'contact:{c.id}', 'type': 'contact',
            'data': {'label': c.name, 'title': c.title,
                     'strength': c.relationship_strength,
                     'profile_url': c.profile_url}}


def _company_node(co: Company) -> dict:
    return {'id': f'company:{co.id}', 'type': 'company',
            'data': {'label': co.name, 'domain': co.domain}}


def neighborhood(*, user, root_kind: str, root_id: int, depth: int = 1) -> dict:
    """Return {nodes: [...], edges: [...]} centred on a root node.

    root_kind: 'user' | 'contact' | 'company'
    depth: 1 returns immediate neighbours; 2 also expands one more layer.
    Capped at ~200 nodes total."""

    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    edge_seen: set[tuple[str, str, str]] = set()

    def add_edge(src: str, dst: str, label: str, kind: str = 'rel') -> None:
        key = (src, dst, label)
        if key in edge_seen:
            return
        edge_seen.add(key)
        edges.append({'id': f'e{len(edges)}', 'source': src, 'target': dst,
                      'label': label, 'data': {'kind': kind}})

    def add_node(node: dict) -> bool:
        if node['id'] in nodes:
            return False
        if len(nodes) >= _MAX_NODES:
            return False
        nodes[node['id']] = node
        return True

    def expand_user(u, current_depth: int) -> None:
        add_node(_user_node(u))
        if current_depth <= 0:
            return
        contacts = Contact.objects.filter(user=u).select_related('company')[:50]
        for c in contacts:
            if add_node(_contact_node(c)):
                add_edge(f'user:{u.id}', f'contact:{c.id}', 'knows')
                # Surface the contact's direct company FK even at depth 1 so the
                # default graph shows where people work, not just who you know.
                if c.company_id:
                    if add_node(_company_node(c.company)):
                        add_edge(f'contact:{c.id}', f'company:{c.company_id}',
                                 c.title or 'works at', 'employment')
                if current_depth - 1 > 0:
                    expand_contact(c, current_depth - 1)

    def expand_contact(c: Contact, current_depth: int) -> None:
        add_node(_contact_node(c))
        if current_depth <= 0:
            return
        for emp in c.employments.select_related('company')[:20]:
            if add_node(_company_node(emp.company)):
                label = emp.title or ('worked at' if not emp.is_current else 'works at')
                add_edge(f'contact:{c.id}', f'company:{emp.company_id}', label, 'employment')
        for rel in c.outgoing_relationships.select_related('to_contact').filter(user=user)[:25]:
            if add_node(_contact_node(rel.to_contact)):
                add_edge(f'contact:{c.id}', f'contact:{rel.to_contact_id}',
                         rel.get_kind_display().lower(), 'contact_rel')

    def expand_company(co: Company, current_depth: int) -> None:
        add_node(_company_node(co))
        if current_depth <= 0:
            return
        employees = (
            ContactEmployment.objects
            .filter(company=co, contact__user=user)
            .select_related('contact')[:50]
        )
        for emp in employees:
            if add_node(_contact_node(emp.contact)):
                add_edge(f'contact:{emp.contact_id}', f'company:{co.id}',
                         emp.title or ('works at' if emp.is_current else 'worked at'),
                         'employment')
        for rel in co.outgoing_company_rels.select_related('to_company')[:25]:
            if add_node(_company_node(rel.to_company)):
                add_edge(f'company:{co.id}', f'company:{rel.to_company_id}',
                         rel.get_kind_display().lower(), 'company_rel')

    depth = max(1, min(depth, 3))

    if root_kind == 'user':
        expand_user(user, depth)
    elif root_kind == 'contact':
        contact = Contact.objects.filter(user=user, pk=root_id).select_related('company').first()
        if contact is None:
            return {'nodes': [], 'edges': []}
        add_node(_user_node(user))
        add_edge(f'user:{user.id}', f'contact:{contact.id}', 'knows')
        expand_contact(contact, depth)
    elif root_kind == 'company':
        company = Company.objects.filter(pk=root_id).first()
        if company is None:
            return {'nodes': [], 'edges': []}
        expand_company(company, depth)
    else:
        return {'nodes': [], 'edges': []}

    return {'nodes': list(nodes.values()), 'edges': edges}
