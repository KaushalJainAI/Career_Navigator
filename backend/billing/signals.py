"""Grant the welcome credit bonus the moment a user account is created."""
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .services import grant_signup_bonus


@receiver(post_save, sender=settings.AUTH_USER_MODEL, dispatch_uid='billing_signup_bonus')
def award_signup_bonus(sender, instance, created, **kwargs):
    if created:
        grant_signup_bonus(instance)
