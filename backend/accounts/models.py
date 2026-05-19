from django.conf import settings
from django.db import models


class Tier(models.TextChoices):
    GUEST = 'guest', 'Guest'
    FREE = 'free', 'Free'
    PRO = 'pro', 'Pro'
    ENTERPRISE = 'enterprise', 'Enterprise'


class UserProfile(models.Model):
    """One-to-one extension of the Django User with Career Navigator metadata."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cn_profile'
    )
    tier = models.CharField(max_length=16, choices=Tier.choices, default=Tier.FREE)
    nvidia_guest_key_issued = models.BooleanField(default=False)
    credits_remaining = models.IntegerField(default=0)
    stealth_domains = models.JSONField(
        default=list,
        blank=True,
        help_text='Company domains to NEVER ingest/notify (e.g. current employer).',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f'{self.user} ({self.tier})'

    @property
    def is_paid(self) -> bool:
        return self.tier in {Tier.PRO, Tier.ENTERPRISE}


class GuestSession(models.Model):
    """Anonymous session granted access to the NVIDIA NIM guest pool."""

    session_key = models.CharField(max_length=64, unique=True, db_index=True)
    tokens_used = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
