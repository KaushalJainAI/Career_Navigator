from django.conf import settings
from django.db import models

from jobs.models import JobPosting


class Channel(models.TextChoices):
    EMAIL = 'email', 'Email'
    WEBPUSH = 'webpush', 'Web Push'
    IN_APP = 'in_app', 'In-app'


class Subscription(models.Model):
    """A user's saved-search → alert subscription. `filter_json` is the DSL the
    `match_filter()` helper compares against incoming JobPosting rows."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscriptions')
    name = models.CharField(max_length=255, default='My alerts')
    filter_json = models.JSONField(default=dict, blank=True)
    channels = models.JSONField(default=list, blank=True)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class WebPushDevice(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='push_devices')
    endpoint = models.URLField(max_length=1000)
    auth = models.CharField(max_length=255)
    p256dh = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # One row per browser subscription; re-registering updates it in place.
        unique_together = [('user', 'endpoint')]


class Alert(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='alerts')
    job = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='alerts')
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='alerts')
    channel = models.CharField(max_length=16, choices=Channel.choices)
    sent_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    class Meta:
        unique_together = [('user', 'job', 'channel')]
