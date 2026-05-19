"""AES-GCM envelope encryption for stored secrets.
The master key is derived from settings.CREDENTIAL_ENCRYPTION_KEY (any string ≥ 1 char;
SHA-256 normalises it to 32 bytes). The ciphertext stored in the DB is
`base64(nonce || tag || ciphertext)` so a single column suffices."""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings


def _key() -> bytes:
    raw = (settings.CREDENTIAL_ENCRYPTION_KEY or '').encode()
    if not raw:
        raise RuntimeError('CREDENTIAL_ENCRYPTION_KEY is not configured')
    return hashlib.sha256(raw).digest()


def encrypt(plaintext: str) -> str:
    aes = AESGCM(_key())
    nonce = os.urandom(12)
    ct = aes.encrypt(nonce, plaintext.encode('utf-8'), None)
    return base64.b64encode(nonce + ct).decode('ascii')


def decrypt(token: str) -> str:
    blob = base64.b64decode(token.encode('ascii'))
    nonce, ct = blob[:12], blob[12:]
    aes = AESGCM(_key())
    return aes.decrypt(nonce, ct, None).decode('utf-8')
