import json
from datetime import timedelta

import pytest
from django.utils import timezone

from agent.copilot.loop import llm_turn, parse_when, route
from applications.models import Application
from jobs.models import Company, JobPosting, Source
from networking.models import Contact
from profiles.models import Education, Experience, Preference, Project, Skill, StructuredProfile

pytestmark = pytest.mark.django_db


def _fresher(user):
    p = StructuredProfile.objects.create(user=user, full_name='Aarav Mehta', headline='Final-year CSE student')
    for s in ['Python', 'Java', 'SQL', 'React']:
        Skill.objects.create(profile=p, name=s)
    Education.objects.create(profile=p, institution='VIT Vellore', degree='B.Tech', field_of_study='CSE', gpa='8.4/10',
                             end_date=timezone.now().date().replace(month=6, day=1) + timedelta(days=365))
    Project.objects.create(profile=p, name='CampusCart', description='Built a React + Django marketplace used by 300 students',
                           tech_stack=['React', 'Django'])
    Preference.objects.create(profile=p, target_titles=['Software Engineer'], remote=True)
    return p


def _job(ext, title, company, desc='Python, Java and SQL. Open to 2026 graduates.'):
    c, _ = Company.objects.get_or_create(name=company, domain='')
    s, _ = Source.objects.get_or_create(name='greenhouse', kind='ats_public')
    return JobPosting.objects.create(source=s, external_id=ext, company=c, title=title, description=desc)


def chat(client, message, sid=None):
    r = client.post('/api/v1/agent/copilot/', {'message': message, 'session_id': sid}, format='json')
    assert r.status_code == 200, r.data
    return r.data


def test_help_and_overview(auth_client, user):
    _fresher(user)
    out = chat(auth_client, 'hi')
    assert 'Find new jobs' in out['reply'] and out['mode'] == 'rules'
    out = chat(auth_client, 'What should I do today?', out['session_id'])
    assert out['steps'][0]['tool'] == 'get_overview'
    assert 'This week' in out['reply']


def test_search_tailor_and_track_flow(auth_client, user):
    _fresher(user)
    job = _job('1', 'Software Engineer - New Grad', 'Zoho')
    _job('2', 'Senior Staff Engineer', 'Acme', 'Go, Kubernetes. 10+ years of experience.')
    out = chat(auth_client, 'show my best matches')
    assert out['steps'][0]['tool'] == 'search_jobs'
    assert out['reply'].index('Zoho') < out['reply'].index('Acme')

    out = chat(auth_client, 'tailor my resume for Zoho', out['session_id'])
    assert out['steps'][0]['tool'] == 'tailor_resume' and out['steps'][0]['ok'], out
    app = Application.objects.get(user=user, job=job)
    assert app.status == 'tailored'
    assert any(u['to'] == f'/jobs/{job.id}' for u in out['ui'])

    # status change is confirm-gated
    sid = out['session_id']
    out = chat(auth_client, 'I got an OA from Zoho tomorrow at 10am', sid)
    pending = out['pending_action']
    assert pending and pending['tool'] == 'update_application' and pending['args']['status'] == 'assessment'
    app.refresh_from_db()
    assert app.status == 'tailored'  # nothing changed before approval
    r = auth_client.post(f'/api/v1/agent/copilot/{sid}/approve/', {'action_id': pending['id'], 'approve': True}, format='json')
    assert r.status_code == 200 and 'assessment' in r.data['reply']
    app.refresh_from_db()
    assert app.status == 'assessment' and app.next_interview_at.hour == 10
    # replaying the approval is rejected
    r = auth_client.post(f'/api/v1/agent/copilot/{sid}/approve/', {'action_id': pending['id'], 'approve': True}, format='json')
    assert r.status_code == 409


def test_cancel_changes_nothing(auth_client, user):
    _fresher(user)
    out = chat(auth_client, 'add skills Docker, Kubernetes')
    p = out['pending_action']
    assert p['args']['add'] == ['Docker', 'Kubernetes']
    r = auth_client.post(f"/api/v1/agent/copilot/{out['session_id']}/approve/", {'action_id': p['id'], 'approve': False}, format='json')
    assert 'did not change' in r.data['reply']
    assert not Skill.objects.filter(name='Docker').exists()


