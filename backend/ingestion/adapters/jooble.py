"""Jooble aggregator adapter — official POST API, no scraping.

Docs: https://jooble.org/api/about — POST https://jooble.org/api/{key}
with a JSON body of search filters; responds with {totalCount, jobs[]}.
The API key rides in the URL, so request failures must never log it."""

from __future__ import annotations

import logging
from typing import Iterable

import httpx
from django.conf import settings

from .base import AdapterContext, BaseAdapter, looks_remote, make_posting, parse_iso_dt

logger = logging.getLogger(__name__)


class JoobleAdapter(BaseAdapter):
    source_name = 'jooble'
    source_kind = 'aggregator'
    base_url = 'https://jooble.org/api'

    def __init__(self, api_key: str | None = None,
                 transport: httpx.BaseTransport | None = None):
        super().__init__(transport)
        self.api_key = api_key if api_key is not None else settings.JOOBLE_API_KEY

    def fetch(self, ctx: AdapterContext) -> Iterable[dict]:
        if not self.api_key:
            logger.info('jooble: skipped, JOOBLE_API_KEY not configured')
            return
        with self.http_client() as client:
            for page in range(1, ctx.max_pages + 1):
                payload = self.post_json(client, f'{self.base_url}/{self.api_key}', json={
                    'keywords': ctx.query,
                    'location': ctx.location,
                    'page': page,
                })
                jobs = (payload or {}).get('jobs', [])
                if not jobs:
                    break
                for row in jobs:
                    yield self._normalise(row)

    @staticmethod
    def _normalise(row: dict) -> dict:
        location = row.get('location', '')
        return make_posting(
            external_id=row.get('id'),
            title=row.get('title'),
            description=row.get('snippet', ''),
            location=location,
            remote=looks_remote(row.get('title'), location),
            apply_url=row.get('link'),
            posted_at=parse_iso_dt(row.get('updated')),
            company_name=row.get('company'),
            raw=row,
        )
