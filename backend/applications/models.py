import secrets

from django.conf import settings
from django.db import models

from jobs.models import JobPosting


class ApplicationStatus(models.TextChoices):
    SAVED = 'saved', 'Saved'
    TAILORED = 'tailored', 'Tailored'
    READY = 'ready', 'Ready to apply'
    APPLIED = 'applied', 'Applied'
    PHONE = 'phone', 'Phone screen'
    ONSITE = 'onsite', 'Onsite'
    OFFER = 'offer', 'Offer'
    REJECTED = 'rejected', 'Rejected'
    WITHDRAWN = 'withdrawn', 'Withdrawn'


class AutoApplyTier(models.TextChoices):
    ASSIST = 'assist', 'Assist only'
    AUTOFILL = 'autofill', 'Autofill (extension)'
    AUTONOMOUS = 'autonomous', 'Autonomous w/ approval'


class AutoApplySession(models.Model):
    """Coordinates an autonomous-apply run. Carries the approval token used to
    hard-gate `submit_application` in the agent."""

    STATE_CHOICES = [
        ('queued', 'queued'),
        ('running', 'running'),
        ('waiting_approval', 'waiting-approval'),
        ('done', 'done'),
        ('failed', 'failed'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='auto_apply_sessions')
    state = models.CharField(max_length=24, choices=STATE_CHOICES, default='queued')
    paused_reason = models.CharField(max_length=255, blank=True)
    approval_token = models.CharField(max_length=64, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def issue_approval_token(self) -> str:
        self.approval_token = secrets.token_urlsafe(32)
        self.state = 'waiting_approval'
        self.save(update_fields=['approval_token', 'state', 'updated_at'])
        return self.approval_token


class Application(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='applications')
    job = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='applications')
    status = models.CharField(max_length=24, choices=ApplicationStatus.choices,
                              default=ApplicationStatus.SAVED)
    tier_used = models.CharField(max_length=24, choices=AutoApplyTier.choices, blank=True)
    auto_apply_session = models.OneToOneField(
        AutoApplySession, null=True, blank=True, on_delete=models.SET_NULL, related_name='application'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('user', 'job')]
        ordering = ['-updated_at']


class ApplicationEvent(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='events')
    type = models.CharField(max_length=64)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
