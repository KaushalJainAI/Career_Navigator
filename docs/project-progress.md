# Project Progress

Last updated: 2026-07-02 (status re-verified directly against the code and a full local test run — 225 backend tests passing)

This file summarizes the current state of Career Navigator from the repository structure, README, and implementation docs.

## Overall Status

Career Navigator is past the initial scaffold. The core Django backend, React frontend, browser extension shell, infrastructure files, and documentation are all present. Phase 1 is implemented beyond scaffold, Phase 2 is partially implemented, and Phase 3 is still mostly pending.

**Critical repo-state note (verified 2026-07-02):** all recent work lives on the local `agent` branch and remains **uncommitted** (~110+ modified/untracked files). Per the device rule, commits happen only on `agent` (never merged to `main`) and only when explicitly requested, so `origin/main` is still far behind and GitHub Actions CI has not run on any of it. Committing `agent` and opening a PR to `main` remains the single highest-priority housekeeping action. The live deployment at `testing.kaushaljain.com` is served straight from the working tree (see [development.md](development.md)), so "shipped" below means live there, not merged.

## Recently Completed

- Networking, company hub & interactive graph (2026-07-02):
  - **Company hub** — a cross-app read model (`networking/company_hub.py`, no new tables) joining each `Company` to the user's contacts, open `JobPosting`s, and applications. `GET /networking/companies/` lists every company you have a contact/employment/application at with counts; `GET/PATCH /networking/companies/<id>/` returns the full hub (connections, opportunities, applications, warm intros) and lets the user edit the shared `careers_url`/`description`. New frontend `/companies` list + `/companies/:id` detail pages (in the **More** menu). The company↔application link is *derived* (Application→JobPosting→Company), never a stored FK, so it can't drift.
  - **Contact↔company surfaced** — the pre-existing `Contact.company` FK is now drawn in the graph at depth 1 and listed on every company hub.
  - **Interactive network graph** — replaced the placeholder (type-grouped list + raw edge dump) with a dependency-free **SVG node-link diagram**: draggable nodes coloured by type, click-to-inspect, double-click-to-expand, and **GUI editing** — "Add person" (creates the company FK) and a Connect mode that clicks node→node to POST a `ContactRelationship` (person↔person) or `ContactEmployment` (person→company). `?root=company:X` centres the graph on a company.
  - Verified live: 13 companies aggregated, detail counts correct, graph returns 11 company nodes / 24 edges; 225 backend tests pass.
- Credit billing + web-push notifications (this cycle):
  - Credit ledger (`billing`) charges **before** expensive LLM work (tailoring/interview/autonomous apply) so an out-of-credit user gets a clean `402 InsufficientCredits`, not half a service. A signup bonus is granted via a `post_save` signal so first-run flows and tests stay funded.
  - Web push: VAPID keypair, service worker, subscribe/unsubscribe endpoints; alerts fan out to in-app + email + browser push. Both `.env`s hold the real VAPID keys (gitignored).
- Application-tracking overhaul: four-tab pipeline Kanban (to-apply / applied / interviewing / outcome), a **Todos** feature and a **Goals** feature (live progress computed from the pipeline in `applications/goals.py`), editable per-application `next_action`/`follow_up_on`, and a `seed_demo` command that populates a realistic demo dataset (jobs, contacts, referrals, outreach, actions, alerts) for any `--email`.
- Networking frontend: tabbed Connections hub (Contacts / Referrals / Outreach / Next actions) surfacing the referral, outreach draft→approve, and action-queue endpoints that previously had no UI.
- Profile & settings decoupled into separate pages; profile expanded (Certifications + Languages models added); **dark mode** via a `class`-based Tailwind toggle + `html.dark` overrides and a persisted theme store.
- Unified **notification bell**: an activity feed (`notifications/activity.py`) merging alerts with application events; centred, on-screen dropdown on mobile.
- UX pass: marketing-led dashboard (hero + trust strip + live pipeline snapshot + "how it works"), CSS-only motion layer gated behind `prefers-reduced-motion`, a **More** menu for secondary pages, and a mobile card-density pass (compact 2-up cards on phones, full cards at `sm:`).
- Documentation: refreshed README (feature statuses, networking/notifications rows, phase note) and added four reference docs — [networking.md](networking.md), [billing.md](billing.md), [notifications.md](notifications.md), and [deployment.md](deployment.md) (the live `switch`/EC2 box, including the `--noreload` backend-restart gotcha).

