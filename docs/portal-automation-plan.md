# Portal Automation Plan — `portals` app

Status: **in progress (foundation landing 2026-06-12)**. This plan covers the
browser-driven, in-session scraping agent for portals that publish **no public
API** — LinkedIn, Naukri, Unstop, and Y Combinator (Work at a Startup). It is the
missing discovery path called out in [project-progress.md](project-progress.md)
("Playwright scraper", "LinkedIn integration") and [vision.md](vision.md).

## Why a browser agent (and not an API adapter)

The `ingestion/adapters/` layer covers API-friendly sources (Adzuna, Jooble,
JSearch, Greenhouse, Lever). The highest-volume supply — LinkedIn and the
India-specific boards — ship **no API** and are JS-rendered and bot-protected.
The only way to reach them is to drive a real browser the way a person does.

## Non-negotiable principles (carried from vision.md)

1. **User-session-cookie based, never a shared scraping account.** The agent acts
   inside the *user's own* authenticated session. We never operate one shared
   login across users. (vision.md principle: "LinkedIn integration is best-effort
   … user-session-cookie based. Never use a shared scraping account.")
2. **The candidate stays in control.** Login / MFA is a human handoff: the user
   provides their session (a cookie or a stored `storage_state`), or completes a
   login in a visible browser. The agent does not credential-stuff passwords by
   default. Submitting applications stays behind the existing `HITL_HARD_GATE`
   approval-token in `agent/tools`.
3. **Polite by default.** Per-portal rate limit, randomised human-like delays,
   capped result counts, one in-flight session per (user, portal). Identify the
   automation honestly where a UA is set; respect `robots`-style intent.
4. **Reuse the canonical pipeline.** Scrapers emit the **same normalised posting
   dict** as `ingestion/adapters/base.py::make_posting`, then go through
   `ingestion.services.upsert_postings`. That means the Ghost-Job Shield,
   match-explainability, stealth-domain filter, and idempotent `(source,
   external_id)` upsert all apply for free.
5. **Testable without a browser or network.** The browser is behind an injectable
   `BrowserDriver` (real `PlaywrightDriver` in prod, `FakeBrowserDriver` in
   tests) — the same dependency-injection discipline as `httpx.MockTransport`
   and the `llm=` callables. Page parsers are pure functions over canned HTML.

## Architecture

```
portals/
  drivers.py          BrowserDriver (interface) | PlaywrightDriver | FakeBrowserDriver
  scrapers/
    base.py           PortalScraper, PortalQuery, NeedsLoginError
    linkedin.py       LinkedInScraper   (+ pure parse_list)
    naukri.py         NaukriScraper
    unstop.py         UnstopScraper
    ycombinator.py    YCombinatorScraper  (Work at a Startup)
  sessions.py         load_storage_state(user, portal): PortalAccount -> env cookie fallback
  services.py         run_portal_scrape(portal, user, query, driver=None) -> PortalScrapeRun
  tasks.py            Celery: portals.run_portal_scrape
  models.py           Portal, PortalAccount (encrypted session), PortalScrapeRun
  registry.py         PORTALS: name -> {scraper, login_url, cookie_name, cookie_domain, source_kind}
  views.py / urls.py  trigger scrape, list runs, store/clear a portal session
```

### Browser driver

`BrowserDriver.goto(url, wait_selector=None, scrolls=0) -> str` returns the
rendered HTML; `storage_state()` returns the post-run cookies/localStorage so a
refreshed session can be re-encrypted and saved. `PlaywrightDriver` lazily
imports `sync_playwright` **inside** `start()` (never at module import — the same
rule as the injected LLM), so the package imports and the test suite run with no
browser binary installed. Requires `playwright install chromium` in deploy.

### Credentials / sessions (the "fetch from env" requirement)

`sessions.load_storage_state(user, portal)`:
1. If the user has a `PortalAccount` with a stored (AES-GCM encrypted) session,
   decrypt and use it.
2. Otherwise fall back to an **env-provided session cookie** —
   `LINKEDIN_SESSION_COOKIE`, `NAUKRI_SESSION_COOKIE`, `UNSTOP_SESSION_COOKIE`,
   `YC_SESSION_COOKIE` — mapped to the right cookie name/domain via `registry.py`
   (e.g. LinkedIn `li_at`). This lets a single-operator deployment run without a
   per-user UI yet.
3. If neither exists, the scrape returns status `needs_login` (a clean,
   user-actionable state — not a crash).

Secrets are encrypted at rest with the existing `credentials/crypto.py`
(AES-GCM, key from `CREDENTIAL_ENCRYPTION_KEY`) and never serialised back out.

### Data model

- `Portal` — registry row (name, display_name, login_url, enabled, config).
- `PortalAccount` — per `(user, portal)` encrypted `storage_state`, status
  (`active` / `needs_login` / `expired`), `last_used_at`. Write-only session.
- `PortalScrapeRun` — per run: portal, user, query JSON, status
  (`running`/`success`/`needs_login`/`failed`), stats (created/updated/skipped),
  error, timings. Mirrors `ingestion.IngestionRun`.

### API (`/api/v1/portals/`)

- `GET  portals/` — list supported portals + this user's account status.
- `POST portals/<name>/session/` — store a session cookie / storage_state (write-only).
- `DELETE portals/<name>/session/` — forget a session.
- `POST portals/<name>/scrape/` — trigger a scrape (sync in dev, Celery in prod).
- `GET  portals/runs/` — recent scrape runs for the user.

## Guardrails baked in

- `PORTAL_SCRAPER_ENABLED` (default `False`) — master switch; off in tests/CI.
- `PORTAL_SCRAPER_HEADLESS`, `PORTAL_SCRAPER_MIN_DELAY_SECONDS`,
  `PORTAL_SCRAPER_MAX_RESULTS` — politeness knobs.
- One run per (user, portal) in flight; `needs_login` instead of password retries.
- Scraped postings flow through the stealth-domain filter at read time like every
  other source.

## What lands now vs. later

**Now (this PR):** the full framework — app, models, migration, injectable driver
(+ real Playwright driver), the four scrapers with pure HTML parsers, env/DB
session loading, services + Celery task, REST surface, and a test suite that
exercises orchestration end-to-end with `FakeBrowserDriver` and canned HTML. No
real browser or network in tests.

**Later (needs live tuning — cannot be unit-verified here):** real per-portal CSS
selectors must be tuned against live pages and re-checked as the sites change;
session provisioning UX in the frontend; optional AuthFlow password login behind
HITL for portals where the user opts in; CAPTCHA/MFA handoff. These are flagged in
code with `# LIVE-SELECTOR` comments.

## Testing policy

Every scraper ships a pure `parse_list(html, base_url)` unit test with a
representative HTML fixture. Services are tested with `FakeBrowserDriver`
(canned pages) driving the full `scrape -> upsert_postings -> PortalScrapeRun`
chain, including the `needs_login` and idempotent-rerun paths. Session loading is
tested for the DB-first / env-fallback / none branches. No test touches a real
browser or the network.
