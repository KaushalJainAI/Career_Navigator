from __future__ import annotations

from django.conf import settings
from django.core.mail import send_mail

from streaming.broadcaster import push_to_user

from .filters import match_filter
from .models import Alert, Channel, Subscription, WebPushDevice
from .webpush import send_web_push


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
    # In-app realtime nudge for every channel (cheap, same-origin websocket).
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
    elif alert.channel == Channel.WEBPUSH:
        _deliver_web_push(alert, payload)


def _deliver_web_push(alert: Alert, payload: dict) -> None:
    """Fan a job-alert push out to every browser the user has subscribed."""
    push_payload = {
        'title': f'New match: {alert.job.title}',
        'body': f'{payload["company"] or "New role"} · open to review and apply',
        'url': f'/jobs/{alert.job_id}',
        'tag': f'job-{alert.job_id}',
    }
    for device in WebPushDevice.objects.filter(user_id=alert.user_id):
        send_web_push(device, push_payload)
