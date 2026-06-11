import pytest

from jobs.models import Company, JobPosting, Source
from matching.models import MatchScore
from resumes.models import Resume

pytestmark = pytest.mark.django_db


def _job():
    company, _ = Company.objects.get_or_create(name='Acme', domain='acme.com')
    source, _ = Source.objects.get_or_create(name='greenhouse-acme', kind='ats_public')
    return JobPosting.objects.create(
        source=source, external_id='m1', company=company,
        title='Senior Backend Engineer',
        description='Build microservices with Python, Django, Kafka.',
    )


def test_match_endpoint_returns_explanation_and_caches_it(auth_client, user):
    job = _job()
    Resume.objects.create(
        user=user, is_master=True,
        parsed_json={
            'summary': 'Backend engineer with Python and Django experience',
            'skills': [{'name': 'Python'}, {'name': 'Django'}],
        },
    )

    response = auth_client.get(f'/api/v1/matching/jobs/{job.id}/')

    assert response.status_code == 200
    assert 'python' in response.data['matched_skills']
    assert 'kafka' in response.data['gaps']
    assert response.data['explanation']
    assert any(item['kind'] == 'negative' for item in response.data['explanation'])

    cached = MatchScore.objects.get(user=user, job=job)
    assert cached.matched_skills == response.data['matched_skills']
    assert cached.explanation == response.data['explanation']


def test_match_endpoint_requires_a_parsed_resume(auth_client):
    job = _job()
    response = auth_client.get(f'/api/v1/matching/jobs/{job.id}/')
    assert response.status_code == 400
