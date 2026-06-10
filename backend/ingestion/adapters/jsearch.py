"""JSearch (RapidAPI) aggregator adapter — official API, no scraping.

GET https://jsearch.p.rapidapi.com/search with X-RapidAPI-Key header;
responds with {status, data: [job rows]} where rows carry Google-for-Jobs
style fields (job_title, employer_name, job_apply_link, ...)."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

import httpx
from django.conf import settings

from .base import AdapterContext, BaseAdapter


class JSearchAdapter(BaseAdapter):
    source_name = 'jsearch'
    source_kind = 'aggregator'
    base_url = 'https://jsearch.p.rapidapi.com/search'

    def __init__(self, api_key: str | None = None, transport: httpx.BaseTransport | None = None):
        self.api_key = api_key if api_key is not None else settings.JSEARCH_RAPIDAPI_KEY
        self.transport = transport

    def fetch(self, ctx: AdapterContext) -> Iterable[dict]:
        if not self.api_key:
            return
        headers = {
            'X-RapidAPI-Key': self.api_key,
            'X-RapidAPI-Host': 'jsearch.p.rapidapi.com',
        }
        query = ' '.join(part for part in (ctx.query, ctx.location) if part) or 'software engineer'
        with httpx.Client(timeout=20.0, transport=self.transport, headers=headers) as client:
            for page in range(1, ctx.max_pages + 1):
                r = client.get(self.base_url, params={'query': query, 'page': page, 'num_pages': 1})
                if r.status_code != 200:
                    break
                rows = r.json().get('data', [])
                if not rows:
                    break
                for row in rows:
                    yield self._normalise(row)

    @staticmethod
    def _normalise(row: dict) -> dict:
        location = ', '.join(part for part in (
            row.get('job_city'), row.get('job_state'), row.get('job_country'),
        ) if part)
        salary_min = row.get('job_min_salary')
        salary_max = row.get('job_max_salary')
        domain = (row.get('employer_website') or '').replace('https://', '').replace('http://', '').strip('/')
        return {
            'external_id': str(row.get('job_id')),
            'title': (row.get('job_title') or '').strip(),
            'description': row.get('job_description', '') or '',
            'location': location,
            'remote': bool(row.get('job_is_remote')),
            'salary_min': int(salary_min) if salary_min else None,
            'salary_max': int(salary_max) if salary_max else None,
            'salary_currency': row.get('job_salary_currency', '') or '',
            'apply_url': row.get('job_apply_link', '') or '',
            'posted_at': _parse_dt(row.get('job_posted_at_datetime_utc')),
            'company': {
                'name': (row.get('employer_name') or 'Unknown').strip() or 'Unknown',
                'domain': domain,
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
