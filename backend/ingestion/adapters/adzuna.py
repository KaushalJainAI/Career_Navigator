"""Adzuna aggregator adapter — official API, no scraping."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

import httpx
from django.conf import settings

from .base import AdapterContext, BaseAdapter


class AdzunaAdapter(BaseAdapter):
    source_name = 'adzuna'
    source_kind = 'aggregator'
    base_url = 'https://api.adzuna.com/v1/api/jobs'

    def __init__(self, country: str = 'us', app_id: str | None = None, app_key: str | None = None):
        self.country = country
        self.app_id = app_id or settings.ADZUNA_APP_ID
        self.app_key = app_key or settings.ADZUNA_APP_KEY

    def fetch(self, ctx: AdapterContext) -> Iterable[dict]:
        if not (self.app_id and self.app_key):
            return
        with httpx.Client(timeout=20.0) as client:
            for page in range(1, ctx.max_pages + 1):
                url = f'{self.base_url}/{self.country}/search/{page}'
                params = {
                    'app_id': self.app_id,
                    'app_key': self.app_key,
                    'results_per_page': ctx.page_size,
                    'what': ctx.query,
                    'where': ctx.location,
                    'content-type': 'application/json',
                }
                r = client.get(url, params=params)
                if r.status_code != 200:
                    break
                payload = r.json()
                results = payload.get('results', [])
                if not results:
                    break
                for row in results:
                    yield self._normalise(row)

    @staticmethod
    def _normalise(row: dict) -> dict:
        company = (row.get('company') or {}).get('display_name') or 'Unknown'
        loc = (row.get('location') or {}).get('display_name', '')
        salary_min = row.get('salary_min')
        salary_max = row.get('salary_max')
        return {
            'external_id': str(row.get('id')),
            'title': row.get('title', '').strip(),
            'description': row.get('description', ''),
            'location': loc,
            'remote': 'remote' in (row.get('title', '') + ' ' + loc).lower(),
            'salary_min': int(salary_min) if salary_min else None,
            'salary_max': int(salary_max) if salary_max else None,
            'salary_currency': row.get('salary_currency', '') or '',
            'apply_url': row.get('redirect_url', ''),
            'posted_at': _parse_dt(row.get('created')),
            'company': {'name': company, 'domain': '', 'ats_type': 'other'},
            'raw': row,
        }


def _parse_dt(val):
    if not val:
        return None
    try:
        return datetime.fromisoformat(val.replace('Z', '+00:00'))
    except Exception:  # noqa: BLE001
        return None
