import pytest

from applications.models import Application, ApplicationStatus
from jobs.models import Company, JobPosting, Source
from matching.models import MatchScore

pytestmark = pytest.mark.django_db


def _job(title='Backend Engineer'):
    company, _ = Company.objects.get_or_create(name='Acme', domain='acme.com')
    source, _ = Source.objects.get_or_create(name='greenhouse-acme', kind='ats_public')
    return JobPosting.objects.create(
        source=source,
        external_id=title,
        company=company,
        title=title,
        location='Remote',
    )


def test_application_list_includes_job_detail(auth_client, user):
    job = _job()
    Application.objects.create(user=user, job=job, status=ApplicationStatus.SAVED)

    response = auth_client.get('/api/v1/applications/')

    assert response.status_code == 200
    data = response.data['results'] if isinstance(response.data, dict) and 'results' in response.data else response.data
    assert data[0]['job'] == job.id
    assert data[0]['job_detail']['title'] == 'Backend Engineer'
    assert data[0]['job_detail']['company']['name'] == 'Acme'


def test_dashboard_stats_count_real_user_pipeline(auth_client, user):
    saved = _job('Saved Role')
    phone = _job('Phone Role')
    offer = _job('Offer Role')
    Application.objects.create(user=user, job=saved, status=ApplicationStatus.SAVED)
    Application.objects.create(user=user, job=phone, status=ApplicationStatus.PHONE)
    Application.objects.create(user=user, job=offer, status=ApplicationStatus.OFFER)
    MatchScore.objects.create(user=user, job=saved, score=0.8, breakdown={}, gaps=[])

    response = auth_client.get('/api/v1/applications/stats/')

    assert response.status_code == 200
    assert response.data['active_applications'] == 2
    assert response.data['interviews_ready'] == 1
    assert response.data['offers_received'] == 1
    assert response.data['new_matches'] == 1
    assert response.data['saved_jobs'] == 1
    assert response.data['total_jobs'] == 3


def test_prepare_assist_application_saves_job_and_events(auth_client, user):
    job = _job('Assist Role')

    response = auth_client.post('/api/v1/applications/prepare/', {
        'job_id': job.id,
        'tier': 'assist',
    }, format='json')

    assert response.status_code == 201
    assert response.data['status'] == ApplicationStatus.SAVED
    assert response.data['approval_token'] == ''
    app = Application.objects.get(user=user, job=job)
    assert app.tier_used == 'assist'
    assert app.events.filter(type='assist_prepared').exists()


def test_prepare_autofill_application_marks_ready(auth_client, user):
    job = _job('Autofill Role')

    response = auth_client.post('/api/v1/applications/prepare/', {
        'job_id': job.id,
        'tier': 'autofill',
    }, format='json')

    assert response.status_code == 201
    assert response.data['status'] == ApplicationStatus.READY
    assert response.data['application']['tier_used'] == 'autofill'
    assert 'extension' in ' '.join(response.data['next_actions']).lower()
    assert Application.objects.get(user=user, job=job).events.filter(type='autofill_prepared').exists()


def test_prepare_autonomous_application_issues_approval_token(auth_client, user):
    job = _job('Autonomous Role')

    response = auth_client.post('/api/v1/applications/prepare/', {
        'job_id': job.id,
        'tier': 'autonomous',
    }, format='json')

    assert response.status_code == 201
    assert response.data['status'] == ApplicationStatus.READY
    assert response.data['approval_token']
    app = Application.objects.get(user=user, job=job)
    assert app.auto_apply_session is not None
    assert app.auto_apply_session.state == 'waiting_approval'
    assert app.events.filter(type='autonomous_prepared').exists()