def test_contacts_and_referral_draft(auth_client, user):
    _fresher(user)
    job = _job('3', 'SDE Intern', 'Google')
    Application.objects.create(user=user, job=job)
    out = chat(auth_client, 'add contact Riya Shah, SDE at Google, my college senior')
    assert out['pending_action']['args'] == {'name': 'Riya Shah', 'title': 'SDE', 'company': 'Google', 'notes': 'my college senior'}
    auth_client.post(f"/api/v1/agent/copilot/{out['session_id']}/approve/",
                     {'action_id': out['pending_action']['id'], 'approve': True}, format='json')
    assert Contact.objects.get(user=user).company.name == 'Google'
    out = chat(auth_client, 'draft a referral message for Google', out['session_id'])
    assert out['steps'][0]['tool'] == 'draft_referral_message' and 'Riya' in out['reply']


def test_targets_and_deadline(auth_client, user):
    _fresher(user)
    app = Application.objects.create(user=user, job=_job('4', 'Graduate Engineer Trainee', 'Infosys'))
    out = chat(auth_client, 'My target roles are SDE Intern and Data Analyst')
    assert out['pending_action']['args']['roles'] == ['SDE Intern', 'Data Analyst']
    out = chat(auth_client, 'deadline for Infosys is 14 Nov')
    assert out['pending_action']['args']['deadline'].endswith('-11-14')
    assert out['pending_action']['args']['application_id'] == app.id


def test_parse_when():
    now = timezone.make_aware(timezone.datetime(2026, 11, 2, 9, 0))  # Monday
    assert parse_when('OA on friday at 3pm', now).isoformat().startswith('2026-11-06T15:00')
    assert parse_when('tomorrow', now).date().isoformat() == '2026-11-03'
    assert parse_when('14th Nov', now).date().isoformat() == '2026-11-14'
    assert parse_when('nothing here', now) is None


def test_llm_loop_reads_then_pauses_on_confirm(user):
    _fresher(user)
    app = Application.objects.create(user=user, job=_job('5', 'SDE', 'Wipro'))
    calls = []

    def fake_llm(prompt):
        calls.append(prompt)
        if len(calls) == 1:
            return json.dumps({'tool_calls': [{'name': 'list_applications', 'args': {'company': 'Wipro'}}]})
        assert '--- PRIOR STEPS ---' in prompt and 'Wipro' in prompt.split('--- PRIOR STEPS ---')[1]
        return json.dumps({'tool_calls': [{'name': 'update_application',
                                           'args': {'application_id': app.id, 'status': 'rejected'}}]})

    out = llm_turn(user, 'Wipro rejected me', [], fake_llm)
    assert out['steps'][0]['tool'] == 'list_applications'
    assert out['pending_action']['tool'] == 'update_application'
    app.refresh_from_db()
    assert app.status == 'saved'


def test_tool_endpoint_requires_confirmation_for_writes(auth_client, user):
    _fresher(user)
    assert any(t['name'] == 'search_jobs' for t in auth_client.get('/api/v1/agent/copilot/tools/').data['tools'])
    r = auth_client.post('/api/v1/agent/copilot/tools/update_skills/', {'args': {'add': ['Go']}}, format='json')
    assert r.status_code == 409
    r = auth_client.post('/api/v1/agent/copilot/tools/update_skills/', {'args': {'add': ['Go']}, 'confirmed': True}, format='json')
    assert r.status_code == 200 and 'Go' in r.data['result']['added']


def test_router_never_targets_other_users_data(auth_client, user):
    from django.contrib.auth import get_user_model
    other = get_user_model().objects.create_user(username='o', email='o@x.com', password='pw-123456')
    Application.objects.create(user=other, job=_job('6', 'SDE', 'Secretco'))
    plan = route(user, 'I applied to Secretco')
    assert not (isinstance(plan, list) and plan[0][0] == 'update_application')
