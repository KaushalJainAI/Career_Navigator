# Project Progress

Last updated: 2026-06-10 (status re-verified directly against the code and a full local test run)

This file summarizes the current state of Career Navigator from the repository structure, README, and implementation docs.

## Overall Status

Career Navigator is past the initial scaffold. The core Django backend, React frontend, browser extension shell, infrastructure files, and documentation are all present. Phase 1 is implemented beyond scaffold, Phase 2 is partially implemented, and Phase 3 is still mostly pending.

**Critical repo-state note (verified 2026-06-10):** `origin/main` is still at commit `184274a` — every recent feature (CI workflow, E2E tests, extension autofill bridge, onboarding agent, billing/tailoring/profile test suites, this doc) exists only as uncommitted local changes (~40 modified + ~25 untracked files). GitHub Actions CI has therefore never run. Committing and pushing is the single highest-priority action.

## Recently Completed

- Created this project progress tracker.
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

- Adzuna, Greenhouse, Jooble, JSearch, and Lever backend adapters are implemented (2026-06-10) and registered in `ingestion/tasks.py::ADAPTER_REGISTRY`, with `httpx.MockTransport` test coverage (138 backend tests passing).
- Jooble/JSearch/Lever need API keys (`JOOBLE_API_KEY`, `JSEARCH_RAPIDAPI_KEY`) or company tokens (`LEVER_TOKENS`) configured before they ingest live data — a real-key smoke run is still pending.
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
- JD red-flag detector.
- Real-LLM evaluation suite for tailoring quality.

### Data and Integrations

- Live-key smoke runs for the Jooble/JSearch/Lever adapters (code + tests landed 2026-06-10).
- Email-forward job alert parser.
- Production web-push setup with VAPID validation.
- Resend email notification integration.
- Stripe checkout and webhook integration.
- Production secrets/environment hardening.

### Testing and QA

- Broader frontend end-to-end tests with Playwright beyond the current smoke coverage.
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
6. Expand Playwright E2E coverage for onboarding, job detail tailoring, applications Kanban status changes, and Interview Grill.
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
