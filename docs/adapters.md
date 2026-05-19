# Job-Discovery Adapters

How to add a new job source. Read [ingestion/adapters/base.py](../backend/ingestion/adapters/base.py) alongside this.

## The contract

Every adapter subclasses `BaseAdapter` and implements `fetch(ctx: AdapterContext) -> Iterable[dict]`. It yields **normalised dicts** with this exact shape:

```python
{
    'external_id': str,            # adapter's stable id for this posting — REQUIRED
    'title':       str,            # REQUIRED
    'description': str,
    'location':    str,
    'remote':      bool,
    'salary_min':  int | None,
    'salary_max':  int | None,
    'salary_currency': str,        # ISO 4217 or ''
    'apply_url':   str,
    'posted_at':   datetime | None,  # timezone-aware
    'company': {
        'name': str,
        'domain': str,
        'ats_type': str,           # 'greenhouse' | 'lever' | 'workday' | 'smartrecruiters' | 'other'
    },
    'raw':         dict,           # original API payload, for debugging
}
```

Rows missing `external_id` or `title` are silently skipped by `upsert_postings` — that's how `_normalise` failures degrade gracefully.

## Existing adapters

| Adapter | Source kind | File | Auth |
|---|---|---|---|
| `AdzunaAdapter` | aggregator API | [ingestion/adapters/adzuna.py](../backend/ingestion/adapters/adzuna.py) | `ADZUNA_APP_ID` + `ADZUNA_APP_KEY` |
| `GreenhouseAdapter` | public ATS boards | [ingestion/adapters/greenhouse.py](../backend/ingestion/adapters/greenhouse.py) | none — iterates over `GREENHOUSE_TOKENS` |

Phase 2 adds:
- `JoobleAdapter`, `JSearchAdapter` (RapidAPI)
- `LeverAdapter` (public boards — same shape as Greenhouse, different endpoint)
- `PlaywrightScraperAdapter` (per-company custom scrapers; runs on the playwright Celery queue)
- `EmailForwardAdapter` (parses LinkedIn/Indeed digest emails forwarded to `apply@<domain>`)
- `WebSearchAdapter` (LLM-driven; returns candidate URLs that then go through the scraper)
- `CLIDelegateAdapter` (Faultline-style fallback: invokes Claude Code / Codex / Gemini CLI when no API is available)

## Writing a new adapter

1. Create `backend/ingestion/adapters/<name>.py`. Subclass `BaseAdapter`. Set class attributes `source_name`, `source_kind`.
2. Implement `fetch(self, ctx)`. Use `httpx.Client` synchronously — keep IO simple, the orchestrator parallelises across postings, not within a single source.
3. Write a static `_normalise(row, …)` helper that maps the raw payload to the contract dict. Put parsing edge-cases here so the I/O code stays minimal.
4. Register in `ADAPTER_REGISTRY` in [ingestion/tasks.py](../backend/ingestion/tasks.py). Choose the registry key carefully — it's what the Celery task accepts as `source_name`.
5. Add a `Source` row via `manage.py shell` or a fixture so beat can run it: `Source.objects.create(name='<name>', kind='<kind>')`.
6. Add unit tests in `backend/ingestion/tests/test_adapter_<name>.py`. **The normaliser must have a test with a real-shaped fixture row.** For HTTP, use `httpx.MockTransport`. We do not hit the network in tests, ever.

## Idempotency

`upsert_postings` (in [ingestion/services.py](../backend/ingestion/services.py)) does `update_or_create((source, external_id))`. Rerunning an adapter is safe: existing rows update in place, new rows create. The Company FK is reused via `get_or_create((name, domain))`. Don't bypass `upsert_postings` — adapters should never call `JobPosting.objects.create()` directly.

## Scheduling

Per-source schedules live in `django-celery-beat`. Default cadence:
- Aggregator APIs: every 30 minutes.
- Public ATS boards: every 60 minutes per company token.
- Playwright scrapers: every 4 hours (Phase 2; depends on per-company rate limits).
- Email-forward parser: triggered on receipt (Phase 2).

In dev with `RUN_INGESTION_ASYNC=False` you can trigger a one-off with:

```bash
python manage.py shell -c "from ingestion.tasks import run_source; print(run_source('adzuna', query='python', location='remote'))"
```

Or via the admin endpoint:

```
POST /api/v1/ingestion/run/<source_name>/    # IsAdminUser only
{"query": "python", "location": "remote", "max_pages": 3}
```

## Stealth-domain filter

`JobListView` already filters out postings whose `company.domain` matches `request.user.cn_profile.stealth_domains`. Adapters themselves don't need to know about stealth — the filter happens at read time, not write time. If you build a new list endpoint, replicate the pattern.

## ToS, rate limits, and ethics

- **Respect robots.txt** when adding scraper adapters. The Playwright queue should set `Robotparser` per host.
- **Identify yourself** with a User-Agent string like `Career-Navigator/0.1 (+https://career-navigator.example/bot)`.
- **Back off** on 429s — `httpx` raises; the Celery task should retry with exponential backoff (max 3, see Faultline's pattern).
- **LinkedIn** stays unofficial. Only operate on data the user provides (RSS feeds, forwarded emails, their own session cookie). Never use a shared scraping account.
- **Don't republish** the raw posting body verbatim outside the user's own view. The `raw` JSONField is for debugging, not for export.

## Future: the CLI-delegate adapter

When neither an API nor a scrape route works, we fall back to delegating a research task to a CLI tool (Faultline pattern). The adapter shape is the same — its `fetch()` shells out to `claude code` / `codex` / `gemini` with a structured prompt and parses the output. Code is not yet shipped; the design lives in the implementation plan.
