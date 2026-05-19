from django.conf import settings
from django.db import models


class AgentSession(models.Model):
    """A conversation / agent run owned by a user.
    The same model backs onboarding chat, the interview agent, and the general agent."""

    KIND_CHOICES = [
        ('onboarding', 'Onboarding'),
        ('general', 'General'),
        ('tailoring', 'Tailoring'),
        ('autonomous_apply', 'Autonomous Apply'),
    ]
    STATUS_CHOICES = [
        ('active', 'active'),
        ('paused_hitl', 'paused-hitl'),
        ('done', 'done'),
        ('failed', 'failed'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='agent_sessions')
    kind = models.CharField(max_length=32, choices=KIND_CHOICES, default='general')
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='active')
    state = models.JSONField(default=dict, blank=True)
    pending_approval = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class AgentMessage(models.Model):
    ROLE_CHOICES = [
        ('user', 'user'),
        ('assistant', 'assistant'),
        ('tool', 'tool'),
        ('system', 'system'),
    ]
    session = models.ForeignKey(AgentSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    content = models.TextField(blank=True)
    tool_calls = models.JSONField(default=list, blank=True)
    tool_name = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
