from django.db import models

from applications.models import Application


class TailoredResume(models.Model):
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='tailored_resume')
    content = models.JSONField()
    diff_from_master = models.JSONField(default=dict, blank=True)
    model_used = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class CoverLetter(models.Model):
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='cover_letter')
    content = models.TextField()
    model_used = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