- Created this project progress tracker.
- Portal automation app (`portals`) — browser-driven, no-API scraping foundation shipped (2026-06-12):
  - New Django app for the sources that publish **no API** — LinkedIn, Naukri, Unstop, Y Combinator (Work at a Startup). Plan: [portal-automation-plan.md](portal-automation-plan.md).
  - Injectable `BrowserDriver` (`drivers.py`): real `PlaywrightDriver` (lazy `sync_playwright` import, polite delays + human-like scrolling) and `FakeBrowserDriver` for tests, so the whole stack runs with no Chromium or network in CI.
  - Four scrapers (`scrapers/linkedin|naukri|unstop|ycombinator.py`) with **pure** `parse_list` functions (lxml) that emit the canonical `ingestion.adapters.base.make_posting` dict and flow through `ingestion.services.upsert_postings` — so Ghost-Job Shield, matching, and the stealth filter all apply for free.
  - Sessions are the **user's own** (vision principle: never a shared scraping account): per-user `PortalAccount` with AES-GCM-encrypted Playwright `storage_state`, falling back to env session cookies (`LINKEDIN_SESSION_COOKIE`, etc.). A missing session yields a clean `needs_login` run, not a crash. Login/MFA stays a human handoff.
  - REST surface (`/api/v1/portals/`): list portals + connection status, store/forget a session (write-only), trigger a scrape (sync in dev, Celery in prod, gated by `PORTAL_SCRAPER_ENABLED`), list runs.
  - 24 tests (parse fixtures per portal, `FakeBrowserDriver` service runs incl. needs-login + idempotent rerun, DB/env/none session resolution, API). Backend suite now 202.
  - **Remaining (needs live tuning, not unit-verifiable here):** real per-portal CSS selectors (marked `# LIVE-SELECTOR`), frontend session-connect UX, optional opt-in password AuthFlow behind HITL.
- Response-rate analytics shipped (2026-06-12):
  - New `backend/applications/analytics.py`: a pure function computing the application funnel (applied → phone → onsite → offer), overall response/offer rates, a per-tier breakdown (assist/autofill/autonomous), and average days to first response. It reads `status_changed` event history (not just current status), so an application that reached a phone screen and was later rejected still counts as a response.
  - `GET /api/v1/applications/analytics/` returns the payload; the dashboard renders a panel with headline stats and a funnel bar chart.
  - Tests: `applications/tests/test_analytics.py` (funnel/rates, per-tier, empty-safe, avg-days-from-events) + an endpoint test, and a Playwright `response-analytics.spec.ts`.
- ATS-safe résumé export shipped (2026-06-12):
  - New `backend/resumes/ats_export.py`: deterministic, dependency-light builders that render the user's StructuredProfile as a single-column, ATS-parseable résumé — plain text (`build_ats_resume`) and a minimal table-free `.docx` (`build_ats_docx`, reusing the text builder so the formats never diverge). Standard ALL-CAPS section headers, comma-separated skills, ASCII `- ` bullets, HTML/glyph sanitisation.
  - `GET /api/v1/tailoring/resume/export/?application_id=&fmt=txt|docx` streams the file as an attachment; `application_id` overlays that application's tailored summary. (Param is `fmt`, not `format`, to avoid DRF's content-negotiation override.)
  - Job detail gains "ATS resume .txt" / ".docx" download buttons in the materials panel.
  - Tests: `resumes/tests/test_ats_export.py` (text sections/sanitisation/degradation + valid table-free docx), tailoring API tests (txt, tailored-summary overlay, docx attachment), and a Playwright download assertion.
- Match explainability shipped (2026-06-12):
  - `matching/scorer.py` now returns `matched_skills` and a structured `explanation` (colour-coded positive/negative/neutral reasons: skill coverage %, named skill gaps, text-similarity %) alongside the existing score/breakdown/gaps.
  - `MatchScore` gains `matched_skills` + `explanation` JSON fields (migration `matching/0002`); the match endpoint persists and returns them.
  - Job detail renders the reasons as a colour-coded list so a candidate sees *why* a job scored as it did, not just a number.
  - Tests: scorer unit tests for matched/gap/no-skill cases, a matching API test asserting the explanation is returned and cached, and a Playwright `match-explainability.spec.ts`.
