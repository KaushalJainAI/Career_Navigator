# Career Navigator

AI-powered job-hunt platform: real-time job alerts, structured-profile chat onboarding, resume↔JD match scoring, AI resume + cover-letter tailoring, tiered auto-application (assist / autofill / autonomous), and a dedicated **Interview Grill Chat Agent** that researches the company, generates tailored question banks, runs live grilling rounds, and produces a personalised study plan.

Patterned on the AIAAS Django/Channels/Celery + React/Zustand stack and Faultline's LangGraph agent loop with parallel tool batching and Vault-style credential injection.

> 📖 **New here? Start with [docs/vision.md](docs/vision.md)** for the *why*, then [docs/architecture.md](docs/architecture.md) for the *how*.

## Documentation

| Doc | Read when… |
|---|---|
| [docs/vision.md](docs/vision.md) | You want the product thesis, target user, and design principles. |
| [docs/architecture.md](docs/architecture.md) | You're orienting on the system: processes, apps, URLs, data flows. |
| [docs/agent.md](docs/agent.md) | You're touching anything LLM-facing or the autonomous-apply path. |
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

15 Django apps. Detailed entity model in [docs/data-model.md](docs/data-model.md); detailed orchestration in [docs/agent.md](docs/agent.md).

| App | Purpose |
|---|---|
| [`accounts`](backend/accounts/) | User, tier, NVIDIA guest-key issuance, JWT, Google OAuth |
| [`profiles`](backend/profiles/) | StructuredProfile + Experience/Education/Skill/Project/Preference |
| [`resumes`](backend/resumes/) | Upload + parse (PDF/DOCX) + versioning |
| [`jobs`](backend/jobs/) | Company, Source, JobPosting |
| [`ingestion`](backend/ingestion/) | Adapters (Adzuna, Greenhouse; Phase 2 adds Jooble/JSearch/Lever/scraper/email/web-search/CLI-delegate). See [docs/adapters.md](docs/adapters.md). |
| [`matching`](backend/matching/) | Resume↔JD scorer (lexical + skill-overlap; LLM rerank optional) + MatchScore |
| [`notifications`](backend/notifications/) | Subscription DSL, Alert, web-push, Channels |
| [`applications`](backend/applications/) | Application + AutoApplySession (approval token) + ApplicationEvent |
| [`tailoring`](backend/tailoring/) | TailoredResume + CoverLetter generators (LLM-injectable) |
| [`agent`](backend/agent/) | LangGraph orchestrator + phase-gated tool registry + HITL gates. See [docs/agent.md](docs/agent.md). |
| [`interview`](backend/interview/) | **Interview Grill Chat Agent** — research → question bank → live grilling → report + study plan |
| [`credentials`](backend/credentials/) | AES-GCM encrypted vault for provider keys |
| [`extension_api`](backend/extension_api/) | Endpoints consumed by the MV3 extension |
| [`vault`](backend/vault/) | Faultline-style AuthFlow per portal (Phase 3) |
| [`billing`](backend/billing/) | Stripe + credit ledger |
| [`streaming`](backend/streaming/) | Channels WebSocket consumers (notifications, interview) |

## Phases

- **Phase 1 (MVP) — scaffolded.** Discovery via Adzuna + Greenhouse, profile chat onboarding, resume parse + match, tailoring, email + push notifications, Google OAuth + NVIDIA guest pool.
- **Phase 2 — pending.** Jooble/JSearch/Lever adapters, Playwright scraper, email-forward parser, browser extension (autofill tier), cover letters, JD red-flag detector, Interview Grill (text mode), application analytics.
- **Phase 3 — pending.** Autonomous-apply behind HITL gates, Workday/Greenhouse/Lever AuthFlows, LinkedIn integration, salary intelligence, voice mode for Interview Grill.

Detailed vision and prioritisation: [docs/vision.md](docs/vision.md).

## Reference projects

We copy patterns from two adjacent projects on disk rather than regenerating:

- **AIAAS** (`c:\Users\91700\Desktop\AIAAS`) — auth/tier system, LangGraph chat agent, credentials vault, Channels streaming, Google OAuth provider.
- **Faultline** (`c:\Users\91700\Desktop\Faultline`) — plan→execute→observe loop, parallel tool batching, Vault-style portal AuthFlow.

## Contributing

Read [CLAUDE.md](CLAUDE.md) and [docs/agent.md](docs/agent.md) before making changes that touch the agent / tools / autonomous-apply path. The HITL hard-gate is a load-bearing invariant — never bypass it. The canary test that locks it lives at [backend/agent/tests/test_graph.py](backend/agent/tests/test_graph.py).
