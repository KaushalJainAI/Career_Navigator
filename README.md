# Career Navigator

AI-powered job-hunt platform: real-time job alerts, structured-profile chat onboarding, resume↔JD match scoring, AI resume + cover-letter tailoring, tiered auto-application (assist / autofill / autonomous), and a dedicated **Interview Grill Chat Agent** that researches the company, generates tailored question banks, runs live grilling rounds, and produces a personalised study plan.

Patterned on the AIAAS Django/Channels/Celery + React/Zustand stack and Faultline's LangGraph agent loop with parallel tool batching and Vault-style credential injection.

> 📖 **New here? Start with [docs/vision.md](docs/vision.md)** for the *why*, then [docs/architecture.md](docs/architecture.md) for the *how*.

## Features

| Area | What ships | Status |
|---|---|---|
| **Discovery** | Unified ingestion from aggregator APIs (Adzuna, Jooble, JSearch), ATS APIs (Greenhouse, Lever), JobSpy-wrapped big boards, email forwards, and one-click extension capture from any careers page | Adapters live; JobSpy + capture planned (Phase 2) |
| **Ghost-Job Shield** | Repost fingerprinting, staleness tracking, missing-salary heuristics → ghost-risk score on every job card; auto-apply deprioritizes high-risk postings | Planned (Phase 2 flagship) |
| **Matching** | Lexical + skill-overlap resume↔JD scoring; already emits a missing-skill `gaps` list, with richer matched/missing-keyword explanation, UI rendering, and a direct feed into tailoring planned | Scoring + gaps live; full explainability planned |
| **Tailoring** | Per-JD resume + cover-letter generation with audit-trail diffs and a deterministic truthfulness verification pass (identity fields and claimed skills must match the profile — fails closed) | Generation live; verification pass planned |
| **ATS-safe export** | JSON resume schema → single-column server-rendered templates → round-trip parse test | Planned (Phase 2) |
| **Tiered apply** | `assist` (human submits) → `autofill` (extension fills, never overwrites user input) → `autonomous` (agent submits, hard-gated on a per-application approval token) | Live |
| **Tracking & analytics** | Applications Kanban + outcome-first dashboard: response rate per resume variant, time-to-first-interview, stage conversion — never "applications sent" as the headline | Kanban live; analytics planned |
| **Interview Grill Agent** | Company-researched question banks, live grilling rounds with STAR-rubric evaluation, persisted post-session reports + study plans; voice mode in Phase 3. Preparation only — no live-interview copilot | Text mode live |
| **Stealth mode** | Employer domains filtered from every list endpoint at the query level | Live |
| **Trust** | Encrypted credentials vault, HITL hard-gate on submission (test-enforced), BYOK/local-model option, honest billing (self-serve cancel, rolling credits) | Vault + gate live; billing planned |

How these choices position us against AIHawk, JobSpy, Resume-Matcher, Reactive-Resume, ApplyPilot, Teal/Huntr/Simplify/Careerflow, and Final Round AI — and the user-reported shortcomings of each we engineer against — is documented in [docs/competitive-landscape.md](docs/competitive-landscape.md).

## Documentation

| Doc | Read when… |
|---|---|
| [docs/vision.md](docs/vision.md) | You want the product thesis, target user, and design principles. |
| [docs/competitive-landscape.md](docs/competitive-landscape.md) | You want the competitor comparison, what we borrow from each, and the shortcomings we engineer against. |
| [docs/architecture.md](docs/architecture.md) | You're orienting on the system: processes, apps, URLs, data flows. |
| [docs/agent.md](docs/agent.md) | You're touching anything LLM-facing or the autonomous-apply path. |
| [docs/job-search-skills-workflows-plan.md](docs/job-search-skills-workflows-plan.md) | You want the built-in job search, referral, outreach, and apply-agent workflow plan. |
| [docs/data-model.md](docs/data-model.md) | You're adding fields, relations, or migrations. |
| [docs/adapters.md](docs/adapters.md) | You're wiring a new job-discovery source. |
| [docs/development.md](docs/development.md) | You want to run it locally and know which env keys matter. |
| [docs/testing.md](docs/testing.md) | You're writing tests (you are, right?). |
| [docs/implementation-plan.md](docs/implementation-plan.md) | You want the phased roadmap and the AIAAS/Faultline copy-map. |
| [docs/drop-faiss-and-add-google-auth.md](docs/drop-faiss-and-add-google-auth.md) | Background on why we're dropping the embedder and how Google OAuth landed. |
| [CLAUDE.md](CLAUDE.md) | You're operating this repo via Claude Code. |

## Repo layout

```
career-navigator/
  backend/    Django 5 + DRF + Celery + Channels (Postgres, Redis)
  frontend/   Vite + React 19 + Zustand + Tailwind
  extension/  MV3 browser extension (Phase 2)
  infra/      docker-compose + Dockerfiles
  docs/       Architecture, vision, and reference notes
```

## Quick start (local dev, no Docker)

