# Dynamic Data Pipeline Plan

**Status:** proposed (not yet implemented). Author intent: replace the dummy/hardcoded
data the frontend currently shows with live data that is fetched from external sources,
stored in the database with freshness/expiry semantics, refreshed on a schedule, and
surfaced to each user as a personalized, ranked subset.

This document is the design we agreed on before writing code. Implementation is staged
in Phases A–E below.

---

## 0. Guiding decisions (the "why", read this first)

These three decisions shape the whole design. They intentionally diverge from the naive
"fetch fresh data per user and store it with an expiry" framing.

### 0.1 Fetch once into a shared pool; personalize at read time
Ingestion is **shared and impersonal**. We do **not** scrape per user. One canonical pool
of jobs is deduped by `(source, external_id)` (already true via
[`jobs.models.JobPosting`](../backend/jobs/models.py) + `ingestion.services.upsert_postings`).
Personalization is a **separate, cheap, per-user pass** over that shared pool.

Rationale: per-user scraping multiplies cost, rate-limit exposure, and ban risk by the
number of users for near-identical queries. Shared ingestion + per-user ranking scales.

### 0.2 "Expiry" is two clocks, not one
- **Re-fetch cadence (freshness):** how often we re-poll a *source*. A per-source setting,
  not a per-row one. Aggregator APIs: frequent (e.g. hourly). Expensive scrapers: sparse
  (e.g. daily).
- **Posting liveness:** is this specific job still open? Detected by **absence** — if a
  source stops returning a posting it used to return, mark it expired. Plus a hard TTL
  fallback for sources that can't be re-confirmed.

A single `expires_at` column cannot express both. We use `last_seen_at` + a liveness sweep
**and** a soft TTL.

### 0.3 Prefer official APIs / public ATS JSON over scraping
Greenhouse / Lever / Ashby expose clean public JSON board endpoints; aggregators
(Adzuna / Jooble / JSearch) have APIs. These are stable, legal, and rate-limit-friendly.
Playwright scraping is reserved for targets with no API and is hard-gated (Phase 2/3).
This matches the existing repo direction: injectable HTTP clients, no embeddings,
BM25 + skill-overlap.

---

## 1. What already exists (do not rebuild)

