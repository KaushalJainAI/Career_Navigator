"""Unit + integration tests for accounts.APIToken and APITokenAuthentication."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from accounts.models import APIToken


@pytest.mark.django_db
def test_issue_returns_cleartext_once_and_persists_only_hash():
    user = get_user_model().objects.create_user(username='u1', email='u1@x.com', password='pw-12345')
    token, cleartext = APIToken.issue(user=user, name='Chrome')

    assert cleartext
    # The cleartext token is NOT persisted; only its hash.
    assert token.token_hash == APIToken.hash_token(cleartext)
    assert cleartext != token.token_hash
    # Listing/reading the token instance must not surface the cleartext.
    refreshed = APIToken.objects.get(pk=token.pk)
    for field_value in vars(refreshed).values():
        assert cleartext != field_value


@pytest.mark.django_db
def test_token_authenticates_against_protected_endpoint():
    user = get_user_model().objects.create_user(username='u2', email='u2@x.com', password='pw')
    _, cleartext = APIToken.issue(user=user, name='Ext')

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Token {cleartext}')
    response = client.get('/api/v1/auth/me/')
    assert response.status_code == 200
    assert response.data['email'] == 'u2@x.com'


@pytest.mark.django_db
def test_revoked_token_is_rejected():
    user = get_user_model().objects.create_user(username='u3', email='u3@x.com', password='pw')
    token, cleartext = APIToken.issue(user=user, name='Ext')
    token.revoke()

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Token {cleartext}')
    response = client.get('/api/v1/auth/me/')
    assert response.status_code == 401


@pytest.mark.django_db
def test_tampered_token_is_rejected():
    user = get_user_model().objects.create_user(username='u4', email='u4@x.com', password='pw')
    APIToken.issue(user=user, name='Ext')

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION='Token totally-not-a-real-token')
    response = client.get('/api/v1/auth/me/')
    assert response.status_code == 401


@pytest.mark.django_db
def test_last_used_at_advances_on_use():
    user = get_user_model().objects.create_user(username='u5', email='u5@x.com', password='pw')
    token, cleartext = APIToken.issue(user=user, name='Ext')
    assert token.last_used_at is None

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Token {cleartext}')
    client.get('/api/v1/auth/me/')

    token.refresh_from_db()
    assert token.last_used_at is not None


@pytest.mark.django_db
def test_api_tokens_endpoint_create_returns_cleartext_once_list_does_not():
    user = get_user_model().objects.create_user(username='u6', email='u6@x.com', password='pw')
    client = APIClient()
    client.force_authenticate(user=user)

    resp = client.post('/api/v1/auth/api-tokens/', {'name': 'My laptop'}, format='json')
    assert resp.status_code == 201
    cleartext = resp.data['token']
    assert cleartext

    # Listing must not include the cleartext anywhere.
    resp = client.get('/api/v1/auth/api-tokens/')
    assert resp.status_code == 200
    listed = resp.data if isinstance(resp.data, list) else resp.data.get('results', resp.data)
    for item in listed:
        for v in item.values():
            assert cleartext != v


@pytest.mark.django_db
def test_api_token_revoke_endpoint():
    user = get_user_model().objects.create_user(username='u7', email='u7@x.com', password='pw')
    client = APIClient()
    client.force_authenticate(user=user)

    create = client.post('/api/v1/auth/api-tokens/', {'name': 't1'}, format='json')
    token_id = create.data['id']

    resp = client.post(f'/api/v1/auth/api-tokens/{token_id}/revoke/')
    assert resp.status_code == 200
    assert APIToken.objects.get(pk=token_id).revoked_at is not None

    # Listing returns only non-revoked tokens.
    list_resp = client.get('/api/v1/auth/api-tokens/')
    listed = list_resp.data if isinstance(list_resp.data, list) else list_resp.data.get('results', list_resp.data)
    assert all(item['id'] != token_id for item in listed)
