import datetime as dt

import pytest
from django.contrib.auth import get_user_model

from agent.tools import builtins  # noqa: F401
from agent.tools import registry
from jobs.models import Company, JobPosting, Source
from networking.models import Contact, ContactEmployment, OutreachMessage


@pytest.mark.django_db
def test_referral_and_outreach_tools_create_reviewable_draft():
    user = get_user_model().objects.create_user(username='user', email='user@example.com', password='pass')
    source = Source.objects.create(name='greenhouse', kind='ats_public')
    company = Company.objects.create(name='Acme')
    job = JobPosting.objects.create(
        source=source,
        external_id='job-1',
        company=company,
        title='Backend Engineer',
    )
    contact = Contact.objects.create(user=user, company=company, name='Ada Manager', title='Engineering Manager')

    suggestions = registry.get('find_referral_contacts').fn(user_id=user.id, job_id=job.id)
    draft = registry.get('draft_outreach_message').fn(user_id=user.id, contact_id=contact.id, job_id=job.id)

    assert suggestions[0]['contact_id'] == contact.id
    assert draft['status'] == 'drafted'
    assert OutreachMessage.objects.filter(user=user, contact=contact, job=job).exists()


@pytest.mark.django_db
def test_find_warm_intros_tool_returns_hop1_for_employee():
    user = get_user_model().objects.create_user(username='wi', email='wi@x.com', password='p')
    company = Company.objects.create(name='Stripe', domain='stripe.com')
    contact = Contact.objects.create(user=user, company=company, name='Pat')
    ContactEmployment.objects.create(
        contact=contact, company=company, is_current=True,
        title='EM', started_at=dt.date(2023, 1, 1),
    )
    result = registry.get('find_warm_intros').fn(user_id=user.id, company_id=company.id)
    assert result
    assert result[0]['contact_id'] == contact.id
    assert result[0]['hop'] == 1


@pytest.mark.django_db
def test_explore_network_tool_returns_user_centred_graph():
    user = get_user_model().objects.create_user(username='en', email='en@x.com', password='p')
    company = Company.objects.create(name='Stripe')
    Contact.objects.create(user=user, company=company, name='Pat')
    out = registry.get('explore_network').fn(user_id=user.id, root_kind='user', depth=1)
    assert 'nodes' in out and 'edges' in out
    assert any(n['id'] == f'user:{user.id}' for n in out['nodes'])
