from datetime import timedelta

import pytest
from django.utils import timezone

from applications.models import Application
from jobs.models import Company, JobPosting, Source
from profiles.models import Experience, Preference, Skill, StructuredProfile

pytestmark = pytest.mark.django_db


def _job(ext='1', title='Backend Engineer', company='Acme'):
    c, _ = Company.objects.get_or_create(name=company, domain='')
    s, _ = Source.objects.get_or_create(name='greenhouse', kind='ats_public')
    return JobPosting.objects.create(source=s, external_id=ext, company=c, title=title,
                                     description='Python Django Kafka', remote=True)


def _ready_profile(user):
    p = StructuredProfile.objects.create(user=user, headline='Backend Engineer')
    Skill.objects.create(profile=p, name='Python')
    Skill.objects.create(profile=p, name='Django')
    Skill.objects.create(profile=p, name='Kafka')
    Experience.objects.create(profile=p, company='X', title='Backend Engineer', bullets=['Built Django APIs'])
    Preference.objects.create(profile=p, target_titles=['Backend Engineer'])
    return p


def test_new_user_is_told_to_add_resume_and_targets(auth_client):
    data = auth_client.get('/api/v1/applications/today/').data
    titles = [s['title'] for s in data['steps']]
    assert titles[0] == 'Add your résumé'
    assert 'Tell us the roles you want' in titles
    assert data['setup']['complete'] is False
    assert data['stats']['response_rate'] is None  # no fake numbers


def test_plan_orders_interviews_followups_and_matches(auth_client, user):
    _ready_profile(user)
    j1, j2, j3 = _job('1', company='Alpha'), _job('2', company='Beta'), _job('3', company='Gamma')
    Application.objects.create(user=user, job=j1, status='phone',
                               next_interview_at=timezone.now() + timedelta(days=1))
    Application.objects.create(user=user, job=j2, status='applied',
                               applied_at=timezone.now() - timedelta(days=9),
                               follow_up_at=timezone.now() - timedelta(days=2))
    data = auth_client.get('/api/v1/applications/today/').data
    kinds = [s['kind'] for s in data['steps']]
    assert kinds[0] == 'interview' and 'tomorrow' in data['steps'][0]['title']
    assert kinds[1] == 'follow_up' and 'Beta' in data['steps'][1]['title']
    assert 'discover' in kinds  # Gamma is a strong unseen match
    assert data['top_matches'][0]['id'] == j3.id
    assert data['stats']['applied'] == 2 and data['stats']['responses'] == 1
    assert data['setup']['complete'] is True


def test_status_change_sets_timing_and_follow_up_cycle(auth_client, user):
    app = Application.objects.create(user=user, job=_job())
    r = auth_client.patch(f'/api/v1/applications/{app.id}/', {'status': 'applied'}, format='json')
    assert r.status_code == 200
    app.refresh_from_db()
    assert app.applied_at and app.follow_up_at > app.applied_at
    r = auth_client.post(f'/api/v1/applications/{app.id}/followed-up/')
    app.refresh_from_db()
    assert app.follow_up_at is not None  # one more nudge
    auth_client.post(f'/api/v1/applications/{app.id}/followed-up/')
    app.refresh_from_db()
    assert app.follow_up_at is None  # then we stop nagging
    auth_client.patch(f'/api/v1/applications/{app.id}/', {'status': 'phone'}, format='json')
    app.refresh_from_db()
    assert app.events.filter(type='status_changed', payload__status='phone').exists()
