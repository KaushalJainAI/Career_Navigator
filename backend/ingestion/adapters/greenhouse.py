"""Greenhouse public boards adapter.

Greenhouse exposes a free JSON endpoint per company-token:
    https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true
We iterate over tokens configured in settings.GREENHOUSE_TOKENS."""

from __future__ import annotations

from typing import Iterable

import httpx
from django.conf import settings

from .base import AdapterContext, BaseAdapter, looks_remote, make_posting, parse_iso_dt


class GreenhouseAdapter(BaseAdapter):
    source_name = 'greenhouse'
    source_kind = 'ats_public'
    base_url = 'https://boards-api.greenhouse.io/v1/boards'

    def __init__(self, tokens: list[str] | None = None,
                 transport: httpx.BaseTransport | None = None):
        super().__init__(transport)
        self.tokens = tokens if tokens is not None else settings.GREENHOUSE_TOKENS

    def fetch(self, ctx: AdapterContext) -> Iterable[dict]:
        with self.http_client() as client:
            for token in self.tokens:
                payload = self.get_json(client, f'{self.base_url}/{token}/jobs',
                                        params={'content': 'true'})
                for row in (payload or {}).get('jobs', []):
                    yield self._normalise(row, token)

    @staticmethod
    def _normalise(row: dict, board_token: str) -> dict:
        location = (row.get('location') or {}).get('name', '')
        return make_posting(
            external_id=row.get('id'),
            title=row.get('title'),
            description=row.get('content', ''),
            location=location,
            remote=looks_remote(location),
            apply_url=row.get('absolute_url'),
            posted_at=parse_iso_dt(row.get('updated_at')),
            company_name=board_token.replace('-', ' ').title(),
            ats_type='greenhouse',
            raw=row,
        )
