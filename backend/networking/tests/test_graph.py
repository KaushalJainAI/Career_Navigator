"""Unit tests for networking.graph — colleague inference, warm intros, neighborhood."""

import datetime as dt

import pytest
from django.contrib.auth import get_user_model

from jobs.models import Company
from networking.graph import (
    infer_colleague_relationships,
    neighborhood,
    warm_intros_to_company,
)
from networking.models import (
    Contact,
    ContactEmployment,
    ContactRelationship,
    ContactRelationshipKind,
)


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(
        username='owner', email='owner@x.com', password='pw'
    )


@pytest.fixture
def acme(db):
    return Company.objects.create(name='Acme', domain='acme.com')


@pytest.mark.django_db
def test_infer_colleague_creates_symmetric_edges_for_overlapping_employment(user, acme):
    alice = Contact.objects.create(user=user, name='Alice', company=acme)
    bob = Contact.objects.create(user=user, name='Bob', company=acme)
    ContactEmployment.objects.create(
        contact=alice, company=acme, title='Eng',
        started_at=dt.date(2022, 1, 1), ended_at=dt.date(2024, 1, 1),
    )
    ContactEmployment.objects.create(
        contact=bob, company=acme, title='Eng',
        started_at=dt.date(2023, 1, 1), ended_at=dt.date(2025, 1, 1),
    )

    created = infer_colleague_relationships(user=user, contact=alice)
    assert created == 2

    # Symmetric: A→B and B→A exist.
    assert ContactRelationship.objects.filter(
        user=user, from_contact=alice, to_contact=bob,
        kind=ContactRelationshipKind.COLLEAGUE,
    ).exists()
    assert ContactRelationship.objects.filter(
        user=user, from_contact=bob, to_contact=alice,
        kind=ContactRelationshipKind.COLLEAGUE,
    ).exists()


@pytest.mark.django_db
def test_infer_colleague_is_idempotent(user, acme):
    a = Contact.objects.create(user=user, name='A', company=acme)
    b = Contact.objects.create(user=user, name='B', company=acme)
    ContactEmployment.objects.create(contact=a, company=acme, started_at=dt.date(2022, 1, 1))
    ContactEmployment.objects.create(contact=b, company=acme, started_at=dt.date(2022, 1, 1))

    first = infer_colleague_relationships(user=user, contact=a)
    second = infer_colleague_relationships(user=user, contact=a)
    assert first == 2
    assert second == 0


@pytest.mark.django_db
def test_infer_colleague_no_overlap_means_no_edge(user, acme):
    a = Contact.objects.create(user=user, name='A', company=acme)
    b = Contact.objects.create(user=user, name='B', company=acme)
    ContactEmployment.objects.create(
        contact=a, company=acme,
        started_at=dt.date(2018, 1, 1), ended_at=dt.date(2019, 1, 1),
    )
    ContactEmployment.objects.create(
        contact=b, company=acme,
        started_at=dt.date(2022, 1, 1), ended_at=dt.date(2023, 1, 1),
    )
    created = infer_colleague_relationships(user=user, contact=a)
    assert created == 0


@pytest.mark.django_db
def test_warm_intros_hop1(user, acme):
    insider = Contact.objects.create(user=user, name='Insider', company=acme, relationship_strength=4)
    ContactEmployment.objects.create(
        contact=insider, company=acme, title='EM', is_current=True,
        started_at=dt.date(2023, 1, 1),
    )

    results = warm_intros_to_company(user=user, company=acme)
    assert len(results) == 1
    assert results[0]['contact_id'] == insider.id
    assert results[0]['hop'] == 1
    assert results[0]['path'] == [insider.id]


@pytest.mark.django_db
def test_warm_intros_hop2_via_colleague(user, acme):
    insider = Contact.objects.create(user=user, name='Insider', company=acme)
    bridge = Contact.objects.create(user=user, name='Bridge')
    ContactEmployment.objects.create(
        contact=insider, company=acme, is_current=True, started_at=dt.date(2023, 1, 1),
    )
    ContactRelationship.objects.create(
        user=user, from_contact=bridge, to_contact=insider,
        kind=ContactRelationshipKind.COLLEAGUE, strength=4,
    )

    results = warm_intros_to_company(user=user, company=acme, max_hops=2)
    by_id = {r['contact_id']: r for r in results}
    assert insider.id in by_id
    assert bridge.id in by_id
    assert by_id[insider.id]['hop'] == 1
    assert by_id[bridge.id]['hop'] == 2
    assert by_id[bridge.id]['path'] == [bridge.id, insider.id]


@pytest.mark.django_db
def test_warm_intros_max_hops_1_excludes_hop2(user, acme):
    insider = Contact.objects.create(user=user, name='Insider', company=acme)
    bridge = Contact.objects.create(user=user, name='Bridge')
    ContactEmployment.objects.create(contact=insider, company=acme, is_current=True)
    ContactRelationship.objects.create(
        user=user, from_contact=bridge, to_contact=insider,
        kind=ContactRelationshipKind.COLLEAGUE,
    )

    results = warm_intros_to_company(user=user, company=acme, max_hops=1)
    ids = {r['contact_id'] for r in results}
    assert insider.id in ids
    assert bridge.id not in ids


@pytest.mark.django_db
def test_neighborhood_user_root(user, acme):
    Contact.objects.create(user=user, name='C1', company=acme)
    Contact.objects.create(user=user, name='C2')

    data = neighborhood(user=user, root_kind='user', root_id=user.id, depth=1)
    node_ids = {n['id'] for n in data['nodes']}
    assert f'user:{user.id}' in node_ids
    assert any(nid.startswith('contact:') for nid in node_ids)


@pytest.mark.django_db
def test_neighborhood_company_root_lists_employees(user, acme):
    c = Contact.objects.create(user=user, name='Alice', company=acme)
    ContactEmployment.objects.create(contact=c, company=acme, is_current=True)

    data = neighborhood(user=user, root_kind='company', root_id=acme.id, depth=1)
    node_ids = {n['id'] for n in data['nodes']}
    assert f'company:{acme.id}' in node_ids
    assert f'contact:{c.id}' in node_ids
