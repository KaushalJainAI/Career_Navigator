# Project Progress

Last updated: 2026-06-10 (status re-verified directly against the code and a full local test run)

This file summarizes the current state of Career Navigator from the repository structure, README, and implementation docs.

## Overall Status

Career Navigator is past the initial scaffold. The core Django backend, React frontend, browser extension shell, infrastructure files, and documentation are all present. Phase 1 is implemented beyond scaffold, Phase 2 is partially implemented, and Phase 3 is still mostly pending.

**Critical repo-state note (verified 2026-06-10):** `origin/main` is still at commit `184274a` — every recent feature (CI workflow, E2E tests, extension autofill bridge, onboarding agent, billing/tailoring/profile test suites, this doc) exists only as uncommitted local changes (~40 modified + ~25 untracked files). GitHub Actions CI has therefore never run. Committing and pushing is the single highest-priority action.

## Recently Completed

- Created this project progress tracker.
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

- Adzuna, Greenhouse, Jooble, JSearch, and Lever backend adapters are implemented and registered in `ingestion/tasks.py::ADAPTER_REGISTRY`, with `httpx.MockTransport` unit tests (normalise + fetch paging, no-key skip, and failure branches), a fetch→DB integration test, and a shared resilient base layer (163 backend tests passing as of 2026-06-11, including the Ghost-Job Shield suite).
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
