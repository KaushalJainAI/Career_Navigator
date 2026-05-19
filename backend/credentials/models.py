from django.conf import settings
from django.db import models

from .crypto import decrypt, encrypt


class Credential(models.Model):
    """Encrypted-at-rest secret for an external provider (OpenRouter, OpenAI, …).
    The plaintext is never exposed to API clients — only injected into tool calls."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='credentials')
    provider = models.CharField(max_length=64)
    label = models.CharField(max_length=128, blank=True)
    ciphertext = models.TextField()
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [('user', 'provider', 'label')]

    def set_secret(self, plaintext: str) -> None:
        self.ciphertext = encrypt(plaintext)

    def reveal(self) -> str:
        return decrypt(self.ciphertext)