| Capability | Where |
|---|---|
| Canonical job record, deduped `(source, external_id)`, idempotent upsert | `jobs/models.py::JobPosting`, `ingestion/services.py::upsert_postings` |
| Source registry + adapter context | `jobs/models.py::Source`, `ingestion/adapters/base.py` |
| Adapters (Adzuna, Greenhouse) returning normalized dicts | `ingestion/adapters/` |
| Run-a-source Celery task + run log | `ingestion/tasks.py::run_source`, `ingestion/models.py::IngestionRun` |
| Celery + DB-backed beat scheduler | `config/celery.py`, `CELERY_BEAT_SCHEDULER` in `config/settings/base.py` |
| Cached per-user/job match score | `matching/models.py::MatchScore`, `matching/scorer.py` |
| Stealth-domain filtering at query time | `jobs/views.py::JobListView` (invariant #7) |
| Frontend stores hitting real endpoints | `frontend/src/stores/`, `frontend/src/api/endpoints.ts` |

**Gaps this plan closes:** no freshness/liveness fields, no beat schedule entries, no
liveness sweep / prune, no per-user feed, `MatchScore` has no TTL, and a few hardcoded UI
literals (e.g. the `68%` match ring in `frontend/src/routes/dashboard/Dashboard.tsx`).

---

## 2. Phase A — Freshness & liveness (data model)

Add an abstract `FreshnessMixin` (reusable across future domains — salary intel, company
intel, networking contacts) providing:

- `last_seen_at` — `DateTimeField`, indexed. Bumped on every source run that includes the row.
- `expires_at` — nullable `DateTimeField`. Set explicitly when the source carries a closing
  date; otherwise computed as `last_seen_at + source.ttl`.
- `is_active` — `BooleanField`, indexed. The flag user-facing queries filter on.

Apply it to `JobPosting`, and additionally add:

- `content_hash` — `CharField`. Hash of the meaningful fields so `upsert_postings` can
  distinguish a genuine change from a re-seen-unchanged row (avoids write churn and lets us
  detect "materially updated").

Per-source cadence/TTL lives in the existing `Source.config` JSON (no new model):

```json
{ "refetch_minutes": 60, "ttl_days": 21, "max_pages": 5 }
```

Extend `upsert_postings` to: set `last_seen_at = now()`, recompute `expires_at`, reactivate
a posting that reappears, and short-circuit writes when `content_hash` is unchanged
(still bump `last_seen_at`).

**Migrations:** one migration on `jobs`. Backfill `last_seen_at = created_at`,
`is_active = True` for existing rows.

---

## 3. Phase B — Scheduling & sweeps (the "scripts")

The "scripts" become **Celery beat tasks + thin management-command wrappers**, so they run
identically in dev (`manage.py …`) and prod (beat), and can fall back to cron.

- `beat_schedule`: one `ingestion.run_source` entry per enabled source, on its own cadence
  derived from `Source.config.refetch_minutes`.
- `ingestion.sweep_liveness` (new task): set `is_active=False` where `expires_at < now()`
  OR the row was not seen in the last *N* runs of its source.
- `ingestion.prune` (new task): hard-delete rows expired beyond a retention window
  (e.g. 90 days). Keep `IngestionRun` rows for observability.
- Management commands under `backend/ingestion/management/commands/`:
  `ingest_source <name>`, `sweep_liveness`, `prune_postings`.

---

## 4. Phase C — Personalization (precomputed `UserJobFeed`)

**Chosen approach:** a precomputed, TTL'd per-user feed table (not read-time-only filtering).
Scales better and directly powers dashboard KPIs.

New `feed/` app (or module) with `UserJobFeed`:

- Fields: `user`, `job` (FK `JobPosting`), `rank`, `score`, `reason`/`breakdown` (JSON),
  `computed_at`. Unique `(user, job)`; index `(user, rank)`.
- `feed.rebuild_for_user(user)` task pipeline:
  1. Start from **active** `JobPosting` rows (`is_active=True`).
  2. Hard filters: stealth domains (invariant #7), location/remote, salary floor,
     seniority — sourced from the user's structured profile.
  3. Score with `matching.scorer` (reuse `MatchScore`; recompute when the cached score is
     older than the job's `last_seen_at` or on `model_version` bump — closes the current
     "MatchScore has no TTL" gap).
  4. Write the top *N* as the user's ranked feed with `computed_at` (per-user "expiry":
     stale after ~6h or on profile change).
- **Triggers:** profile/resume change (Django signal), after a source run yields new
  high-score matches, and a periodic refresh. **Not** on every page load.
- Dashboard KPIs (`new_matches`, etc.) derive from this table.

---

## 5. Phase D — Replace dummy data in the UI

Most endpoints already exist; the gaps are a few hardcoded literals.

- `GET /api/v1/feed/` → personalized ranked jobs. Dashboard uses this instead of generic
  `/jobs/`. Keep `/jobs/` as the raw browse/search endpoint.
- Replace the hardcoded `68%` match ring in
  [`Dashboard.tsx`](../frontend/src/routes/dashboard/Dashboard.tsx) with a real aggregate
  from the feed. Audit `JobsList.tsx` / `NetworkGraph.tsx` for similar literals.

Note: Phase D can ship against the **shared live pool** (Phase A/B) *before* personalization
lands, to kill obvious dummy values early.

---

## 6. Phase E — Observability & safety

- Per-source health: "last successful run" + alert when a source goes silent (use the
  `notifications` app). `IngestionRun` already logs per-run stats.
- Per-source rate-limit / back-off config; respect robots/ToS.
- Never scrape behind auth without the user's own credentials — that belongs in the
  `credentials` vault (Phase 3).

---

## 7. Suggested rollout order

`A (model + freshness)` → `B (scheduling + sweeps)` → `D (point UI at live pool, kill obvious
dummy values)` → `C (personalized UserJobFeed)` → `E (observability)`.

A + B + D yields a genuinely live product quickly; C is the differentiator.

**Phase mapping:** A/B/D are Phase 1 hardening; extra adapters + Playwright scraper are the
existing Phase 2; autonomous/credential-backed sources are Phase 3.

---

## 8. Open questions to resolve before coding

- Default TTLs per source kind (aggregator vs ATS vs scraper)?
- Feed size *N* per user and refresh interval?
- Do we precompute feeds for all users or only recently-active ones (cost control)?