- Ghost-Job Shield — flagship Phase 2 feature shipped (2026-06-11):
  - New `backend/jobs/ghost.py`: deterministic, network-free ghost-risk scorer (0–100 + low/medium/high band + human-readable reasons) over content fingerprinting, copy-staleness, repost cycles, missing salary, and evergreen/red-flag JD language. Subsumes the previously-separate JD red-flag detector.
  - `JobPosting` gains liveness fields (`first_seen_at`, `last_seen_at`, `content_fingerprint`, `repost_count`, `ghost_risk`, `ghost_reasons`) + migration `jobs/0002`. `first_seen_at` resets only when the JD copy/salary changes, so staleness measures the age of *this* copy.
  - `ingestion/services.upsert_postings` now computes the fingerprint, tracks first/last seen, detects take-down-and-repost cycles (same fingerprint under another source/external_id for the same company), and stores the risk score — all inside the existing idempotent upsert.
  - API: `JobPostingSerializer` exposes `ghost_risk`/`ghost_band`/`ghost_reasons`; `JobListView` adds `ordering=ghost_risk` and a `max_ghost_risk` filter; the apply-prepare path returns the risk and prepends a caution to `next_actions` for high-risk roles (HITL-friendly deprioritization).
  - Frontend: reusable `GhostRiskBadge` on the jobs list and job detail, with a reasons panel + warning banner for high-risk postings.
  - Tests: `jobs/tests/test_ghost.py` (unit), repost/staleness/missing-salary integration in `ingestion/tests/test_services.py`, a prepare-endpoint caution test, and two Playwright specs (`ghost-shield.spec.ts`).
- Playwright E2E expansion (2026-06-11):
  - Grew the suite from 2 smoke tests to 7 by adding flow coverage for the core Phase 2 surfaces: onboarding chat (user message → assistant reply), job-detail tailoring (match score → assist-apply prepare → generate resume + cover letter, plus the autonomous approval-token paused state), applications Kanban status change (asserts the `PATCH /applications/:id/` body and the optimistic board update), and the full Interview Grill loop (start → answer each question with feedback → report).
  - Reworked `frontend/e2e/api-mocks.ts` into a method-aware router (GET/POST/PATCH) covering job detail, matching, prepare, tailoring, interview sessions/answer/report, and agent onboarding endpoints. All 7 tests pass; no real network.
