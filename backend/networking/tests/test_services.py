import pytest
from django.contrib.auth import get_user_model

from jobs.models import Company, JobPosting, Source
from networking.models import Contact, MessageStatus
from networking.services import (
    approve_outreach_message,
    draft_referral_message,
    mark_outreach_sent,
    rank_contacts_for_job,
)


@pytest.mark.django_db
def test_rank_contacts_prefers_company_and_seniority():
    user = get_user_model().objects.create_user(username='user', email='user@example.com', password='pass')
    source = Source.objects.create(name='greenhouse', kind='ats_public')
    company = Company.objects.create(name='Acme', domain='acme.test')
    job = JobPosting.objects.create(
        source=source,
        external_id='job-1',
        company=company,
        title='Backend Engineer',
    )
    senior = Contact.objects.create(
        user=user,
        company=company,
        name='Ada Manager',
        title='Senior Engineering Manager',
        relationship_strength=3,
    )
    Contact.objects.create(user=user, name='Loose Contact', title='Engineer')

    opportunities = rank_contacts_for_job(user=user, job=job)

    assert opportunities[0].contact == senior
    assert opportunities[0].score > 50
    assert 'works at Acme' in opportunities[0].reason


@pytest.mark.django_db
def test_outreach_send_requires_matching_unexpired_consent():
    user = get_user_model().objects.create_user(username='user', email='user@example.com', password='pass')
    company = Company.objects.create(name='Acme')
    contact = Contact.objects.create(user=user, company=company, name='Grace Hopper')
    message = draft_referral_message(user=user, contact=contact)

    missing = mark_outreach_sent(user=user, message=message, approval_token='bad-token')
    assert missing == {'ok': False, 'error': 'valid approval required'}

    consent = approve_outreach_message(user=user, message=message, approved_body='Approved body')
    sent = mark_outreach_sent(user=user, message=message, approval_token=consent.approval_token)

    message.refresh_from_db()
    consent.refresh_from_db()
    assert sent['ok'] is True
    assert message.status == MessageStatus.SENT
    assert consent.used_at is not None
