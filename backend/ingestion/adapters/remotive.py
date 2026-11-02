"""Remotive public API (remote jobs, no key):
    https://remotive.com/api/remote-jobs?search=<q>&limit=<n>
Remotive asks API users to link back to the original posting and not to hit
the endpoint more than a few times a day — we only call it on a user refresh."""

from __future__ import annotations

from typing import Iterable

import httpx

from .base import AdapterContext, BaseAdapter, make_posting, parse_iso_dt


class RemotiveAdapter(BaseAdapter):
    source_name = 'remotive'
    source_kind = 'aggregator'
    base_url = 'https://remotive.com/api/remote-jobs'

    def __init__(self, transport: httpx.BaseTransport | None = None):
        super().__init__(transport)

    def fetch(self, ctx: AdapterContext) -> Iterable[dict]:
        params = {'limit': min(ctx.page_size * max(ctx.max_pages, 1), 100)}
        if ctx.query:
            params['search'] = ctx.query
        with self.http_client() as client:
            payload = self.get_json(client, self.base_url, params=params)
            for row in (payload or {}).get('jobs', []):
                yield make_posting(
                    external_id=row.get('id'),
                    title=row.get('title'),
                    description=row.get('description', ''),
                    location=row.get('candidate_required_location') or 'Remote',
                    remote=True,
                    apply_url=row.get('url'),
                    posted_at=parse_iso_dt(row.get('publication_date')),
                    company_name=row.get('company_name'),
                    raw={k: row.get(k) for k in ('id', 'category', 'job_type', 'salary', 'tags')},
                )
