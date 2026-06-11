from django.conf import settings
from django.db import models

from jobs.models import JobPosting


class MatchScore(models.Model):
    """Cached match score between one user (their master resume) and one job."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='match_scores')
    job = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='match_scores')
    score = models.FloatField()
    breakdown = models.JSONField(default=dict, blank=True)
    gaps = models.JSONField(default=list, blank=True)
    matched_skills = models.JSONField(default=list, blank=True)
    explanation = models.JSONField(default=list, blank=True)
    model_version = models.CharField(max_length=64, default='v1')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('user', 'job')]
        indexes = [models.Index(fields=['user', '-score'])]
