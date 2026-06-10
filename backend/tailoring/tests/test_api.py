import pytest

from applications.models import Application, ApplicationStatus
from jobs.models import Company, JobPosting, Source
from resumes.models import Resume

pytestmark = pytest.mark.django_db


def _application(user):
    company = Company.objects.create(name='Tailor Co', domain='tailor.example')
    source = Source.objects.create(name='tailor-source', kind='manual')
    job = JobPosting.objects.create(
        source=source,
        external_id='tailor-1',
        company=company,
        title='Backend Engineer',
        description='Python Django APIs',
    )
    Resume.objects.create(
        user=user,
        label='Master',
        is_master=True,
        parse_status='done',
        parsed_json={'summary': 'Python engineer', 'skills': [{'name': 'Python'}]},
    )
    return Application.objects.create(user=user, job=job, status=ApplicationStatus.SAVED)


def test_tailor_resume_endpoint_updates_status_and_event(auth_client, user, monkeypatch):
    monkeypatch.setattr('tailoring.views.get_configured_llm', lambda: None)
    app = _application(user)

    response = auth_client.post('/api/v1/tailoring/resume/', {'application_id': app.id}, format='json')

    assert response.status_code == 200
    assert response.data['id']
    app.refresh_from_db()
    assert app.status == ApplicationStatus.TAILORED
    assert app.events.filter(type='tailored_resume_generated').exists()


def test_cover_letter_endpoint_records_event(auth_client, user, monkeypatch):
    monkeypatch.setattr('tailoring.views.get_configured_llm', lambda: None)
    app = _application(user)

    response = auth_client.post('/api/v1/tailoring/cover-letter/', {'application_id': app.id}, format='json')

    assert response.status_code == 200
    assert response.data['content']
    assert app.events.filter(type='cover_letter_generated').exists()
