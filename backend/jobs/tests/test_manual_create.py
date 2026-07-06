"""Adding a job by hand via POST /api/v1/jobs/."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from jobs.models import Company, JobPosting, Source

pytestmark = pytest.mark.django_db


def _client():
    user = get_user_model().objects.create_user(username='u', email='u@x.com', password='pw-12345')
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_manual_create_makes_a_job_under_the_manual_source():
    client = _client()
    resp = client.post('/api/v1/jobs/', {
        'company_name': 'Acme Robotics',
        'title': 'Senior Backend Engineer',
        'location': 'Remote',
        'remote': True,
        'apply_url': 'https://acme.example/careers/42',
        'salary_min': 120000,
        'salary_max': 160000,
    }, format='json')

    assert resp.status_code == 201, resp.content
    job = JobPosting.objects.get(pk=resp.data['id'])
    assert job.title == 'Senior Backend Engineer'
    assert job.company.name == 'Acme Robotics'
    assert job.source.kind == 'manual'
    assert job.external_id.startswith('manual-')
    # User-entered → trusted → no ghost risk.
    assert job.ghost_risk == 0
    assert job.posted_at is not None


def test_manual_create_reuses_existing_company_and_source():
    client = _client()
    Company.objects.create(name='Acme Robotics')
    for i in range(2):
        client.post('/api/v1/jobs/', {'company_name': 'Acme Robotics', 'title': f'Role {i}'}, format='json')

    assert Company.objects.filter(name='Acme Robotics').count() == 1
    assert Source.objects.filter(name='Manual entry').count() == 1


def test_manual_create_requires_company_and_title():
    client = _client()
    resp = client.post('/api/v1/jobs/', {'title': 'No company'}, format='json')
    assert resp.status_code == 400
    assert 'company_name' in resp.data


def test_manually_added_job_shows_up_in_the_list():
    client = _client()
    client.post('/api/v1/jobs/', {'company_name': 'Acme', 'title': 'Widget Maker'}, format='json')
    resp = client.get('/api/v1/jobs/')
    assert resp.status_code == 200
    titles = [j['title'] for j in resp.data['results']]
    assert 'Widget Maker' in titles