- Adapter quality + verification pass (2026-06-11):
  - Refactored the ingestion adapter layer: `make_posting()` factory enforces the posting contract, shared `get_json`/`post_json` helpers contain per-page/board failures (logged without URLs so the Jooble key can't leak), `http_client()` gives uniform timeout + connect retries, and all five adapters accept an injectable `transport` for `httpx.MockTransport` tests.
  - Added an integration test covering the full fetch → normalise → upsert → `IngestionRun`/`JobPosting` chain, including idempotent reruns and invalid-row skipping.
  - Filled the remaining adapter branch gaps with unit tests: JSearch no-key skip, pagination stop-on-empty, and the `_domain` bare/scheme/empty cases; Adzuna no-key skip; and the shared resilience branch where a 200 with a non-JSON body yields nothing instead of raising.
  - Live end-to-end smoke via `backend/scripts/smoke_adapters.py`: Greenhouse (stripe board) returned 496 postings and Lever (mistral board) 173 postings, all contract-valid. Empty boards (companies that left the ATS) degrade gracefully to zero rows. Jooble/JSearch live smoke still needs real API keys.
  - CI green on the refactor commit; backend suite at 149 tests.
- Competitive-positioning docs pass (2026-06-10):
  - Added [competitive-landscape.md](competitive-landscape.md): project-by-project comparison against AIHawk, JobSpy, Resume-Matcher, Reactive-Resume/OpenResume, ApplyPilot, Teal/Huntr/Simplify/Careerflow, and Final Round AI, plus a researched section on user-reported shortcomings (Reddit/Trustpilot/GitHub issues) and our guardrails against each.
  - Updated vision.md: ghost jobs added as a core friction; truthfulness now deterministically verified post-generation; new design principles 9–11 (agent never speaks as the candidate without review; outcomes over volume; billing trust); expanded "What we are not building" (no spray-and-pray applier, no covert live-interview copilot, no resume-builder product).
  - Updated implementation-plan.md: JobSpy wrapper adapter as a locked source decision; Phase 2 re-scoped around the Ghost-Job Shield (flagship), match explainability, truthfulness verification pass, ATS-safe export, extension job capture + PortalRecipe field maps, grill post-session reports, outcome-first analytics; Phase 3 billing-trust requirements and BYOK option.
  - Updated README: new Features table and a Documentation link to the landscape doc.
- Implemented the browser-extension autofill bridge:
  - receives autofill suggestions from the backend,
  - fills matching empty form fields only,
  - avoids overwriting user-entered values,
  - records filled values when the user clicks submit/apply.
- Added extension runtime tests for autofill and submit-event behavior.
- Fixed extension packaging so `manifest.json` and `popup.html` are copied into `extension/dist`.
- Added `npm run package` for the extension.
- Added a build validator that checks the MV3 package contains the manifest, popup, background worker, and all content-script bundles.
- Ran full local verification across backend, frontend, and extension.
- Added GitHub Actions CI for backend tests, frontend tests/build, and extension tests/package validation.
- Added Playwright E2E smoke coverage for authenticated navigation across Dashboard, Jobs, Applications, and Settings.
- Added a Playwright unauthenticated redirect check for protected routes.
- Updated CI to install Chromium and run frontend E2E tests.

## Completed

### Foundation

- Django 5 backend with DRF apps for accounts, profiles, resumes, jobs, ingestion, matching, notifications, applications, tailoring, agent, interview, credentials, extension API, vault, billing, streaming, and networking.
- React/Vite frontend with Zustand stores, Tailwind styling, and authenticated app routes.
- Docker Compose infrastructure for backend, frontend, Postgres, Redis, Celery worker, and Celery beat.
- Documentation for vision, architecture, data model, adapters, development, testing, agent behavior, and implementation planning.

### Authentication and Account Setup

- User registration and login.
- JWT-authenticated API flow.
- Google OAuth support.
- API token support.
- Tier/guest-key model for NVIDIA-style shared access.

### Profile and Onboarding

- Structured profile models for experience, education, skills, projects, and preferences.
- Chat-style onboarding flow that can update profile fields.
- Deterministic profile extraction/update helpers.
- Profile readiness score, missing-section reporting, and frontend readiness display.

### Resumes and Matching

- Resume upload and parsing pipeline.
- Rule-based fallback parsing for PDF/DOCX text.
- Deterministic technical skill extraction.
- Resume-to-job match scoring using lexical and skill-overlap logic.
- Match scorer tests.

### Job Discovery

- Job/company/source data models.
- Adzuna adapter.
- Greenhouse adapter.
- Ingestion services and tasks.
- Jobs list and job detail frontend routes.

### Applications and Tailoring

- Applications Kanban.
- Application stats endpoint for dashboard KPIs.
- Job detail cards include job/company/location context.
- Apply preparation endpoint with `assist`, `autofill`, and `autonomous` paths.
- Application events for important workflow steps.
- Auto-apply session and approval-token issuance for autonomous preparation.
- Tailored resume generation.
- Cover-letter generation.
- Frontend display for generated resume and cover-letter materials.

### Notifications

- Notification subscription model and API.
- Subscription create/list/detail/update/delete support.
- Alert subscription manager in settings.
- In-app and web-push architecture is present.

### Interview Preparation

- Interview Grill text-mode backend.
- Research, question-bank, answer-evaluation, report, and study-plan flow.
- Frontend interview route.

### Networking

- Networking models and graph services.
- Network graph frontend route.
- Manual contact seeding from the frontend.
- Networking service and relationship tests.

### Billing Base

- Billing models and credit ledger.
- Billing summary, ledger, and top-up endpoints.
- Billing frontend page under settings.
- API tests for credit ledger behavior.

### Browser Extension Base

- MV3 extension project structure.
- Parser files for LinkedIn jobs/profile, Greenhouse, Lever, Mercor, Naukri, and Unstop.
- Extension API app in backend.
- Extension parser tests.
- Autofill runtime bridge that fills high-confidence empty fields and records filled values on submit.
- Extension package build now copies `manifest.json` and `popup.html` into `dist`.
- Extension build validator checks that the MV3 package contains all manifest-referenced scripts.

### Testing

- Backend test suite exists across most apps.
- Frontend store/page tests exist.
- Latest documented verification:
  - `cd backend && pytest -q` passed with 131 tests.
  - `cd frontend && npm run test -- --run` passed with 5 tests.
  - `cd frontend && npm run build` passed.
  - `cd backend && pytest extension_api/tests/test_views.py -q` passed with 12 tests.
  - `cd extension && npm run test` passed with 14 tests.
  - `cd extension && npm run package` passed and reported `Extension build valid.`
  - Full rerun after the latest Phase 2 work:
    - `cd backend && pytest -q` passed with 131 tests and 7 warnings.
    - `cd frontend && npm run test -- --run` passed with 5 tests.
    - `cd frontend && npm run test:e2e` passed with 2 tests.
    - `cd frontend && npm run build` passed.
    - `cd extension && npm run test` passed with 14 tests.
    - `cd extension && npm run package` passed and reported `Extension build valid.`
  - Independent re-verification on 2026-06-10:
    - `cd backend && pytest -q` — 131 passed, 7 warnings.
    - `cd frontend && npm run test -- --run` — 5 passed (3 files).
    - `cd extension && npm run test` — 14 passed (runtime + parsers).
    - `cd frontend && npm run build` — passed.
    - `cd extension && npm run package` — `Extension build valid.`
    - Playwright E2E suite lists 2 tests in `frontend/e2e/app-smoke.spec.ts` (authenticated navigation + unauthenticated redirect).
    - Code spot-checks confirmed: only Adzuna + Greenhouse adapters exist under `backend/ingestion/adapters/`; HITL `approval_token` is enforced in `agent/tools/builtins.py` and covered by `agent/tests/test_graph.py`; billing reports `stripe_enabled: False` with `StripeSubscription` as a placeholder model only; `notifications/services.py::_deliver_channel` delivers in-app (Channels) + email only — the `WEBPUSH` channel enum exists but pywebpush/VAPID delivery is not implemented.

## Partially Complete

### Phase 2 Discovery Sources

- Adzuna, Greenhouse, Jooble, JSearch, and Lever backend adapters are implemented and registered in `ingestion/tasks.py::ADAPTER_REGISTRY`, with `httpx.MockTransport` unit tests (normalise + fetch paging, no-key skip, and failure branches), a fetch→DB integration test, and a shared resilient base layer (178 backend tests passing as of 2026-06-12, including the Ghost-Job Shield, match-explainability, ATS-export, and response-analytics suites).
- Greenhouse and Lever were smoke-tested live against real public boards on 2026-06-11 (stripe: 496 postings, mistral: 173, all contract-valid) via `backend/scripts/smoke_adapters.py`.
- Jooble/JSearch need API keys (`JOOBLE_API_KEY`, `JSEARCH_RAPIDAPI_KEY`) before a live smoke run; production ingestion also needs `LEVER_TOKENS`/`GREENHOUSE_TOKENS` set to the boards we want to track.
- Playwright scraper framework, email-forward parsing, and web-search/CLI-delegate fallback are planned but not implemented.

### Autofill and Extension Workflow

- Extension project, parsers, content scripts, and backend extension API exist.
- Content runtime now applies backend autofill suggestions to matching empty form fields.
- Submit-event capture now includes the values filled by the extension.
- Production packaging now validates the built extension package.
- Full install-to-autofill-to-submit validation in a real browser is still missing.
- Browser-extension UX still needs more verification.

### Autonomous Apply

- Backend preparation path and approval-token issuance exist.
- HITL gate behavior exists in the agent/tool contract.
- Real server-side Playwright portal automation and final autonomous submit flow are not complete.

### Notifications Delivery

- Subscription management exists.
- Alert filtering architecture exists.
- In-app delivery (Channels `push_to_user`) and email delivery (`django.core.mail.send_mail`) are implemented in `notifications/services.py`.
- Web-push delivery is **not implemented** — the `WEBPUSH` channel enum exists but `_deliver_channel` never sends a push; pywebpush/VAPID wiring is missing.
- Production email (Resend) is not wired; email goes through whatever Django email backend is configured.

### Billing

- Credit ledger and top-up-like API behavior exist.
- Stripe checkout, Stripe customer lifecycle, and webhook handling are intentionally not complete.

### Dynamic Data Pipeline

- A separate plan exists in `docs/dynamic-data-pipeline-plan.md`.
- Freshness/liveness expiry, scheduled refresh sweeps, and personalized precomputed feeds are not yet implemented.

## Missing / Not Yet Complete

### Product Features

- Server-side Playwright autonomous application submission.
- Portal-specific AuthFlows in the vault app.
- LinkedIn session-cookie integration.
- Salary intelligence from external sources.
- Advanced analytics, including response-rate analytics per resume variant.
- Weekly career-coach digest.
- Salary negotiation rehearsal.
- Voice mode for Interview Grill.
- ~~JD red-flag detector~~ — shipped 2026-06-11 as part of the Ghost-Job Shield (`jobs/ghost.py` red-flag + evergreen language signals).
- Real-LLM evaluation suite for tailoring quality.

### Data and Integrations

- Live-key smoke runs for the Jooble/JSearch/Lever adapters (code + tests landed 2026-06-10).
- Email-forward job alert parser.
- Production web-push setup with VAPID validation.
- Resend email notification integration.
- Stripe checkout and webhook integration.
- Production secrets/environment hardening.

### Testing and QA

- Further Playwright E2E coverage (resumes upload, networking graph, billing top-up) beyond the 7 flows now covered (auth nav, redirect, onboarding, job-detail tailoring, Kanban status, Interview Grill).
- Browser extension E2E tests.
- Channels WebSocket integration tests.
- Production-like Docker smoke test.
- CI workflow exists at `.github/workflows/ci.yml` and includes backend tests, frontend unit/E2E/build, and extension tests/package validation, but it still needs to run on GitHub after commit/push.
- Full verification should be rerun before release if more uncommitted changes are added.

### Deployment

- Production deployment configuration is not finished.
- Domain, HTTPS, allowed hosts, CORS origins, and secret management need final setup.
- Celery queue separation for scraping/autonomous apply needs production validation.
- Monitoring, logging, backups, and operational runbooks are missing.

## What We Need More

### Immediate Next Steps

1. ~~Commit the working tree in logical groups and push to GitHub~~ — done 2026-06-10 (7 grouped commits pushed, CI triggered). The local `backend/scripts/seed_kaushal.py` is gitignored because it carries a personal password and the repo is public.
2. ~~Implement the remaining Phase 2 job sources~~ — done 2026-06-10 (Jooble, JSearch, Lever adapters + tests).
3. Confirm GitHub Actions CI passes on the pushed commits; fix any environment drift between local and CI.
4. Configure real API keys (`JOOBLE_API_KEY`, `JSEARCH_RAPIDAPI_KEY`, `LEVER_TOKENS`) and smoke-run each new adapter against live endpoints.
5. Load `extension/dist` in Chrome and validate install-to-autofill-to-submit end to end on supported job pages.
6. ~~Expand Playwright E2E coverage for onboarding, job detail tailoring, applications Kanban status changes, and Interview Grill~~ — done 2026-06-11 (suite now 7 tests).
7. Add browser-extension E2E coverage once the real Chrome install flow is validated.

### Next Product Milestone

The most practical next milestone is a reliable Phase 2 beta:

- Users can onboard.
- Users can upload resumes.
- Users can browse real jobs.
- Users can see match scores.
- Users can generate tailored resume and cover-letter material.
- Users can track applications in Kanban.
- Users can manage notification subscriptions.
- Users can use the extension for assisted autofill.
- Users can run text-mode Interview Grill.

### Later Milestones

- Phase 3 autonomous apply with real Playwright portal automation and strict HITL approvals.
- Stripe-backed paid tier.
- LinkedIn, salary intelligence, and networking automation.
- Voice interview mode.
- Advanced analytics and weekly career coaching.

## Current Risk Areas

- The repo has many modified and untracked files, so verification should be rerun after any additional broad edits.
- Browser extension behavior is present in pieces but needs real browser validation.
- Autonomous apply must remain guarded by HITL approval in every code path.
- External integrations should be mocked in tests and validated separately in controlled integration runs.
- Production deployment needs careful environment and secret handling before real users.
