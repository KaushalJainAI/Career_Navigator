from django.conf import settings
from django.db import models


def resume_upload_path(instance, filename):
    return f'resumes/{instance.user_id}/{filename}'


class Resume(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='resumes')
    label = models.CharField(max_length=255, default='Master Resume')
    file = models.FileField(upload_to=resume_upload_path)
    parsed_json = models.JSONField(null=True, blank=True)
    is_master = models.BooleanField(default=False)
    parse_status = models.CharField(
        max_length=16,
        choices=[('pending', 'pending'), ('done', 'done'), ('failed', 'failed')],
        default='pending',
    )
    parse_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(is_master=True),
                name='one_master_resume_per_user',
            ),
        ]


class ResumeVersion(models.Model):
    """Immutable snapshot of a resume — used when an Application is created."""

    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='versions')
    parsed_json = models.JSONField()
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
