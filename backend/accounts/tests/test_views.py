import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_register_creates_user_and_returns_tokens(api_client):
    url = reverse('auth-register')
    resp = api_client.post(url, {'email': 'new@example.com', 'password': 'pw12345678'}, format='json')
    assert resp.status_code == 201
    assert 'access' in resp.data and 'refresh' in resp.data
    assert resp.data['user']['email'] == 'new@example.com'


def test_register_duplicate_email_returns_400(api_client):
    url = reverse('auth-register')
    payload = {'email': 'dupe@example.com', 'password': 'pw12345678'}
    first = api_client.post(url, payload, format='json')
    assert first.status_code == 201
    # Second signup with the same email must be a clean 400, never a 500.
    second = api_client.post(url, payload, format='json')
    assert second.status_code == 400
    assert 'email' in second.data


def test_register_duplicate_email_case_insensitive_returns_400(api_client):
    url = reverse('auth-register')
    api_client.post(url, {'email': 'Mixed@Example.com', 'password': 'pw12345678'}, format='json')
    resp = api_client.post(url, {'email': 'mixed@example.com', 'password': 'pw12345678'}, format='json')
    assert resp.status_code == 400


def test_register_short_password_returns_400(api_client):
    resp = api_client.post(
        reverse('auth-register'),
        {'email': 'short@example.com', 'password': 'pw1'},
        format='json',
    )
    assert resp.status_code == 400
    assert 'password' in resp.data


def test_me_requires_auth(api_client):
    resp = api_client.get(reverse('auth-me'))
    assert resp.status_code == 401


def test_me_returns_profile(auth_client, user):
    resp = auth_client.get(reverse('auth-me'))
    assert resp.status_code == 200
    assert resp.data['email'] == user.email
    assert resp.data['cn_profile']['tier'] == 'free'


def test_me_patch_updates_name_and_stealth_domains(auth_client, user):
    resp = auth_client.patch(
        reverse('auth-me'),
        {'first_name': 'Ada', 'last_name': 'Lovelace', 'stealth_domains': ['acme.com']},
        format='json',
    )
    assert resp.status_code == 200
    assert resp.data['first_name'] == 'Ada'
    assert resp.data['last_name'] == 'Lovelace'
    assert resp.data['cn_profile']['stealth_domains'] == ['acme.com']
    user.refresh_from_db()
    assert user.cn_profile.stealth_domains == ['acme.com']


def test_change_password_requires_correct_current(auth_client):
    resp = auth_client.post(
        reverse('auth-change-password'),
        {'current_password': 'wrong', 'new_password': 'brand-new-pw-123'},
        format='json',
    )
    assert resp.status_code == 400
    assert 'current_password' in resp.data


def test_change_password_succeeds(auth_client, user):
    resp = auth_client.post(
        reverse('auth-change-password'),
        {'current_password': 'pw-test-1234', 'new_password': 'brand-new-pw-123'},
        format='json',
    )
    assert resp.status_code == 200
    user.refresh_from_db()
    assert user.check_password('brand-new-pw-123')


def test_change_password_rejects_short_password(auth_client):
    resp = auth_client.post(
        reverse('auth-change-password'),
        {'current_password': 'pw-test-1234', 'new_password': 'short'},
        format='json',
    )
    assert resp.status_code == 400
    assert 'new_password' in resp.data


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
