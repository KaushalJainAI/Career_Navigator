"""Response-rate analytics over a user's applications.

A response is an application that reached an interview stage (phone screen or
beyond). Because `Application.status` only holds the *current* stage, we read
`status_changed` events too, so an application that progressed to a phone screen
and was later rejected still counts as a response. Pure function over an
iterable of Applications with prefetched events — deterministic and unit-tested.
"""

from __future__ import annotations

from .models import ApplicationStatus, AutoApplyTier

STATUS_RANK = {
    ApplicationStatus.SAVED: 0,
    ApplicationStatus.TAILORED: 1,
    ApplicationStatus.READY: 2,
    ApplicationStatus.APPLIED: 3,
    ApplicationStatus.PHONE: 4,
    ApplicationStatus.ONSITE: 5,
    ApplicationStatus.OFFER: 6,
}
RESPONSE_STATUSES = {ApplicationStatus.PHONE, ApplicationStatus.ONSITE, ApplicationStatus.OFFER}
APPLIED_RANK = STATUS_RANK[ApplicationStatus.APPLIED]
RESPONSE_RANK = STATUS_RANK[ApplicationStatus.PHONE]


def _peak_rank_and_first_response(app):
    """Highest funnel stage the application ever reached, and when it first hit
    an interview stage (from event history, falling back to nothing)."""
    ranks = []
    first_response_at = None
    if app.status in STATUS_RANK:
        ranks.append(STATUS_RANK[app.status])
    for event in app.events.all():
        if event.type != 'status_changed':
            continue
        status = (event.payload or {}).get('status')
        if status in STATUS_RANK:
            ranks.append(STATUS_RANK[status])
            if status in RESPONSE_STATUSES and first_response_at is None:
                first_response_at = event.created_at
    return (max(ranks) if ranks else 0), first_response_at


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def build_response_analytics(applications) -> dict:
    total = 0
    submitted = responses = offers = rejections = 0
    funnel = {'applied': 0, 'phone': 0, 'onsite': 0, 'offer': 0}
    by_tier: dict[str, dict] = {}
    response_days: list[int] = []

    for app in applications:
        total += 1
        peak, first_response_at = _peak_rank_and_first_response(app)
        tier = app.tier_used or AutoApplyTier.ASSIST
        tier_stats = by_tier.setdefault(tier, {'submitted': 0, 'responses': 0, 'offers': 0})

        if peak >= APPLIED_RANK:
            submitted += 1
            funnel['applied'] += 1
            tier_stats['submitted'] += 1
        if peak >= STATUS_RANK[ApplicationStatus.PHONE]:
            funnel['phone'] += 1
        if peak >= STATUS_RANK[ApplicationStatus.ONSITE]:
            funnel['onsite'] += 1
        if peak >= STATUS_RANK[ApplicationStatus.OFFER]:
            funnel['offer'] += 1
        if peak >= RESPONSE_RANK:
            responses += 1
            tier_stats['responses'] += 1
            if first_response_at is not None:
                response_days.append((first_response_at - app.created_at).days)
        if peak >= STATUS_RANK[ApplicationStatus.OFFER]:
            offers += 1
            tier_stats['offers'] += 1
        if app.status in (ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN):
            rejections += 1

    for tier_stats in by_tier.values():
        tier_stats['response_rate'] = _rate(tier_stats['responses'], tier_stats['submitted'])

    return {
        'total': total,
        'submitted': submitted,
        'responses': responses,
        'offers': offers,
        'rejections': rejections,
        'response_rate': _rate(responses, submitted),
        'offer_rate': _rate(offers, submitted),
        'funnel': funnel,
        'by_tier': by_tier,
        'avg_days_to_first_response': (
            round(sum(response_days) / len(response_days), 1) if response_days else None
        ),
    }
