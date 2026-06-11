"""JSearch (RapidAPI) aggregator adapter — official API, no scraping.

GET https://jsearch.p.rapidapi.com/search with X-RapidAPI-Key header;
responds with {status, data: [job rows]} where rows carry Google-for-Jobs
style fields (job_title, employer_name, job_apply_link, ...)."""

from __future__ import annotations

import logging
from typing import Iterable
from urllib.parse import urlparse

import httpx
from django.conf import settings

from .base import AdapterContext, BaseAdapter, make_posting, parse_iso_dt

logger = logging.getLogger(__name__)


class JSearchAdapter(BaseAdapter):
    source_name = 'jsearch'
    source_kind = 'aggregator'
    base_url = 'https://jsearch.p.rapidapi.com/search'

    def __init__(self, api_key: str | None = None,
                 transport: httpx.BaseTransport | None = None):
        super().__init__(transport)
        self.api_key = api_key if api_key is not None else settings.JSEARCH_RAPIDAPI_KEY

    def fetch(self, ctx: AdapterContext) -> Iterable[dict]:
        if not self.api_key:
            logger.info('jsearch: skipped, JSEARCH_RAPIDAPI_KEY not configured')
            return
        headers = {
            'X-RapidAPI-Key': self.api_key,
            'X-RapidAPI-Host': 'jsearch.p.rapidapi.com',
        }
        query = ' '.join(part for part in (ctx.query, ctx.location) if part) or 'software engineer'
        with self.http_client(headers=headers) as client:
            for page in range(1, ctx.max_pages + 1):
                payload = self.get_json(client, self.base_url,
                                        params={'query': query, 'page': page, 'num_pages': 1})
                rows = (payload or {}).get('data', [])
                if not rows:
                    break
                for row in rows:
                    yield self._normalise(row)

    @staticmethod
    def _normalise(row: dict) -> dict:
        location = ', '.join(part for part in (
            row.get('job_city'), row.get('job_state'), row.get('job_country'),
        ) if part)
        return make_posting(
            external_id=row.get('job_id'),
            title=row.get('job_title'),
            description=row.get('job_description', ''),
            location=location,
            remote=bool(row.get('job_is_remote')),
            salary_min=row.get('job_min_salary'),
            salary_max=row.get('job_max_salary'),
            salary_currency=row.get('job_salary_currency'),
            apply_url=row.get('job_apply_link'),
            posted_at=parse_iso_dt(row.get('job_posted_at_datetime_utc')),
            company_name=row.get('employer_name'),
            company_domain=_domain(row.get('employer_website')),
            raw=row,
        )


def _domain(url: str | None) -> str:
    if not url:
        return ''
    return urlparse(url if '//' in url else f'//{url}').netloc
