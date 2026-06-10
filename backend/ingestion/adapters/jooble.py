"""Jooble aggregator adapter — official POST API, no scraping.

Docs: https://jooble.org/api/about — POST https://jooble.org/api/{key}
with a JSON body of search filters; responds with {totalCount, jobs[]}."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

import httpx
from django.conf import settings

from .base import AdapterContext, BaseAdapter


class JoobleAdapter(BaseAdapter):
    source_name = 'jooble'
    source_kind = 'aggregator'
    base_url = 'https://jooble.org/api'

    def __init__(self, api_key: str | None = None, transport: httpx.BaseTransport | None = None):
        self.api_key = api_key if api_key is not None else settings.JOOBLE_API_KEY
        self.transport = transport

    def fetch(self, ctx: AdapterContext) -> Iterable[dict]:
        if not self.api_key:
            return
        with httpx.Client(timeout=20.0, transport=self.transport) as client:
            for page in range(1, ctx.max_pages + 1):
                r = client.post(f'{self.base_url}/{self.api_key}', json={
                    'keywords': ctx.query,
                    'location': ctx.location,
                    'page': page,
                })
                if r.status_code != 200:
                    break
                jobs = r.json().get('jobs', [])
                if not jobs:
                    break
                for row in jobs:
                    yield self._normalise(row)

    @staticmethod
    def _normalise(row: dict) -> dict:
        location = row.get('location', '') or ''
        title = row.get('title', '') or ''
        return {
            'external_id': str(row.get('id')),
            'title': title.strip(),
            'description': row.get('snippet', '') or '',
            'location': location,
            'remote': 'remote' in (title + ' ' + location).lower(),
            'salary_min': None,
            'salary_max': None,
            'salary_currency': '',
            'apply_url': row.get('link', '') or '',
            'posted_at': _parse_dt(row.get('updated')),
            'company': {
                'name': (row.get('company') or 'Unknown').strip() or 'Unknown',
                'domain': '',
                'ats_type': 'other',
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
