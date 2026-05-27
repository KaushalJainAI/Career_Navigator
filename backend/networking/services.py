import secrets
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from jobs.models import JobPosting

from .models import (
    ActionQueueItem,
    ConsentAction,
    Contact,
    OutreachChannel,
    OutreachMessage,
    ReferralOpportunity,
    UserConsentEvent,
)


SENIORITY_TERMS = ('chief', 'vp', 'vice president', 'director', 'head', 'lead', 'manager', 'principal', 'staff', 'senior')
RECRUITER_TERMS = ('recruiter', 'talent', 'people', 'sourcer')


def rank_contacts_for_job(*, user, job: JobPosting, limit: int = 10) -> list[ReferralOpportunity]:
    contacts = Contact.objects.filter(user=user).select_related('company')
    company_terms = [job.company.name]
    if job.company.domain:
        company_terms.append(job.company.domain)
    query = Q()
    for term in company_terms:
        query |= Q(company__name__icontains=term) | Q(notes__icontains=term) | Q(tags__icontains=term)
    company_contacts = contacts.filter(query).distinct()
    if not company_contacts.exists():
        company_contacts = contacts

    opportunities = []
    for contact in company_contacts[: max(limit * 3, 20)]:
        score = contact.relationship_strength * 12
        reason_bits = []
        title = contact.title.lower()
        if contact.company_id == job.company_id:
            score += 40
            reason_bits.append(f'works at {job.company.name}')
        if any(term in title for term in SENIORITY_TERMS):
            score += 20
            reason_bits.append('has senior/team influence')
        if any(term in title for term in RECRUITER_TERMS):
            score += 18
            reason_bits.append('likely involved in hiring')
        if contact.email:
            score += 8
            reason_bits.append('has an approved contact channel')
        if contact.profile_url:
            score += 5
            reason_bits.append('has a profile URL for manual review')
        score = min(score, 100)
        if not reason_bits:
            reason_bits.append('available in your contact network')
        opportunity, _ = ReferralOpportunity.objects.update_or_create(
            user=user,
            job=job,
            contact=contact,
            defaults={
                'score': score,
                'reason': '; '.join(reason_bits),
                'next_action': 'Draft a concise referral note',
            },
        )
        opportunities.append(opportunity)

    return sorted(opportunities, key=lambda item: item.score, reverse=True)[:limit]


def draft_referral_message(*, user, contact: Contact, job: JobPosting | None = None,
                           channel: str = OutreachChannel.MANUAL) -> OutreachMessage:
    profile = getattr(user, 'structured_profile', None)
    user_name = getattr(profile, 'full_name', '') or user.get_username() or 'there'
    role_line = f' for the {job.title} role at {job.company.name}' if job else ''
    subject = f'Quick question{role_line}'[:255]
    greeting = contact.name.split()[0] if contact.name else 'there'
    body = (
        f'Hi {greeting},\n\n'
        f'I am {user_name}. I came across{role_line or " a role that looks relevant"} and thought your perspective '
        'could be really helpful. If you are open to it, I would appreciate a quick pointer on whether the team is '
        'actively hiring and whether my background looks worth referring.\n\n'
        'I can send a short resume summary or the job link if useful. Thanks either way.'
    )
    return OutreachMessage.objects.create(
        user=user,
        contact=contact,
        job=job,
        channel=channel,
        subject=subject,
        draft_body=body,
    )


def approve_outreach_message(*, user, message: OutreachMessage, approved_body: str | None = None,
                             ttl_hours: int = 24) -> UserConsentEvent:
    payload_hash = message.approve(approved_body)
    token = secrets.token_urlsafe(32)
    return UserConsentEvent.objects.create(
        user=user,
        action_type=ConsentAction.SEND_OUTREACH,
        target_type='outreach_message',
        target_id=message.id,
        payload_hash=payload_hash,
        approval_token=token,
        expires_at=timezone.now() + timedelta(hours=ttl_hours),
    )


def mark_outreach_sent(*, user, message: OutreachMessage, approval_token: str) -> dict:
    consent = UserConsentEvent.objects.filter(
        user=user,
        action_type=ConsentAction.SEND_OUTREACH,
        target_type='outreach_message',
        target_id=message.id,
        approval_token=approval_token,
        payload_hash=message.payload_hash,
    ).first()
    if not consent or not consent.is_valid:
        return {'ok': False, 'error': 'valid approval required'}
    message.status = 'sent'
    message.sent_at = timezone.now()
    message.save(update_fields=['status', 'sent_at', 'updated_at'])
    consent.used_at = timezone.now()
    consent.save(update_fields=['used_at'])
    ActionQueueItem.objects.create(
        user=user,
        action_type='follow_up_outreach',
        title=f'Follow up with {message.contact.name}',
        priority=60,
        due_at=timezone.now() + timedelta(days=5),
        job=message.job,
        contact=message.contact,
        metadata={'outreach_message_id': message.id},
    )
    return {'ok': True, 'message_id': message.id, 'status': message.status}
