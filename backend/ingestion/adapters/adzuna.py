"""Adzuna aggregator adapter — official API, no scraping."""

from __future__ import annotations

import logging
from typing import Iterable

import httpx
from django.conf import settings

from .base import AdapterContext, BaseAdapter, looks_remote, make_posting, parse_iso_dt

logger = logging.getLogger(__name__)


class AdzunaAdapter(BaseAdapter):
    source_name = 'adzuna'
    source_kind = 'aggregator'
    base_url = 'https://api.adzuna.com/v1/api/jobs'

    def __init__(self, country: str = 'us', app_id: str | None = None,
                 app_key: str | None = None, transport: httpx.BaseTransport | None = None):
        super().__init__(transport)
        self.country = country
        self.app_id = app_id if app_id is not None else settings.ADZUNA_APP_ID
        self.app_key = app_key if app_key is not None else settings.ADZUNA_APP_KEY

    def fetch(self, ctx: AdapterContext) -> Iterable[dict]:
        if not (self.app_id and self.app_key):
            logger.info('adzuna: skipped, ADZUNA_APP_ID/ADZUNA_APP_KEY not configured')
            return
        with self.http_client() as client:
            for page in range(1, ctx.max_pages + 1):
                payload = self.get_json(client, f'{self.base_url}/{self.country}/search/{page}', params={
                    'app_id': self.app_id,
                    'app_key': self.app_key,
                    'results_per_page': ctx.page_size,
                    'what': ctx.query,
                    'where': ctx.location,
                    'content-type': 'application/json',
                })
                results = (payload or {}).get('results', [])
                if not results:
                    break
                for row in results:
                    yield self._normalise(row)

    @staticmethod
    def _normalise(row: dict) -> dict:
        location = (row.get('location') or {}).get('display_name', '')
        return make_posting(
            external_id=row.get('id'),
            title=row.get('title'),
            description=row.get('description', ''),
            location=location,
            remote=looks_remote(row.get('title'), location),
            salary_min=row.get('salary_min'),
            salary_max=row.get('salary_max'),
            salary_currency=row.get('salary_currency'),
            apply_url=row.get('redirect_url'),
            posted_at=parse_iso_dt(row.get('created')),
            company_name=(row.get('company') or {}).get('display_name'),
            raw=row,
        )
