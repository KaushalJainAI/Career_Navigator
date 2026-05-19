import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_register_creates_user_and_returns_tokens(api_client):
    url = reverse('auth-register')
    resp = api_client.post(url, {'email': 'new@example.com', 'password': 'pw12345678'}, format='json')
    assert resp.status_code == 201
    assert 'access' in resp.data and 'refresh' in resp.data
    assert resp.data['user']['email'] == 'new@example.com'


def test_me_requires_auth(api_client):
    resp = api_client.get(reverse('auth-me'))
    assert resp.status_code == 401


def test_me_returns_profile(auth_client, user):
    resp = auth_client.get(reverse('auth-me'))
    assert resp.status_code == 200
    assert resp.data['email'] == user.email
    assert resp.data['cn_profile']['tier'] == 'free'


def test_guest_key_requires_nvidia_key_configured(api_client, settings):
    settings.NVIDIA_API_KEY = ''
    resp = api_client.post(reverse('auth-guest-key'))
    assert resp.status_code == 503


def test_guest_key_issues_session(api_client, settings):
    settings.NVIDIA_API_KEY = 'dummy'
    resp = api_client.post(reverse('auth-guest-key'))
    assert resp.status_code == 201
    assert 'session_key' in resp.data
    assert resp.data['model'] == settings.NVIDIA_GUEST_MODEL
