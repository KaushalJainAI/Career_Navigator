"""Session resolution for portal scraping.

Order of precedence:
1. the user's stored `PortalAccount` (AES-GCM encrypted Playwright storage_state);
2. an env-provided session cookie (`<PORTAL>_SESSION_COOKIE`), mapped to the
   right cookie name/domain via the registry — lets a single-operator deploy run
   before the per-user session UI exists;
3. nothing → the caller turns this into a clean `needs_login` run.

We deliberately accept a *session cookie*, not a password: the agent acts inside
a session the human already established, never a shared scraping account.
"""

from __future__ import annotations

from django.conf import settings

from .models import PortalAccount
from .registry import PORTALS, PortalSpec


def _state_from_cookie(spec: PortalSpec, cookie_value: str) -> dict:
    return {
        'cookies': [{
            'name': spec.cookie_name,
            'value': cookie_value,
            'domain': spec.cookie_domain,
            'path': '/',
            'httpOnly': True,
            'secure': True,
        }],
        'origins': [],
    }


def env_cookie_for(portal_name: str) -> str:
    return (getattr(settings, 'PORTAL_SESSION_COOKIES', {}) or {}).get(portal_name, '') or ''


def load_storage_state(user, portal_name: str) -> dict | None:
    """Resolve a Playwright storage_state for (user, portal), or None."""
    spec = PORTALS.get(portal_name)
    if spec is None:
        return None

    account = PortalAccount.objects.filter(
        user=user, portal__name=portal_name,
    ).select_related('portal').first()
    if account and account.has_session():
        return account.reveal_storage_state()

    cookie = env_cookie_for(portal_name)
    if cookie:
        return _state_from_cookie(spec, cookie)
    return None
