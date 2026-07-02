"""Unified activity feed backing the notification bell.

Merges two streams into one time-sorted list:
  * job-match **alerts** (have a read/unread state), and
  * **application events** — status changes, tailored resume / cover-letter
    generation, autonomous-apply prep (informational).

Returns plain dicts (already datetime-serialised) plus an `unread` count of
unread alerts for the bell badge.
"""
from __future__ import annotations

from applications.models import ApplicationEvent, ApplicationStatus

from .models import Alert

STATUS_LABELS = dict(ApplicationStatus.choices)


def _subtitle(*parts) -> str:
    return ' · '.join(p for p in parts if p)


def _alert_item(a: Alert) -> dict:
    company = a.job.company.name if a.job.company_id else ''
    return {
        'key': f'alert-{a.id}',
        'kind': 'alert',
        'title': a.job.title or 'New job match',
        'subtitle': _subtitle('New match', company),
        'url': f'/jobs/{a.job_id}',
        'at': a.sent_at,
        'read': a.read,
        'alert_id': a.id,
    }


def _event_item(ev: ApplicationEvent) -> dict:
    job = ev.application.job
    company = job.company.name if job.company_id else ''
    role = job.title
    subtitle = _subtitle(company, role)
    t = ev.type

    if t == 'status_changed':
        status = (ev.payload or {}).get('status', '')
        label = STATUS_LABELS.get(status, status.title() if status else 'a new stage')
        item = {'kind': 'status', 'title': f'Moved to {label}', 'url': '/applications'}
    elif t == 'tailored_resume_generated':
        item = {'kind': 'material', 'title': 'Tailored resume generated', 'url': f'/jobs/{job.id}'}
    elif t == 'cover_letter_generated':
        item = {'kind': 'material', 'title': 'Cover letter drafted', 'url': f'/jobs/{job.id}'}
    elif t in ('approval_issued', 'autonomous_prepared'):
        item = {'kind': 'apply', 'title': 'Autonomous apply ready for approval', 'url': f'/jobs/{job.id}'}
    elif t.endswith('_prepared'):
        tier = t.replace('_prepared', '')
        item = {'kind': 'apply', 'title': f'Application prepared ({tier})', 'url': f'/jobs/{job.id}'}
    else:
        item = {'kind': 'activity', 'title': t.replace('_', ' ').capitalize(), 'url': '/applications'}

    return {
        'key': f'event-{ev.id}',
        'subtitle': subtitle,
        'at': ev.created_at,
        'read': True,  # events are informational, not dismissable
        **item,
    }


def build_activity(user, limit: int = 25) -> dict:
    alerts = list(
        Alert.objects.filter(user=user).select_related('job', 'job__company').order_by('-sent_at')[:limit]
    )
    events = list(
        ApplicationEvent.objects.filter(application__user=user)
        .select_related('application', 'application__job', 'application__job__company')
        .order_by('-created_at')[:limit]
    )

    items = [_alert_item(a) for a in alerts] + [_event_item(e) for e in events]
    items.sort(key=lambda x: (x['at'] is not None, x['at']), reverse=True)
    for it in items:
        it['at'] = it['at'].isoformat() if it['at'] else None

    return {
        'items': items[:limit],
        'unread': sum(1 for a in alerts if not a.read),
    }
