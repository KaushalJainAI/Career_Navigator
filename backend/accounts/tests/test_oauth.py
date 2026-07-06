"""Unit tests for Google OAuth — both the provider helper and the view.

We never hit the real Google endpoints. The provider is unit-tested by
injecting an httpx.MockTransport client; the view is tested by swapping
out `GoogleLoginView.provider_factory` with a fake."""

from __future__ import annotations

import pytest
import httpx
from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.oauth import GoogleOAuthError, GoogleOAuthProvider
from accounts.views import GoogleLoginView


# ────────────────────────── provider unit tests ──────────────────────────

def _mock_client(handler):
    transport = httpx.MockTransport(handler)
    return httpx.Client(transport=transport)


def test_get_auth_url_contains_expected_params(settings):
    settings.GOOGLE_OAUTH_CLIENT_ID = 'cid'
    settings.GOOGLE_OAUTH_REDIRECT_URI = 'http://localhost/cb'
    p = GoogleOAuthProvider()
    url = p.get_auth_url(state='xyz')
    assert url.startswith('https://accounts.google.com/o/oauth2/v2/auth?')
    assert 'client_id=cid' in url
    assert 'redirect_uri=http%3A%2F%2Flocalhost%2Fcb' in url
    assert 'state=xyz' in url
    assert 'response_type=code' in url


def test_exchange_code_posts_form_to_token_url(settings):
    settings.GOOGLE_OAUTH_CLIENT_ID = 'cid'
    settings.GOOGLE_OAUTH_CLIENT_SECRET = 'secret'
    settings.GOOGLE_OAUTH_REDIRECT_URI = 'http://localhost/cb'
    captured = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured['url'] = str(req.url)
        captured['body'] = req.content.decode()
        return httpx.Response(200, json={'access_token': 'AT', 'refresh_token': 'RT'})

    p = GoogleOAuthProvider(http=_mock_client(handler))
    tokens = p.exchange_code('the-code')
    assert captured['url'] == p.TOKEN_URL
    assert 'code=the-code' in captured['body']
    assert 'client_id=cid' in captured['body']
    assert 'grant_type=authorization_code' in captured['body']
    assert tokens == {'access_token': 'AT', 'refresh_token': 'RT'}


def test_exchange_code_transport_error_raises():
    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError('boom', request=req)

    p = GoogleOAuthProvider(http=_mock_client(handler))
    with pytest.raises(GoogleOAuthError):
        p.exchange_code('x')


def test_get_user_info_sends_bearer_header():
    captured = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured['auth'] = req.headers.get('authorization')
        return httpx.Response(200, json={'email': 'a@b.com', 'given_name': 'A', 'family_name': 'B'})

    p = GoogleOAuthProvider(http=_mock_client(handler))
    info = p.get_user_info('AT')
    assert captured['auth'] == 'Bearer AT'
    assert info['email'] == 'a@b.com'


# ────────────────────────── view integration tests ─────────────────────
# The view verifies a Google ID token via `GoogleLoginView.verify_token`; tests
# swap that for a fake so we never call google-auth or the network.

def _fake_verifier(idinfo=None, *, raise_exc=None):
    info = idinfo or {'email': 'alice@example.com', 'given_name': 'Alice', 'family_name': 'X'}

    def verify(_token):
        if raise_exc:
            raise raise_exc
        return info
    return staticmethod(verify)


@pytest.fixture(autouse=True)
def restore_verify_token():
    original = GoogleLoginView.verify_token
    yield
    GoogleLoginView.verify_token = original


@pytest.mark.django_db
def test_google_login_creates_user_and_returns_jwt(api_client):
    GoogleLoginView.verify_token = _fake_verifier()
    resp = api_client.post(reverse('auth-google'), {'credential': 'tok'}, format='json')
    assert resp.status_code == 201
    assert 'access' in resp.data and 'refresh' in resp.data
    assert resp.data['user']['email'] == 'alice@example.com'
    User = get_user_model()
    user = User.objects.get(email='alice@example.com')
    assert user.first_name == 'Alice'
    assert not user.has_usable_password()  # OAuth-only account
    assert hasattr(user, 'cn_profile')  # signal created the profile


@pytest.mark.django_db
def test_google_login_existing_user_returns_jwt_without_duplicating(api_client):
    User = get_user_model()
    User.objects.create_user(username='alice', email='alice@example.com', password='x')
    GoogleLoginView.verify_token = _fake_verifier()
    # NGU sends the credential under `access_token`; we accept it too.
    resp = api_client.post(reverse('auth-google'), {'access_token': 'tok'}, format='json')
    assert resp.status_code == 200
    assert User.objects.filter(email='alice@example.com').count() == 1


@pytest.mark.django_db
def test_google_login_401_on_invalid_token(api_client):
    GoogleLoginView.verify_token = _fake_verifier(raise_exc=GoogleOAuthError('bad audience'))
    resp = api_client.post(reverse('auth-google'), {'credential': 'tok'}, format='json')
    assert resp.status_code == 401
    assert 'invalid google token' in resp.data['detail'].lower()


@pytest.mark.django_db
def test_google_login_400_on_missing_credential(api_client):
    resp = api_client.post(reverse('auth-google'), {}, format='json')
    assert resp.status_code == 400  # serializer rejects: no token supplied


@pytest.mark.django_db
def test_google_login_400_on_missing_email(api_client):
    GoogleLoginView.verify_token = _fake_verifier({'given_name': 'A', 'family_name': 'B'})
    resp = api_client.post(reverse('auth-google'), {'credential': 'tok'}, format='json')
    assert resp.status_code == 400
    assert 'email' in resp.data['detail'].lower()


@pytest.mark.django_db
def test_google_login_handles_username_collision(api_client):
    User = get_user_model()
    User.objects.create_user(username='alice', email='someone-else@x.com', password='x')
    GoogleLoginView.verify_token = _fake_verifier()
    resp = api_client.post(reverse('auth-google'), {'credential': 'tok'}, format='json')
    assert resp.status_code == 201
    user = User.objects.get(email='alice@example.com')
    assert user.username == 'alice1'
