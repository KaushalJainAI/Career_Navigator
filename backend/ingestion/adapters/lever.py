"""Lever public postings adapter.

Lever exposes a free JSON endpoint per company-site:
    https://api.lever.co/v0/postings/{site}?mode=json
We iterate over sites configured in settings.LEVER_TOKENS."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

import httpx
from django.conf import settings

from .base import AdapterContext, BaseAdapter


class LeverAdapter(BaseAdapter):
    source_name = 'lever'
    source_kind = 'ats_public'
    base_url = 'https://api.lever.co/v0/postings'

    def __init__(self, tokens: list[str] | None = None, transport: httpx.BaseTransport | None = None):
        self.tokens = tokens if tokens is not None else settings.LEVER_TOKENS
        self.transport = transport

    def fetch(self, ctx: AdapterContext) -> Iterable[dict]:
        if not self.tokens:
            return
        with httpx.Client(timeout=20.0, transport=self.transport) as client:
            for token in self.tokens:
                r = client.get(f'{self.base_url}/{token}', params={'mode': 'json'})
                if r.status_code != 200:
                    continue
                for row in r.json():
                    yield self._normalise(row, token)

    @staticmethod
    def _normalise(row: dict, site_token: str) -> dict:
        categories = row.get('categories') or {}
        location = categories.get('location', '') or ''
        workplace = (row.get('workplaceType') or '').lower()
        salary = row.get('salaryRange') or {}
        return {
            'external_id': str(row.get('id')),
            'title': (row.get('text') or '').strip(),
            'description': row.get('descriptionPlain') or row.get('description', '') or '',
            'location': location,
            'remote': workplace == 'remote' or 'remote' in location.lower(),
            'salary_min': int(salary['min']) if salary.get('min') else None,
            'salary_max': int(salary['max']) if salary.get('max') else None,
            'salary_currency': salary.get('currency', '') or '',
            'apply_url': row.get('applyUrl') or row.get('hostedUrl', '') or '',
            'posted_at': _parse_ms(row.get('createdAt')),
            'company': {
                'name': site_token.replace('-', ' ').title(),
                'domain': '',
                'ats_type': 'lever',
            },
            'raw': row,
        }


def _parse_ms(val):
    """Lever timestamps are epoch milliseconds."""
    if not val:
        return None
    try:
        return datetime.fromtimestamp(int(val) / 1000, tz=timezone.utc)
    except Exception:  # noqa: BLE001
        return None