```bash
# 1. Backend
cd backend
python -m venv venv && source venv/bin/activate   # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                              # then fill in CREDENTIAL_ENCRYPTION_KEY
python manage.py makemigrations && python manage.py migrate
python manage.py runserver

# 2. Frontend (separate shell)
cd frontend
cp .env.example .env
npm install
npm run dev
```

Visit `http://localhost:5173`. Full setup notes, env reference, and troubleshooting in [docs/development.md](docs/development.md).

## Quick start (Docker)

```bash
cd infra
docker compose up
```

Brings up Postgres, Redis, backend (daphne), Celery worker, Celery beat, and the Vite dev server.

## Tests

```bash
# Backend
cd backend && pytest -q

# Frontend
cd frontend && npm run test
```

Every app ships unit tests in `<app>/tests/test_*.py`. Full policy: [docs/testing.md](docs/testing.md).

## Apps overview

18 Django apps. Detailed entity model in [docs/data-model.md](docs/data-model.md); detailed orchestration in [docs/agent.md](docs/agent.md).

| App | Purpose |
|---|---|
| [`accounts`](backend/accounts/) | User, tier, NVIDIA guest-key issuance, JWT, Google OAuth |
| [`profiles`](backend/profiles/) | StructuredProfile + Experience/Education/Skill/Project/Preference |
| [`resumes`](backend/resumes/) | Upload + parse (PDF/DOCX) + versioning |
| [`jobs`](backend/jobs/) | Company, Source, JobPosting |
| [`ingestion`](backend/ingestion/) | Adapters (Adzuna, Greenhouse, Jooble, JSearch, Lever; Phase 2 adds JobSpy wrapper/scraper/email/web-search/CLI-delegate). See [docs/adapters.md](docs/adapters.md). |
| [`matching`](backend/matching/) | Resume↔JD scorer (lexical + skill-overlap; LLM rerank optional) + MatchScore |
| [`notifications`](backend/notifications/) | Subscription DSL, Alert, web-push, Channels |
| [`applications`](backend/applications/) | Application + AutoApplySession (approval token) + ApplicationEvent |
| [`networking`](backend/networking/) | Contacts, referral opportunities, outreach drafts, consent events, action queue |
| [`tailoring`](backend/tailoring/) | TailoredResume + CoverLetter generators (LLM-injectable) |
| [`agent`](backend/agent/) | LangGraph orchestrator + phase-gated tool registry + HITL gates. See [docs/agent.md](docs/agent.md). |
| [`interview`](backend/interview/) | **Interview Grill Chat Agent** — research → question bank → live grilling → report + study plan |
| [`credentials`](backend/credentials/) | AES-GCM encrypted vault for provider keys |
| [`extension_api`](backend/extension_api/) | Endpoints consumed by the MV3 extension |
| [`vault`](backend/vault/) | Faultline-style AuthFlow per portal (Phase 3) |
| [`billing`](backend/billing/) | Stripe + credit ledger |
| [`streaming`](backend/streaming/) | Channels WebSocket consumers (notifications, interview) |
| [`ai`](backend/ai/) | Shared LLM provider transports (NVIDIA, CLI delegates, fallback) injected as `llm=` callables |

## Phases

- **Phase 1 (MVP) - implemented beyond scaffold.** Auth, Google OAuth, API tokens, profile onboarding updates, profile readiness, resume upload/parse, deterministic skill extraction, Adzuna + Greenhouse ingestion, match scoring, real dashboard stats, applications Kanban with job details, tailoring, cover letters, notification subscriptions, credits ledger, and Interview Grill text mode are wired.
- **Phase 2 - partially implemented.** Apply workflow now supports distinct `assist`, `autofill`, and `autonomous` preparation paths with application events and HITL approval-token issuance. Job detail can generate and display tailored resume + cover letter materials. Network graph supports manual contact seeding. Browser extension APIs and parsers exist, but the full install/autofill/submit workflow still needs end-to-end validation.
- **Phase 3 - pending.** Server-side Playwright autonomous submit, portal AuthFlows, LinkedIn integration, salary intelligence, voice interview mode, Stripe checkout/webhooks, and advanced analytics are not complete.

Latest verification after the staged functionality pass:

```bash
cd backend && pytest -q              # 131 passed
cd frontend && npm run test -- --run # 5 tests passed
cd frontend && npm run build         # passed
```

Detailed vision and prioritisation: [docs/vision.md](docs/vision.md).

## Reference projects

We copy patterns from two adjacent projects on disk rather than regenerating:

- **AIAAS** (`c:\Users\91700\Desktop\AIAAS`) — auth/tier system, LangGraph chat agent, credentials vault, Channels streaming, Google OAuth provider.
- **Faultline** (`c:\Users\91700\Desktop\Faultline`) — plan→execute→observe loop, parallel tool batching, Vault-style portal AuthFlow.

## Contributing

Read [CLAUDE.md](CLAUDE.md) and [docs/agent.md](docs/agent.md) before making changes that touch the agent / tools / autonomous-apply path. The HITL hard-gate is a load-bearing invariant — never bypass it. The canary test that locks it lives at [backend/agent/tests/test_graph.py](backend/agent/tests/test_graph.py).
