"""Email-OTP password reset flow: request → verify → confirm.

The OTP is read back out of the captured email (pytest-django's `mailoutbox`
fixture routes mail to an in-memory backend), since it's stored only hashed.
"""

import re
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from accounts.models import PasswordResetOTP

pytestmark = pytest.mark.django_db

REQUEST = 'auth-password-reset'
VERIFY = 'auth-password-reset-verify'
CONFIRM = 'auth-password-reset-confirm'


def _user(email='reset@example.com', password='OldPassw0rd!'):
    return get_user_model().objects.create_user(username=email, email=email, password=password)


def _code_from(mailoutbox):
    assert mailoutbox, 'no email was sent'
    return re.search(r'\b(\d{6})\b', mailoutbox[0].body).group(1)


def test_request_sends_code_and_creates_record(api_client, mailoutbox):
    user = _user()
    resp = api_client.post(reverse(REQUEST), {'email': user.email}, format='json')
    assert resp.status_code == 200
    assert PasswordResetOTP.objects.filter(user=user, is_used=False).count() == 1
    assert len(mailoutbox) == 1
    assert re.search(r'\b\d{6}\b', mailoutbox[0].body)


def test_request_is_enumeration_safe(api_client, mailoutbox):
    resp = api_client.post(reverse(REQUEST), {'email': 'nobody@example.com'}, format='json')
    assert resp.status_code == 200
    assert 'if that email exists' in resp.data['detail'].lower()
    assert PasswordResetOTP.objects.count() == 0
    assert mailoutbox == []


def test_full_flow_resets_password(api_client, mailoutbox):
    user = _user()
    api_client.post(reverse(REQUEST), {'email': user.email}, format='json')
    code = _code_from(mailoutbox)

    v = api_client.post(reverse(VERIFY), {'email': user.email, 'otp_code': code}, format='json')
    assert v.status_code == 200
    reset_token = v.data['reset_token']
    assert reset_token

    c = api_client.post(reverse(CONFIRM), {
        'email': user.email, 'reset_token': reset_token, 'new_password': 'BrandNewPass9!',
    }, format='json')
    assert c.status_code == 200

    user.refresh_from_db()
    assert user.check_password('BrandNewPass9!')
    # Token is burned — can't be replayed.
    record = PasswordResetOTP.objects.get(user=user)
    assert record.reset_token is None


def test_wrong_code_counts_down_then_locks(api_client, mailoutbox):
    user = _user()
    api_client.post(reverse(REQUEST), {'email': user.email}, format='json')

    for _ in range(PasswordResetOTP.MAX_FAILED_ATTEMPTS - 1):
        r = api_client.post(reverse(VERIFY), {'email': user.email, 'otp_code': '000000'}, format='json')
        assert r.status_code == 400
        assert 'attempt' in r.data['detail'].lower()
    # Final wrong attempt locks the OTP.
    r = api_client.post(reverse(VERIFY), {'email': user.email, 'otp_code': '000000'}, format='json')
    assert r.status_code == 429


def test_expired_code_is_rejected(api_client, mailoutbox):
    user = _user()
    api_client.post(reverse(REQUEST), {'email': user.email}, format='json')
    code = _code_from(mailoutbox)
    PasswordResetOTP.objects.filter(user=user).update(
        expires_at=timezone.now() - timedelta(minutes=1)
    )
    r = api_client.post(reverse(VERIFY), {'email': user.email, 'otp_code': code}, format='json')
    assert r.status_code == 400
    assert 'expired' in r.data['detail'].lower()


def test_confirm_rejects_bad_reset_token(api_client, mailoutbox):
    user = _user()
    api_client.post(reverse(REQUEST), {'email': user.email}, format='json')
    r = api_client.post(reverse(CONFIRM), {
        'email': user.email, 'reset_token': 'not-a-real-token', 'new_password': 'BrandNewPass9!',
    }, format='json')
    assert r.status_code == 400


def test_new_request_invalidates_previous_code(api_client, mailoutbox):
    user = _user()
    api_client.post(reverse(REQUEST), {'email': user.email}, format='json')
    first_code = _code_from(mailoutbox)
    api_client.post(reverse(REQUEST), {'email': user.email}, format='json')

    # The first code is now marked used; verifying it must fail.
    r = api_client.post(reverse(VERIFY), {'email': user.email, 'otp_code': first_code}, format='json')
    # Newest pending record holds a different code, so the old one won't match.
    assert r.status_code == 400
