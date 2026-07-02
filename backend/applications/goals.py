"""Live progress for a Goal, computed from the real application pipeline.

Built-in metrics read the user's applications inside the goal's period window;
`custom` goals fall back to the manually-tracked counter.
"""
from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from .models import ApplicationStatus, Goal

INTERVIEW_STATUSES = [ApplicationStatus.PHONE, ApplicationStatus.ONSITE, ApplicationStatus.OFFER]


def _window_start(period: str):
    """Start of the goal's period, or None for all-time."""
    now = timezone.now()
    if period == Goal.Period.WEEK:
        monday = now - timedelta(days=now.weekday())
        return monday.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == Goal.Period.MONTH:
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return None


def goal_progress(goal: Goal) -> int:
    """Current count toward the goal's target."""
    if goal.metric == Goal.Metric.CUSTOM:
        return goal.manual_progress

    apps = goal.user.applications.all()
    start = _window_start(goal.period)

    if goal.metric == Goal.Metric.APPLICATIONS:
        qs = apps if start is None else apps.filter(created_at__gte=start)
        return qs.count()

    if goal.metric == Goal.Metric.INTERVIEWS:
        qs = apps.filter(status__in=INTERVIEW_STATUSES)
        if start is not None:
            qs = qs.filter(updated_at__gte=start)
        return qs.count()

    if goal.metric == Goal.Metric.OFFERS:
        qs = apps.filter(status=ApplicationStatus.OFFER)
        if start is not None:
            qs = qs.filter(updated_at__gte=start)
        return qs.count()

    return 0
