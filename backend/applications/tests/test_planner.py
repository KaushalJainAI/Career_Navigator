"""Tests for the tracker planner: todos, goals (live progress), and follow-ups."""
import pytest

from applications.models import Application, ApplicationStatus, Goal, Todo
from jobs.models import Company, JobPosting, Source

pytestmark = pytest.mark.django_db


def _job(title='Backend Engineer'):
    company, _ = Company.objects.get_or_create(name='Acme', domain='acme.com')
    source, _ = Source.objects.get_or_create(name='gh-planner', kind='ats_public')
    return JobPosting.objects.create(source=source, external_id=title, company=company, title=title)


# ---- Application follow-up fields ----

def test_application_accepts_next_action_and_follow_up(auth_client, user):
    app = Application.objects.create(user=user, job=_job(), status=ApplicationStatus.APPLIED)
    response = auth_client.patch(f'/api/v1/applications/{app.id}/',
                                 {'next_action': 'Chase recruiter', 'follow_up_on': '2026-07-05'},
                                 format='json')
    assert response.status_code == 200
    assert response.data['next_action'] == 'Chase recruiter'
    assert response.data['follow_up_on'] == '2026-07-05'


# ---- Todos ----

def test_todo_crud_and_user_scoping(auth_client, user, django_user_model):
    app = Application.objects.create(user=user, job=_job('Dev'), status=ApplicationStatus.APPLIED)
    created = auth_client.post('/api/v1/applications/todos/',
                               {'title': 'Follow up', 'application': app.id, 'due_on': '2026-07-02'},
                               format='json')
    assert created.status_code == 201
    assert created.data['application_title'] == 'Dev'
    todo_id = created.data['id']

    done = auth_client.patch(f'/api/v1/applications/todos/{todo_id}/', {'done': True}, format='json')
    assert done.status_code == 200 and done.data['done'] is True

    # Not visible to another user.
    other = django_user_model.objects.create_user(username='o', email='o@x.com', password='pw')
    from rest_framework.test import APIClient
    c = APIClient(); c.force_authenticate(other)
    assert len(c.get('/api/v1/applications/todos/').data.get('results', c.get('/api/v1/applications/todos/').data)) == 0

    assert auth_client.delete(f'/api/v1/applications/todos/{todo_id}/').status_code == 204
    assert not Todo.objects.filter(id=todo_id).exists()


def test_todo_ordering_open_before_done(auth_client, user):
    Todo.objects.create(user=user, title='done one', done=True)
    Todo.objects.create(user=user, title='open one', done=False)
    data = auth_client.get('/api/v1/applications/todos/').data
    rows = data['results'] if isinstance(data, dict) and 'results' in data else data
    assert rows[0]['title'] == 'open one'  # open sorts first


# ---- Goals with live progress ----

def test_goal_progress_counts_applications_in_period(auth_client, user):
    for i in range(3):
        Application.objects.create(user=user, job=_job(f'App{i}'), status=ApplicationStatus.APPLIED)
    resp = auth_client.post('/api/v1/applications/goals/',
                            {'title': 'Apply weekly', 'metric': 'applications', 'target': 10, 'period': 'week'},
                            format='json')
    assert resp.status_code == 201
    assert resp.data['current'] == 3
    assert resp.data['target'] == 10


def test_goal_progress_counts_interviews(auth_client, user):
    Application.objects.create(user=user, job=_job('P'), status=ApplicationStatus.PHONE)
    Application.objects.create(user=user, job=_job('O'), status=ApplicationStatus.ONSITE)
    Application.objects.create(user=user, job=_job('S'), status=ApplicationStatus.SAVED)
    goal = Goal.objects.create(user=user, title='Interviews', metric=Goal.Metric.INTERVIEWS,
                               target=5, period=Goal.Period.ALL)
    data = auth_client.get(f'/api/v1/applications/goals/{goal.id}/').data
    assert data['current'] == 2  # phone + onsite, not saved


def test_custom_goal_uses_manual_progress(auth_client, user):
    goal = Goal.objects.create(user=user, title='Network', metric=Goal.Metric.CUSTOM,
                               target=10, period=Goal.Period.WEEK, manual_progress=4)
    data = auth_client.get(f'/api/v1/applications/goals/{goal.id}/').data
    assert data['current'] == 4
