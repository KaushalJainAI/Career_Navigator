"""User-triggered 'find new jobs' refresh endpoint."""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def _client():
    user = get_user_model().objects.create_user(username='r', email='r@x.com', password='pw')
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def test_refresh_requires_auth():
    resp = APIClient().post('/api/v1/jobs/refresh/')
    assert resp.status_code in (401, 403)


def test_refresh_runs_sources_and_reports_counts(settings):
    settings.RUN_INGESTION_ASYNC = False
    c = _client()
    fake = {'created': 3, 'updated': 1, 'skipped': 0, 'new_jobs': 3, 'sources': {'adzuna': 'success'}}
    with patch('ingestion.services.run_registered_sources', return_value=fake) as run:
        resp = c.post('/api/v1/jobs/refresh/')
    assert resp.status_code == 200, resp.content
    assert resp.data['new_jobs'] == 3
    assert '3 new jobs' in resp.data['detail']
    run.assert_called_once()


def test_refresh_zero_new_is_honest(settings):
    settings.RUN_INGESTION_ASYNC = False
    c = _client()
    fake = {'created': 0, 'updated': 0, 'skipped': 0, 'new_jobs': 0, 'sources': {}}
    with patch('ingestion.services.run_registered_sources', return_value=fake):
        resp = c.post('/api/v1/jobs/refresh/')
    assert resp.status_code == 200
    assert 'no new jobs' in resp.data['detail'].lower()


def test_refresh_async_dispatches_task(settings):
    settings.RUN_INGESTION_ASYNC = True
    c = _client()
    with patch('ingestion.tasks.run_all_sources.delay') as delay:
        resp = c.post('/api/v1/jobs/refresh/')
    assert resp.status_code == 202
    assert resp.data['status'] == 'started'
    delay.assert_called_once()
