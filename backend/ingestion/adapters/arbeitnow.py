"""Arbeitnow public job-board API (Europe-heavy, many remote roles, no key):
    https://www.arbeitnow.com/api/job-board-api?page=N"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

import httpx

from .base import AdapterContext, BaseAdapter, looks_remote, make_posting


class ArbeitnowAdapter(BaseAdapter):
    source_name = 'arbeitnow'
    source_kind = 'aggregator'
    base_url = 'https://www.arbeitnow.com/api/job-board-api'

    def __init__(self, transport: httpx.BaseTransport | None = None):
        super().__init__(transport)

    def fetch(self, ctx: AdapterContext) -> Iterable[dict]:
        with self.http_client() as client:
            for page in range(1, max(1, min(ctx.max_pages, 3)) + 1):
                payload = self.get_json(client, self.base_url, params={'page': page})
                rows = (payload or {}).get('data', [])
                if not rows:
                    break
                for row in rows:
                    created = row.get('created_at')
                    posted = datetime.fromtimestamp(created, tz=timezone.utc) if isinstance(created, (int, float)) else None
                    yield make_posting(
                        external_id=row.get('slug'),
                        title=row.get('title'),
                        description=row.get('description', ''),
                        location=row.get('location', ''),
                        remote=bool(row.get('remote')) or looks_remote(row.get('location')),
                        apply_url=row.get('url'),
                        posted_at=posted,
                        company_name=row.get('company_name'),
                        raw={k: row.get(k) for k in ('slug', 'tags', 'job_types')},
                    )
