"""Credit accounting service.

All credit spends and grants funnel through here so the ledger stays the single
source of truth for a user's balance. Views should call :func:`charge` before
doing expensive AI work and let :class:`InsufficientCredits` (HTTP 402) bubble up
to DRF's exception handler.
"""
from __future__ import annotations

from django.db.models import Sum
from rest_framework.exceptions import APIException

from .models import CreditLedger
from .pricing import SIGNUP_BONUS, cost_of


class InsufficientCredits(APIException):
    """Raised by :func:`charge` when the balance can't cover an action.

    Rendered by DRF as HTTP 402 with a machine-readable body the frontend uses to
    prompt a top-up.
    """

    status_code = 402
    default_code = 'insufficient_credits'

    def __init__(self, reason: str, cost: int, balance: int):
        self.cost = cost
        self.balance = balance
        super().__init__({
            'detail': "You don't have enough credits for this action.",
            'code': 'insufficient_credits',
            'reason': reason,
            'cost': cost,
            'balance': balance,
            'shortfall': max(cost - balance, 0),
        })


def balance(user) -> int:
    """Current credit balance = sum of every ledger delta."""
    return CreditLedger.objects.filter(user=user).aggregate(total=Sum('delta'))['total'] or 0


def charge(user, reason: str, *, meta: dict | None = None) -> CreditLedger | None:
    """Deduct the cost of ``reason`` from ``user``.

    Free actions (cost 0) are a no-op and record nothing. Raises
    :class:`InsufficientCredits` if the balance is too low — call this *before*
    the expensive work so a broke user is never charged for a half-finished job.
    """
    cost = cost_of(reason)
    if cost <= 0:
        return None
    current = balance(user)
    if current < cost:
        raise InsufficientCredits(reason, cost, current)
    return CreditLedger.objects.create(user=user, delta=-cost, reason=reason, meta=meta or {})


def grant(user, reason: str, amount: int, *, meta: dict | None = None) -> CreditLedger:
    """Add ``amount`` credits to ``user`` (e.g. a top-up or refund)."""
    return CreditLedger.objects.create(user=user, delta=amount, reason=reason, meta=meta or {})


def grant_signup_bonus(user) -> CreditLedger | None:
    """Grant the one-time welcome bonus. Idempotent — safe to call more than once."""
    if CreditLedger.objects.filter(user=user, reason='signup_bonus').exists():
        return None
    return grant(user, 'signup_bonus', SIGNUP_BONUS, meta={'note': 'Welcome bonus'})
