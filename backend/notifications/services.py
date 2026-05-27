from __future__ import annotations

from django.conf import settings
from django.core.mail import send_mail

from streaming.broadcaster import push_to_user

from .filters import match_filter
from .models import Alert, Channel, Subscription


def deliver_job_alert(job) -> list[Alert]:
    """Create and deliver job alerts for every matching enabled subscription."""

    delivered: list[Alert] = []
    subscriptions = Subscription.objects.filter(enabled=True).select_related('user')
    for subscription in subscriptions:
        if not match_filter(job, subscription.filter_json or {}):
            continue
        channels = subscription.channels or [Channel.IN_APP]
        for channel in channels:
            alert, created = Alert.objects.get_or_create(
                user=subscription.user,
                job=job,
                subscription=subscription,
                channel=channel,
            )
            if not created:
                continue
            delivered.append(alert)
            _deliver_channel(alert)
    return delivered


def _deliver_channel(alert: Alert) -> None:
    payload = {
        'type': 'job_alert',
        'id': alert.id,
        'channel': alert.channel,
        'title': alert.job.title,
        'company': alert.job.company.name if alert.job.company_id else '',
        'job_id': alert.job_id,
    }
    push_to_user(alert.user_id, payload)
    if alert.channel == Channel.EMAIL and alert.user.email:
        send_mail(
            f'New job match: {alert.job.title}',
            (
                f'{alert.job.title} at {payload["company"]}\n\n'
                f'Location: {alert.job.location or "Not listed"}\n'
                f'Remote: {"Yes" if alert.job.remote else "No"}\n\n'
                'Open Career Navigator to review and apply.'
            ),
            settings.DEFAULT_FROM_EMAIL,
            [alert.user.email],
            fail_silently=True,
        )
