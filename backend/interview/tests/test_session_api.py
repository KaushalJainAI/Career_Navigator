"""Starting a grill session via the API, including the optional company_name."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def _client():
    user = get_user_model().objects.create_user(username='g', email='g@x.com', password='pw')
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def test_start_session_builds_a_question_bank():
    c = _client()
    resp = c.post('/api/v1/interview/sessions/', {
        'role': 'Senior Backend Engineer', 'stage': 'behavioral', 'difficulty': 'hard',
    }, format='json')
    assert resp.status_code == 201, resp.content
    assert resp.data['status'] == 'ready'
    assert len(resp.data['questions']) > 0
    assert resp.data['difficulty'] == 'hard'


def test_company_name_seeds_research():
    c = _client()
    resp = c.post('/api/v1/interview/sessions/', {
        'role': 'Data Scientist', 'stage': 'tech_phone', 'company_name': 'Stripe',
    }, format='json')
    assert resp.status_code == 201, resp.content
    # perform_create runs research(company_name, ...) which echoes the company back.
    assert resp.data['research'].get('company') == 'Stripe'
    # company_name is write-only — never leaks into the response.
    assert 'company_name' not in resp.data
