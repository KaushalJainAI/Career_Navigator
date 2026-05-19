"""Helper to push a payload to a user's notifications group from anywhere
(Celery tasks, signals, DRF views). Falls back to a no-op if Channels is
not wired (e.g., in unit tests with InMemoryChannelLayer disabled)."""

from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def push_to_user(user_id: int, payload: dict) -> None:
    layer = get_channel_layer()
    if layer is None:
        return
    async_to_sync(layer.group_send)(
        f'user_{user_id}', {'type': 'notify', 'payload': payload}
    )


def push_to_interview(session_id: int, payload: dict) -> None:
    layer = get_channel_layer()
    if layer is None:
        return
    async_to_sync(layer.group_send)(
        f'interview_{session_id}', {'type': 'turn_event', 'payload': payload}
    )
