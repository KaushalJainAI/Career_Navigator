from django.db import models

from jobs.models import Source


class IngestionRun(models.Model):
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name='runs')
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=[('running', 'running'), ('success', 'success'), ('failed', 'failed')],
        default='running',
    )
    stats = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ['-started_at']
