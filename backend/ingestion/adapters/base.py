"""Base adapter contract used by every job-discovery source.

Each adapter yields normalised dicts shaped like:

    {
        'external_id': str,
        'title': str,
        'description': str,
        'location': str,
        'remote': bool,
        'salary_min': int | None,
        'salary_max': int | None,
        'salary_currency': str,
        'apply_url': str,
        'posted_at': datetime | None,
        'company': {'name': str, 'domain': str, 'ats_type': str},
        'raw': dict,
    }

The `run()` method on an adapter returns an iterable of these dicts;
`upsert_postings()` (in ingestion.services) maps them to JobPosting rows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass
class AdapterContext:
    """Per-run config passed in from the caller (filters, page sizes, etc.)."""

    query: str = ''
    location: str = ''
    page_size: int = 50
    max_pages: int = 5
    extra: dict | None = None


class BaseAdapter:
    """Subclass and implement `fetch()`. Caller invokes `run()`."""

    source_name: str = ''
    source_kind: str = ''

    def fetch(self, ctx: AdapterContext) -> Iterable[dict]:  # pragma: no cover - abstract
        raise NotImplementedError

    def run(self, ctx: AdapterContext | None = None) -> list[dict]:
        return list(self.fetch(ctx or AdapterContext()))
