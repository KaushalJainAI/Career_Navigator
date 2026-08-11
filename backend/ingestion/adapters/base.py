"""Base adapter contract used by every job-discovery source.

Each adapter yields normalised dicts built by `make_posting()`:

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

The `run()` method on an adapter returns a list of these dicts;
`upsert_postings()` (in ingestion.services) maps them to JobPosting rows
and skips any row missing `external_id` or `title`.

Resilience rules shared by all adapters:
- every adapter accepts an injectable `transport` so tests use
  `httpx.MockTransport` and live runs get connect retries for free;
- a failed page/board request is logged and yields nothing instead of
  aborting the whole run, so one bad source unit cannot poison the rest.
  Each failure is also recorded on `adapter.request_errors` so the caller
  can tell "the source is broken" apart from "the source had no new jobs" —
  `run_adapter` turns a non-empty list into a `partial`/`failed` run;
- request failures are logged without the URL, because source URLs can
  embed API keys (e.g. Jooble).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

import httpx

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 20.0
CONNECT_RETRIES = 2


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

    def __init__(self, transport: httpx.BaseTransport | None = None):
        self.transport = transport
        # Request failures seen during the current run(). Populated by
        # _request_json; read by ingestion.services.run_adapter.
        self.request_errors: list[str] = []

    def fetch(self, ctx: AdapterContext) -> Iterable[dict]:  # pragma: no cover - abstract
        raise NotImplementedError

    def run(self, ctx: AdapterContext | None = None) -> list[dict]:
        self.request_errors = []
        return list(self.fetch(ctx or AdapterContext()))

    def http_client(self, **kwargs) -> httpx.Client:
        transport = self.transport or httpx.HTTPTransport(retries=CONNECT_RETRIES)
        return httpx.Client(timeout=DEFAULT_TIMEOUT, transport=transport, **kwargs)

    def get_json(self, client: httpx.Client, url: str, **kwargs) -> Any:
        return self._request_json(client, 'GET', url, **kwargs)

    def post_json(self, client: httpx.Client, url: str, **kwargs) -> Any:
        return self._request_json(client, 'POST', url, **kwargs)

    def _request_json(self, client: httpx.Client, method: str, url: str, **kwargs) -> Any:
        """Issue a request and parse JSON; on any failure log and return None."""
        try:
            response = client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            # Never include the URL: source URLs can embed API keys (Jooble).
            self._record_error(f'HTTP {exc.response.status_code}')
        except (httpx.HTTPError, ValueError) as exc:
            self._record_error(type(exc).__name__)
        return None

    def _record_error(self, detail: str) -> None:
        logger.warning('%s: request failed: %s', self.source_name, detail)
        self.request_errors.append(detail)


def make_posting(*, external_id, title, description='', location='', remote=False,
                 salary_min=None, salary_max=None, salary_currency='',
                 apply_url='', posted_at=None, company_name='', company_domain='',
                 ats_type='other', raw=None) -> dict:
    """Build a posting dict in the canonical shape, coercing blank/odd values.

    Rows that still come out without `external_id` or `title` are dropped
    by `upsert_postings()`, so adapters never need their own validation.
    """
    return {
        'external_id': str(external_id or '').strip(),
        'title': str(title or '').strip(),
        'description': description or '',
        'location': location or '',
        'remote': bool(remote),
        'salary_min': to_int(salary_min),
        'salary_max': to_int(salary_max),
        'salary_currency': salary_currency or '',
        'apply_url': apply_url or '',
        'posted_at': posted_at,
        'company': {
            'name': str(company_name or '').strip() or 'Unknown',
            'domain': company_domain or '',
            'ats_type': ats_type or 'other',
        },
        'raw': raw if raw is not None else {},
    }


def looks_remote(*texts: str | None) -> bool:
    return 'remote' in ' '.join(t or '' for t in texts).lower()


def to_int(val) -> int | None:
    if not val:
        return None
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return None


def parse_iso_dt(val) -> datetime | None:
    """Parse an ISO-8601 string into an aware UTC datetime.

    Sources are inconsistent about offsets (Jooble's `updated` carries none),
    and a naive value would be stored under Django's USE_TZ with a warning and
    an implicit-UTC guess. Ghost-risk scoring keys off posting age, so assume
    UTC explicitly rather than letting it happen silently."""
    if not val:
        return None
    try:
        parsed = datetime.fromisoformat(str(val).replace('Z', '+00:00'))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def parse_epoch_ms(val) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.fromtimestamp(int(val) / 1000, tz=timezone.utc)
    except (TypeError, ValueError, OSError, OverflowError):
        return None
