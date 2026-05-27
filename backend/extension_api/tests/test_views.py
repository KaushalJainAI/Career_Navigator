"""Integration tests for extension_api endpoints (page-context, autofill,
submit-event, profile-context)."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from accounts.models import UserProfile
from applications.models import Application, ApplicationEvent
from jobs.models import Company, JobPosting, Source
from networking.models import Contact, ContactEmployment, ContactRelationship


@pytest.fixture
def user(db):
    user = get_user_model().objects.create_user(
        username='owner', email='owner@x.com', password='pw',
    )
    UserProfile.objects.get_or_create(user=user)
    return user


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.mark.django_db
def test_page_context_upserts_via_canonical_pipeline(client):
    payload = {
        'parser': 'linkedin',
        'external_id': '12345',
        'title': 'Backend Engineer',
        'description': 'Build things.',
        'apply_url': 'https://linkedin.com/jobs/view/12345',
        'company': {'name': 'Acme', 'domain': 'acme.com', 'ats_type': 'other'},
        'raw': {'foo': 'bar'},
    }
    resp = client.post('/api/v1/ext/page-context/', payload, format='json')
    assert resp.status_code == 200, resp.data
    assert resp.data['job_id']
    assert resp.data['stealth_blocked'] is False

    # Source is the canonical extension source for linkedin.
    assert Source.objects.filter(name='linkedin_extension').exists()
    job = JobPosting.objects.get(pk=resp.data['job_id'])
    assert job.company.name == 'Acme'
    assert job.raw == {'foo': 'bar'}

    # Same payload again → updated, not duplicated.
    resp2 = client.post('/api/v1/ext/page-context/', payload, format='json')
    assert resp2.status_code == 200
    assert resp2.data['job_id'] == resp.data['job_id']


@pytest.mark.parametrize('parser,source_name', [
    ('linkedin', 'linkedin_extension'),
    ('greenhouse', 'greenhouse_extension'),
    ('lever', 'lever_extension'),
    ('naukri', 'naukri_extension'),
    ('unstop', 'unstop_extension'),
    ('mercor', 'mercor_extension'),
])
@pytest.mark.django_db
def test_page_context_supports_all_parsers(client, parser, source_name):
    payload = {
        'parser': parser, 'external_id': f'{parser}-1', 'title': 'Eng',
        'company': {'name': 'Acme'},
    }
    resp = client.post('/api/v1/ext/page-context/', payload, format='json')
    assert resp.status_code == 200, resp.data
    assert Source.objects.filter(name=source_name).exists()


@pytest.mark.django_db
def test_page_context_stealth_blocks(client, user):
    profile = UserProfile.objects.get(user=user)
    profile.stealth_domains = ['acme.com']
    profile.save()

    payload = {
        'parser': 'linkedin', 'external_id': 'x', 'title': 'T',
        'company': {'name': 'Acme', 'domain': 'acme.com'},
    }
    resp = client.post('/api/v1/ext/page-context/', payload, format='json')
    assert resp.status_code == 200
    assert resp.data['stealth_blocked'] is True
    assert resp.data['job_id'] is None
    assert not JobPosting.objects.filter(external_id='x').exists()


@pytest.mark.django_db
def test_autofill_returns_field_confidence(client):
    resp = client.get('/api/v1/ext/autofill/')
    assert resp.status_code == 200
    assert 'field_confidence' in resp.data
    assert 'email' in resp.data['field_confidence']


@pytest.mark.django_db
def test_submit_event_creates_application_and_event(client, user):
    source, _ = Source.objects.get_or_create(name='greenhouse_extension', defaults={'kind': 'scraper'})
    company = Company.objects.create(name='Acme', domain='acme.com')
    job = JobPosting.objects.create(source=source, external_id='j1', company=company, title='Eng')

    payload = {'job_id': job.id, 'tier': 'autofill', 'parser': 'greenhouse',
               'field_values': {'email': 'x@y.com'}}
    resp = client.post('/api/v1/ext/submit-event/', payload, format='json')
    assert resp.status_code == 200
    app = Application.objects.get(user=user, job=job)
    assert app.status == 'applied'
    assert app.tier_used == 'autofill'
    assert ApplicationEvent.objects.filter(application=app, type='extension_submit').count() == 1

    # Re-submit is idempotent on application but appends an event.
    client.post('/api/v1/ext/submit-event/', payload, format='json')
    assert Application.objects.filter(user=user, job=job).count() == 1
    assert ApplicationEvent.objects.filter(application=app, type='extension_submit').count() == 2


@pytest.mark.django_db
def test_profile_context_creates_contact_and_employments(client, user):
    payload = {
        'profile_url': 'https://linkedin.com/in/alice',
        'name': 'Alice Doe',
        'headline': 'EM at Acme',
        'experiences': [
            {'company_name': 'Acme', 'company_domain': 'acme.com',
             'title': 'EM', 'started_at': '2023-01-01', 'is_current': True},
            {'company_name': 'OldCo', 'title': 'Senior Eng',
             'started_at': '2020-01-01', 'ended_at': '2022-12-31'},
        ],
    }
    resp = client.post('/api/v1/ext/profile-context/', payload, format='json')
    assert resp.status_code == 200, resp.data
    assert resp.data['contact_created'] is True
    assert resp.data['employments_created'] == 2

    contact = Contact.objects.get(pk=resp.data['contact_id'])
    assert contact.name == 'Alice Doe'
    assert contact.employments.count() == 2
    # Current employer hint should be set.
    assert contact.company is not None and contact.company.name == 'Acme'


@pytest.mark.django_db
def test_profile_context_is_idempotent_and_triggers_colleague_inference(client, user):
    # First contact at Acme.
    first = client.post('/api/v1/ext/profile-context/', {
        'profile_url': 'https://linkedin.com/in/alice', 'name': 'Alice',
        'experiences': [{'company_name': 'Acme', 'company_domain': 'acme.com',
                         'title': 'EM', 'started_at': '2023-01-01', 'is_current': True}],
    }, format='json')
    assert first.status_code == 200

    # Re-post same → no new contact, no new employment.
    again = client.post('/api/v1/ext/profile-context/', {
        'profile_url': 'https://linkedin.com/in/alice', 'name': 'Alice',
        'experiences': [{'company_name': 'Acme', 'company_domain': 'acme.com',
                         'title': 'EM', 'started_at': '2023-01-01', 'is_current': True}],
    }, format='json')
    assert again.status_code == 200
    assert again.data['contact_created'] is False
    assert again.data['employments_created'] == 0

    # Second contact at same Acme overlapping → colleague edges should fire.
    second = client.post('/api/v1/ext/profile-context/', {
        'profile_url': 'https://linkedin.com/in/bob', 'name': 'Bob',
        'experiences': [{'company_name': 'Acme', 'company_domain': 'acme.com',
                         'title': 'Eng', 'started_at': '2023-06-01', 'is_current': True}],
    }, format='json')
    assert second.status_code == 200
    assert second.data['colleagues_inferred'] >= 2  # symmetric pair

    assert ContactRelationship.objects.filter(user=user, kind='colleague').count() >= 2
