import pytest

from applications.models import Application, ApplicationStatus
from jobs.models import Company, JobPosting, Source
from profiles.models import Experience, Skill, StructuredProfile
from resumes.models import Resume
from tailoring.models import TailoredResume

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


def test_export_resume_txt_renders_ats_safe_text_from_profile(auth_client, user):
    profile = StructuredProfile.objects.create(
        user=user, full_name='Jane Doe', headline='Backend Engineer', summary='Builds APIs.',
        location='Remote',
    )
    Skill.objects.create(profile=profile, name='Python')
    Experience.objects.create(profile=profile, company='Acme', title='Senior Engineer', is_current=True)

    response = auth_client.get('/api/v1/tailoring/resume/export/')

    assert response.status_code == 200
    assert response['Content-Type'].startswith('text/plain')
    assert 'attachment' in response['Content-Disposition']
    body = response.content.decode()
    assert body.startswith('JANE DOE')
    assert 'SKILLS\nPython' in body
    assert 'Senior Engineer - Acme' in body


def test_export_resume_overlays_tailored_summary(auth_client, user):
    StructuredProfile.objects.create(user=user, full_name='Jane Doe', summary='Generic summary.')
    app = _application(user)
    TailoredResume.objects.create(
        application=app, content={'raw_text': '...', 'summary': 'Tailored for this exact role.'},
    )

    response = auth_client.get(f'/api/v1/tailoring/resume/export/?application_id={app.id}')

    body = response.content.decode()
    assert 'Tailored for this exact role.' in body
    assert 'Generic summary.' not in body


def test_export_resume_docx_returns_attachment(auth_client, user):
    StructuredProfile.objects.create(user=user, full_name='Jane Doe', summary='Builds APIs.')

    response = auth_client.get('/api/v1/tailoring/resume/export/?fmt=docx')

    assert response.status_code == 200
    assert 'wordprocessingml' in response['Content-Type']
    assert response['Content-Disposition'].endswith('resume-ats.docx"')
    assert len(response.content) > 0


def _profile_user(user):
    profile = StructuredProfile.objects.create(user=user, full_name='Jane Doe', headline='Backend Engineer')
    Skill.objects.create(profile=profile, name='Python')
    Experience.objects.create(profile=profile, company='Acme', title='Senior Engineer',
                              bullets=['Ran the offsite', 'Built Django APIs for payments'])
    return profile


def test_tailor_by_job_id_creates_application_and_export_uses_tailored(auth_client, user):
    _profile_user(user)
    app = _application(user)
    app.delete()
    from jobs.models import JobPosting
    job = JobPosting.objects.get(external_id='tailor-1')
    r = auth_client.post('/api/v1/tailoring/resume/', {'job_id': job.id}, format='json')
    assert r.status_code == 200, r.data
    assert r.data['content']['experiences'][0]['bullets'][0] == 'Built Django APIs for payments'
    assert r.data['diff_from_master']['keyword_coverage'] is not None
    app_id = r.data['application_id']
    # user edits a bullet; export reflects the edit
    r2 = auth_client.patch(f"/api/v1/tailoring/resume/{r.data['id']}/", {'content': {
        'summary': 'Edited summary.', 'experiences': [{'bullets': ['Shipped payments APIs in Django']}]}},
        format='json')
    assert r2.status_code == 200
    assert r2.data['content']['experiences'][0]['company'] == 'Acme'
    body = auth_client.get(f'/api/v1/tailoring/resume/export/?application_id={app_id}').content.decode()
    assert 'Edited summary.' in body and '- Shipped payments APIs in Django' in body
    assert auth_client.get(f'/api/v1/tailoring/resume/?application_id={app_id}').status_code == 200


def test_cover_letter_edit_roundtrip(auth_client, user):
    _profile_user(user)
    app = _application(user)
    r = auth_client.post('/api/v1/tailoring/cover-letter/', {'application_id': app.id}, format='json')
    assert r.status_code == 200 and 'Dear Tailor Co hiring team' in r.data['content']
    r2 = auth_client.patch(f"/api/v1/tailoring/cover-letter/{r.data['id']}/", {'content': 'Mine now.'}, format='json')
    assert r2.data['content'] == 'Mine now.'
