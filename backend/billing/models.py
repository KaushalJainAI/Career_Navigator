from django.conf import settings
from django.db import models


class CreditLedger(models.Model):
    REASONS = [
        ('signup_bonus', 'Signup bonus'),
        ('tailor_resume', 'Tailored a resume'),
        ('cover_letter', 'Drafted a cover letter'),
        ('autonomous_apply', 'Autonomous apply'),
        ('mock_interview', 'Mock interview'),
        ('top_up', 'Manual top-up'),
        ('stripe_purchase', 'Stripe purchase'),
        ('refund', 'Refund'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='credit_ledger')
    delta = models.IntegerField()
    reason = models.CharField(max_length=32, choices=REASONS)
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class StripeSubscription(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='stripe_subscription')
    customer_id = models.CharField(max_length=128)
    subscription_id = models.CharField(max_length=128, blank=True)
    status = models.CharField(max_length=32, default='inactive')
    current_period_end = models.DateTimeField(null=True, blank=True)
