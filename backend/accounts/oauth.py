"""Google OAuth2 helper — ported from AIAAS/credentials/oauth.py.

The AIAAS port uses aiohttp + `async def`, but its DRF view calls those
methods synchronously (a latent bug). We use `httpx` synchronously here so
the call site stays straightforward DRF.

Public surface mirrors AIAAS so prior knowledge transfers:
    provider = GoogleOAuthProvider(redirect_uri=...)
    url      = provider.get_auth_url(state="abc")
    tokens   = provider.exchange_code(code)
    info     = provider.get_user_info(tokens['access_token'])
"""

from __future__ import annotations

from urllib.parse import unquote, urlencode

import httpx
from django.conf import settings


class GoogleOAuthError(Exception):
    """Raised on transport / OAuth provider failures."""


class GoogleOAuthProvider:
    AUTHORIZATION_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
    TOKEN_URL = 'https://oauth2.googleapis.com/token'
    USER_INFO_URL = 'https://www.googleapis.com/oauth2/v3/userinfo'

    def __init__(self, redirect_uri: str | None = None, *,
                 client_id: str | None = None,
                 client_secret: str | None = None,
                 http: httpx.Client | None = None):
        self.client_id = client_id or settings.GOOGLE_OAUTH_CLIENT_ID
        self.client_secret = client_secret or settings.GOOGLE_OAUTH_CLIENT_SECRET
        self.redirect_uri = redirect_uri or settings.GOOGLE_OAUTH_REDIRECT_URI
        # Tests inject a fake client; prod opens one per call.
        self._http = http

    def _client(self) -> httpx.Client:
        return self._http or httpx.Client(timeout=15.0)

    def get_auth_url(self, scopes: list[str] | None = None,
                     state: str | None = None, prompt: str = 'consent') -> str:
        scopes = scopes or settings.GOOGLE_OAUTH_LOGIN_SCOPES
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(scopes),
            'access_type': 'offline',
            'prompt': prompt,
            'include_granted_scopes': 'true',
        }
        if state:
            params['state'] = state
        return f'{self.AUTHORIZATION_URL}?{urlencode(params)}'

    def exchange_code(self, code: str) -> dict:
        data = {
            'code': unquote(code),
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri,
            'grant_type': 'authorization_code',
        }
        try:
            client = self._client()
            try:
                resp = client.post(self.TOKEN_URL, data=data)
            finally:
                if self._http is None:
                    client.close()
        except httpx.HTTPError as exc:
            raise GoogleOAuthError(f'Token exchange transport error: {exc}') from exc
        return resp.json()

    def refresh_token(self, refresh_token: str) -> dict:
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
        }
        client = self._client()
        try:
            resp = client.post(self.TOKEN_URL, data=data)
        finally:
            if self._http is None:
                client.close()
        return resp.json()

    def get_user_info(self, access_token: str) -> dict:
        headers = {'Authorization': f'Bearer {access_token}'}
        client = self._client()
        try:
            resp = client.get(self.USER_INFO_URL, headers=headers)
        finally:
            if self._http is None:
                client.close()
        return resp.json()
