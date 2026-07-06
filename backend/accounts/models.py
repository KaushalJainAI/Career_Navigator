import hashlib
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone


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


class PasswordResetOTP(models.Model):
    """Email OTP for password reset (ported from NGU).

    The code is stored *hashed* (never plaintext), expires 10 minutes after
    issue, and locks after ``MAX_FAILED_ATTEMPTS`` wrong guesses. Once verified,
    a one-time ``reset_token`` is issued that the confirm step exchanges for a
    password change — so the raw OTP is never replayed to set the password."""

    MAX_FAILED_ATTEMPTS = 5

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='password_reset_otps'
    )
    otp_code = models.CharField(max_length=255)
    reset_token = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    failed_attempts = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.user} OTP ({"used" if self.is_used else "pending"})'

    def set_otp(self, raw_otp: str) -> None:
        from django.contrib.auth.hashers import make_password
        self.otp_code = make_password(raw_otp)

    def check_otp(self, raw_otp: str) -> bool:
        from django.contrib.auth.hashers import check_password
        return check_password(raw_otp, self.otp_code)

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    @property
    def is_locked(self) -> bool:
        return self.failed_attempts >= self.MAX_FAILED_ATTEMPTS


class APIToken(models.Model):
    """Long-lived, revocable API token for the MV3 browser extension and other
    non-browser clients. Only the SHA-256 hash is persisted — the cleartext is
    shown to the user exactly once on creation."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='api_tokens'
    )
    name = models.CharField(max_length=64)
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    @staticmethod
    def hash_token(cleartext: str) -> str:
        return hashlib.sha256(cleartext.encode('utf-8')).hexdigest()

    @classmethod
    def issue(cls, *, user, name: str) -> tuple['APIToken', str]:
        cleartext = secrets.token_urlsafe(32)
        token = cls.objects.create(
            user=user, name=name[:64], token_hash=cls.hash_token(cleartext)
        )
        return token, cleartext

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None

    def revoke(self) -> None:
        if self.revoked_at is None:
            self.revoked_at = timezone.now()
            self.save(update_fields=['revoked_at'])

    def __str__(self) -> str:
        return f'{self.name} ({self.user})'
