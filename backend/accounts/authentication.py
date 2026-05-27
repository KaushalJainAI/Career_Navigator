"""DRF authentication class for the MV3 browser extension's long-lived API tokens.

Sits alongside JWT in DEFAULT_AUTHENTICATION_CLASSES so the same endpoints work
for both the web app (JWT) and the extension (API token)."""

from __future__ import annotations

from django.utils import timezone
from rest_framework import authentication, exceptions

from .models import APIToken

try:
    from drf_spectacular.extensions import OpenApiAuthenticationExtension
except ImportError:  # drf-spectacular is optional at import time
    OpenApiAuthenticationExtension = None  # type: ignore[assignment]


class APITokenAuthentication(authentication.BaseAuthentication):
    keyword = 'Token'

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).decode('latin-1')
        if not header:
            return None
        parts = header.split()
        if not parts or parts[0] != self.keyword:
            return None
        if len(parts) != 2:
            raise exceptions.AuthenticationFailed('Invalid token header.')
        cleartext = parts[1]
        token_hash = APIToken.hash_token(cleartext)
        token = (
            APIToken.objects.select_related('user')
            .filter(token_hash=token_hash, revoked_at__isnull=True)
            .first()
        )
        if token is None:
            raise exceptions.AuthenticationFailed('Invalid or revoked API token.')
        if not token.user.is_active:
            raise exceptions.AuthenticationFailed('User inactive.')
        # Best-effort last_used_at update; avoid full save() to keep this cheap.
        APIToken.objects.filter(pk=token.pk).update(last_used_at=timezone.now())
        return (token.user, token)

    def authenticate_header(self, request):
        return self.keyword


if OpenApiAuthenticationExtension is not None:

    class APITokenScheme(OpenApiAuthenticationExtension):
        target_class = 'accounts.authentication.APITokenAuthentication'
        name = 'APIToken'

        def get_security_definition(self, auto_schema):
            return {
                'type': 'apiKey',
                'in': 'header',
                'name': 'Authorization',
                'description': 'Long-lived API token. Header: `Authorization: Token <cleartext>`.',
            }
