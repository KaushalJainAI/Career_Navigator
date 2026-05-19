"""Faultline-style dynamic auth flows for portal login (Workday/Greenhouse/Lever).
Phase 3 fleshes these out; Phase 1 lands the schema so the agent code can reference it."""

from django.conf import settings
from django.db import models


class AuthFlow(models.Model):
    portal = models.CharField(max_length=64, unique=True)
    steps = models.JSONField(
        help_text='Ordered list of steps: navigate, fill, click, wait_for, mfa_prompt, etc.'
    )
    description = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class PortalSession(models.Model):
    """Encrypted browser-state per (user, portal). Cookies live as a ciphertext blob."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='portal_sessions')
    auth_flow = models.ForeignKey(AuthFlow, on_delete=models.CASCADE, related_name='sessions')
    cookies_ciphertext = models.TextField()
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('user', 'auth_flow')]
