"""Web Push (VAPID) delivery.

Thin wrapper over ``pywebpush`` that fails soft: a dead subscription (HTTP 404/410)
is pruned, any other error is logged, and delivery never raises into the alert
pipeline. Push is a no-op until VAPID keys are configured, so dev/CI stay quiet.
"""
from __future__ import annotations

import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def push_enabled() -> bool:
    return bool(settings.VAPID_PRIVATE_KEY and settings.VAPID_PUBLIC_KEY)


def send_web_push(device, payload: dict) -> bool:
    """Deliver one push. Returns True on success; prunes the device on 404/410."""
    if not push_enabled():
        return False

    from pywebpush import WebPushException, webpush

    try:
        webpush(
            subscription_info={
                'endpoint': device.endpoint,
                'keys': {'auth': device.auth, 'p256dh': device.p256dh},
            },
            data=json.dumps(payload),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={'sub': settings.VAPID_CLAIM_EMAIL},
            timeout=10,
        )
        return True
    except WebPushException as exc:
        status = getattr(getattr(exc, 'response', None), 'status_code', None)
        if status in (404, 410):
            # Subscription is gone (user cleared it / it expired) — stop pushing to it.
            device.delete()
        else:
            logger.warning('web push delivery failed (status=%s)', status)
        return False
    except Exception:  # never let a push crash the alert pipeline
        logger.exception('unexpected web push error')
        return False
