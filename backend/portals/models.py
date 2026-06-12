"""Models for the portal-automation app.

`PortalAccount.storage_state` is the only place a user's portal session lives,
AES-GCM encrypted via the shared `credentials.crypto` helpers. It is write-only:
serializers accept it on write and never expose it on read.
"""

from __future__ import annotations

import json

from django.conf import settings
from django.db import models

from credentials.crypto import decrypt, encrypt


class Portal(models.Model):
    """A supported no-API portal (LinkedIn, Naukri, Unstop, YC)."""

    name = models.CharField(max_length=64, unique=True)
    display_name = models.CharField(max_length=128, blank=True)
    login_url = models.URLField(blank=True)
    enabled = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:
        return self.display_name or self.name


class PortalAccountStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    NEEDS_LOGIN = 'needs_login', 'Needs login'
    EXPIRED = 'expired', 'Expired'


class PortalAccount(models.Model):
    """A user's authenticated session for one portal — encrypted at rest."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='portal_accounts')
    portal = models.ForeignKey(Portal, on_delete=models.CASCADE, related_name='accounts')
    storage_state_ciphertext = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=PortalAccountStatus.choices,
                              default=PortalAccountStatus.NEEDS_LOGIN)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('user', 'portal')]

    def set_storage_state(self, state: dict) -> None:
        self.storage_state_ciphertext = encrypt(json.dumps(state))
        self.status = PortalAccountStatus.ACTIVE

    def reveal_storage_state(self) -> dict | None:
        if not self.storage_state_ciphertext:
            return None
        return json.loads(decrypt(self.storage_state_ciphertext))

    def has_session(self) -> bool:
        return bool(self.storage_state_ciphertext)


class PortalScrapeRun(models.Model):
    """One scrape attempt against a portal for a user. Mirrors IngestionRun."""

    STATUS_CHOICES = [
        ('running', 'running'),
        ('success', 'success'),
        ('needs_login', 'needs-login'),
        ('failed', 'failed'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='portal_scrape_runs')
    portal = models.ForeignKey(Portal, on_delete=models.CASCADE, related_name='runs')
    query = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='running')
    stats = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']
