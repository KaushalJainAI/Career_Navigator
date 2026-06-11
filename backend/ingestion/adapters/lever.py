"""Lever public postings adapter.

Lever exposes a free JSON endpoint per company-site:
    https://api.lever.co/v0/postings/{site}?mode=json
We iterate over sites configured in settings.LEVER_TOKENS."""

from __future__ import annotations

from typing import Iterable

import httpx
from django.conf import settings

from .base import AdapterContext, BaseAdapter, looks_remote, make_posting, parse_epoch_ms


class LeverAdapter(BaseAdapter):
    source_name = 'lever'
    source_kind = 'ats_public'
    base_url = 'https://api.lever.co/v0/postings'

    def __init__(self, tokens: list[str] | None = None,
                 transport: httpx.BaseTransport | None = None):
        super().__init__(transport)
        self.tokens = tokens if tokens is not None else settings.LEVER_TOKENS

    def fetch(self, ctx: AdapterContext) -> Iterable[dict]:
        with self.http_client() as client:
            for token in self.tokens:
                payload = self.get_json(client, f'{self.base_url}/{token}',
                                        params={'mode': 'json'})
                for row in payload or []:
                    yield self._normalise(row, token)

    @staticmethod
    def _normalise(row: dict, site_token: str) -> dict:
        location = (row.get('categories') or {}).get('location', '')
        salary = row.get('salaryRange') or {}
        workplace = (row.get('workplaceType') or '').lower()
        return make_posting(
            external_id=row.get('id'),
            title=row.get('text'),
            description=row.get('descriptionPlain') or row.get('description', ''),
            location=location,
            remote=workplace == 'remote' or looks_remote(location),
            salary_min=salary.get('min'),
            salary_max=salary.get('max'),
            salary_currency=salary.get('currency'),
            apply_url=row.get('applyUrl') or row.get('hostedUrl'),
            posted_at=parse_epoch_ms(row.get('createdAt')),
            company_name=site_token.replace('-', ' ').title(),
            ats_type='lever',
            raw=row,
        )
