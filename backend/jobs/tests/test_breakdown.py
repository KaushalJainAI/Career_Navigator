"""AI job-breakdown endpoint: generation, caching, billing and honesty."""

import json
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from billing.models import CreditLedger
from billing.services import balance
from jobs.models import Company, JobPosting, Source

pytestmark = pytest.mark.django_db


def _job():
    source, _ = Source.objects.get_or_create(name='Manual entry', defaults={'kind': 'manual'})
    company = Company.objects.create(name='Figma')
    return JobPosting.objects.create(
        source=source, external_id='x1', company=company,
        title='Infrastructure Engineer',
        description='Scale payment infrastructure, observability, and deployment systems.',
    )


def _client():
    """New user — starts with the automatic signup bonus."""
    user = get_user_model().objects.create_user(username='b', email='b@x.com', password='pw')
    c = APIClient()
    c.force_authenticate(user=user)
    return c, user


def _set_balance(user, target):
    """Nudge the ledger so the user's balance is exactly ``target``."""
    CreditLedger.objects.create(user=user, delta=target - balance(user), reason='top_up')


GOOD = json.dumps({
    'responsibilities': ['Own the deployment pipeline.', 'Improve observability.'],
    'requirements': ['5+ years in infra.', 'Strong with Kubernetes.'],
    'benefits': ['Equity.'],
    'about_company': 'Figma builds collaborative design tools.',
})


def test_generates_and_caches_breakdown_and_charges_once():
    job = _job()
    c, user = _client()
    start = balance(user)
    with patch('jobs.views.get_configured_llm', return_value=lambda _p: GOOD), \
         patch('jobs.views.configured_model_label', return_value='stub'):
        resp = c.post(f'/api/v1/jobs/{job.id}/breakdown/')
    assert resp.status_code == 200, resp.content
    assert resp.data['responsibilities'] == ['Own the deployment pipeline.', 'Improve observability.']
    assert resp.data['about_company'].startswith('Figma')
    assert balance(user) == start - 2  # charged 2

    job.refresh_from_db()
    assert job.ai_breakdown['requirements'] == ['5+ years in infra.', 'Strong with Kubernetes.']

    # Second call is a cache hit — no LLM, no further charge.
    with patch('jobs.views.get_configured_llm', side_effect=AssertionError('should not run')):
        resp2 = c.post(f'/api/v1/jobs/{job.id}/breakdown/')
    assert resp2.status_code == 200
    assert balance(user) == start - 2


def test_no_llm_returns_503_and_no_charge():
    job = _job()
    c, user = _client()
    start = balance(user)
    with patch('jobs.views.get_configured_llm', return_value=None):
        resp = c.post(f'/api/v1/jobs/{job.id}/breakdown/')
    assert resp.status_code == 503
    assert balance(user) == start


def test_failed_generation_refunds():
    job = _job()
    c, user = _client()
    start = balance(user)
    # LLM returns junk that yields no usable breakdown.
    with patch('jobs.views.get_configured_llm', return_value=lambda _p: 'sorry, no idea'):
        resp = c.post(f'/api/v1/jobs/{job.id}/breakdown/')
    assert resp.status_code == 502
    assert balance(user) == start  # charged then refunded
    job.refresh_from_db()
    assert job.ai_breakdown == {}


def test_insufficient_credits_returns_402():
    job = _job()
    c, user = _client()
    _set_balance(user, 1)  # below the 2-credit cost
    with patch('jobs.views.get_configured_llm', return_value=lambda _p: GOOD):
        resp = c.post(f'/api/v1/jobs/{job.id}/breakdown/')
    assert resp.status_code == 402
