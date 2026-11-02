# Career Navigator

AI-powered job-hunt platform: real-time job alerts, structured-profile chat onboarding, resume↔JD match scoring, AI resume + cover-letter tailoring, tiered auto-application (assist / autofill / autonomous), and a dedicated **Interview Grill Chat Agent** that researches the company, generates tailored question banks, runs live grilling rounds, and produces a personalised study plan.

Patterned on the AIAAS Django/Channels/Celery + React/Zustand stack and Faultline's LangGraph agent loop with parallel tool batching and Vault-style credential injection.

> 📖 **New here? Start with [docs/vision.md](docs/vision.md)** for the *why*, then [docs/architecture.md](docs/architecture.md) for the *how*.

## What it does

A job-search co-pilot built for people applying to many companies at once — especially **freshers handling campus placements and off-campus applications**. It works fully **without any AI key**; plug in your own Claude / ChatGPT / Gemini subscription to make the assistant conversational.

| Step | What you get |
|---|---|
| **1. Résumé → profile** | Upload a PDF/DOCX or paste text. Name, contact, education (with CGPA), internships, projects and 200+ skills are extracted and fill your profile; target roles are suggested. |
| **2. Ranked jobs** | "Find jobs" searches public company boards (Greenhouse, Lever) and job APIs (Remotive, Arbeitnow, plus Adzuna/Jooble/JSearch if keyed). Add campus drives or referrals by link (Greenhouse/Lever/Ashby) or paste. Every job gets a 0–100 fit with reasons: skills you have/miss, title & seniority, years asked, location, **CGPA cutoff and batch eligibility**, ghost-job risk. |
| **3. Truthful tailoring** | Per-job résumé that reorders your real skills, bullets and projects and writes a factual summary — never invents. Keyword coverage, gaps as suggestions, editable, ATS-safe .docx/.txt export. Factual cover letter. Optional AI polish passes a fail-closed verifier (no new skills, numbers or employers). |
| **4. Pipeline** | Saved → Applied → **Online assessment** → Interviewing → Final/HR → Offer. Deadlines, next-round dates, notes, follow-up nudges. |
| **5. Today** | A plan built from real state: deadlines closing soon, upcoming OAs/interviews, follow-ups due, unfinished applications, strong matches, weekly goal. No made-up numbers. |
| **6. Practice** | Interview rounds generated from the job description and your résumé (skills, gaps, projects), plus HR and CS-fundamentals rounds. STAR feedback per answer, off-topic detection, study plan. |
| **7. Assistant** | A chat copilot that drives the app: "I got an OA from TCS on Friday 10am", "tailor my résumé for Zoho", "add contact Riya, SDE at Google", "draft a referral message". Changes to your records need one-click approval; it never applies or messages anyone for you. |
| **8. Claude Code plugin** | Manage your search from Claude Code with your own subscription — see [integrations/claude-code-plugin](integrations/claude-code-plugin/). |

### Bring your own AI subscription

Self-hosting? Log into a CLI on the backend machine and set `AI_PROVIDER` in `backend/.env`:

| Subscription | Log in | Setting |
|---|---|---|
| Claude (Pro/Max) | `claude` then `/login` | `AI_PROVIDER=claude_cli` |
| ChatGPT | `codex login` | `AI_PROVIDER=codex_cli` |
| Google | `gemini` | `AI_PROVIDER=gemini_cli` |
| Any of the above | — | `AI_PROVIDER=auto` |

Settings → **AI engine** shows what is active. With no provider the app runs in deterministic mode.

### The copilot agent

`backend/agent/copilot/` — a small, user-scoped tool set (search/rank jobs, add/save jobs, tailor, cover letter, pipeline updates, targets, skills, contacts, referral drafts, practice, navigate) driven by an AIAAS-style plan → act → observe loop with a `--- PRIOR STEPS ---` trajectory (max 5 steps per turn). Tools are `read`, `draft` or `confirm`; `confirm` tools pause the loop until you approve the exact change. Without an LLM, a deterministic intent router maps everyday phrasing onto the same tools. The same tools are exposed over MCP for the Claude Code plugin.

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

Visit `http://localhost:5173`. No internet access to job boards (e.g. behind a firewall)? Load demo postings with `python manage.py load_sample_jobs` (remove with `--clear`). Full setup notes, env reference, and troubleshooting in [docs/development.md](docs/development.md).

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
