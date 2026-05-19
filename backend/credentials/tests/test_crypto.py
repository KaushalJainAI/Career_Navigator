import pytest

from credentials.crypto import decrypt, encrypt
from credentials.models import Credential

pytestmark = pytest.mark.django_db


def test_roundtrip():
    token = encrypt('sk-secret-123')
    assert token != 'sk-secret-123'
    assert decrypt(token) == 'sk-secret-123'


def test_two_encryptions_differ_nonce():
    a = encrypt('hello')
    b = encrypt('hello')
    assert a != b
    assert decrypt(a) == decrypt(b) == 'hello'


def test_credential_set_and_reveal(user):
    cred = Credential(user=user, provider='openrouter', label='default')
    cred.set_secret('sk-or-xxx')
    cred.save()
    fresh = Credential.objects.get(pk=cred.pk)
    assert fresh.reveal() == 'sk-or-xxx'
    assert 'sk-or-xxx' not in fresh.ciphertext
