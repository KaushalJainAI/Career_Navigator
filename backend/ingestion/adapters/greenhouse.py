"""Greenhouse public boards adapter.

Greenhouse exposes a free JSON endpoint per company-token:
    https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true
We iterate over tokens configured in settings.GREENHOUSE_TOKENS."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

import httpx
from django.conf import settings

from .base import AdapterContext, BaseAdapter


class GreenhouseAdapter(BaseAdapter):
    source_name = 'greenhouse'
    source_kind = 'ats_public'

    def __init__(self, tokens: list[str] | None = None):
        self.tokens = tokens if tokens is not None else settings.GREENHOUSE_TOKENS

    def fetch(self, ctx: AdapterContext) -> Iterable[dict]:
        if not self.tokens:
            return
        with httpx.Client(timeout=20.0) as client:
            for token in self.tokens:
                url = f'https://boards-api.greenhouse.io/v1/boards/{token}/jobs'
                r = client.get(url, params={'content': 'true'})
                if r.status_code != 200:
                    continue
                payload = r.json()
                for row in payload.get('jobs', []):
                    yield self._normalise(row, token)

    @staticmethod
    def _normalise(row: dict, board_token: str) -> dict:
        location = (row.get('location') or {}).get('name', '')
        return {
            'external_id': str(row.get('id')),
            'title': row.get('title', '').strip(),
            'description': row.get('content', ''),
            'location': location,
            'remote': 'remote' in location.lower(),
            'salary_min': None,
            'salary_max': None,
            'salary_currency': '',
            'apply_url': row.get('absolute_url', ''),
            'posted_at': _parse_dt(row.get('updated_at')),
            'company': {
                'name': board_token.replace('-', ' ').title(),
                'domain': '',
                'ats_type': 'greenhouse',
            },
            'raw': row,
        }


def _parse_dt(val):
    if not val:
        return None
    try:
        return datetime.fromisoformat(val.replace('Z', '+00:00'))
    except Exception:  # noqa: BLE001
        return None
