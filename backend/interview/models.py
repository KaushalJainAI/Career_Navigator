from django.conf import settings
from django.db import models

from jobs.models import Company, JobPosting


class InterviewStage(models.TextChoices):
    RECRUITER = 'recruiter', 'Recruiter screen'
    TECH_PHONE = 'tech_phone', 'Technical phone'
    SYSTEM_DESIGN = 'system_design', 'System design'
    BEHAVIORAL = 'behavioral', 'Behavioral / onsite'
    ROLE_SPECIFIC = 'role_specific', 'Role-specific deep dive'


class InterviewSession(models.Model):
    """One grilling session. Backs both text mode (Phase 2) and voice mode (Phase 3)."""

    STATUS_CHOICES = [
        ('researching', 'researching'),
        ('ready', 'ready'),
        ('in_progress', 'in-progress'),
        ('done', 'done'),
        ('abandoned', 'abandoned'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='interview_sessions')
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)
    job = models.ForeignKey(JobPosting, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=255, blank=True)
    stage = models.CharField(max_length=32, choices=InterviewStage.choices, default=InterviewStage.BEHAVIORAL)
    difficulty = models.CharField(max_length=16, default='medium')
    research = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default='researching')
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']


class InterviewQuestion(models.Model):
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='questions')
    prompt = models.TextField()
    category = models.CharField(max_length=64, blank=True)
    difficulty = models.CharField(max_length=16, blank=True)
    expected_signals = models.JSONField(default=list, blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']


class InterviewTurn(models.Model):
    """One Q&A round: question asked, user's answer, AI evaluation."""

    question = models.ForeignKey(InterviewQuestion, on_delete=models.CASCADE, related_name='turns')
    user_answer = models.TextField(blank=True)
    evaluation = models.JSONField(default=dict, blank=True)
    score = models.FloatField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    drilldown_of = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name='drilldowns')
    created_at = models.DateTimeField(auto_now_add=True)


class InterviewReport(models.Model):
    session = models.OneToOneField(InterviewSession, on_delete=models.CASCADE, related_name='report')
    strengths = models.JSONField(default=list, blank=True)
    gaps = models.JSONField(default=list, blank=True)
    study_plan = models.JSONField(default=list, blank=True)
    overall_score = models.FloatField(null=True, blank=True)
    summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
