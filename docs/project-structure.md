# Project Structure

A map of the Career Navigator repository: what each top-level directory holds,
and — for the Django backend — the function of every app, its key models, and the
API path it mounts under.

> For the *why* behind the design, see [vision.md](vision.md); for request/data
> flow and the runtime stack, see [architecture.md](architecture.md) and
> [data-model.md](data-model.md).

---

## Top-level layout

```
CareerNavigator/
├── backend/        Django 5 + DRF API, Channels (WebSockets), Celery workers
├── frontend/       React 19 + Vite + TypeScript SPA (Zustand state)
├── extension/      MV3 browser extension (one-click capture + autofill)
├── infra/          Dockerfiles + docker-compose (dev & prod)
├── scripts/        EC2 bootstrap / deploy helpers
├── docs/           Architecture, plans, and this file
├── example.env     Committable env template — copy to backend/.env
├── README.md       Feature overview + doc index
└── CLAUDE.md       Repo conventions for AI assistants
```

---

## Backend (`backend/`)

Django project. Every app's URLs mount under `/api/v1/` (see `config/urls.py`),
so e.g. `jobs.urls` is served at `/api/v1/jobs/`.

### `config/` — project wiring (not an app)
Settings, URL root, and infra glue.
- `settings/` — `base.py` (shared), `local.py`, `prod.py`, `test.py`.
- `urls.py` — mounts every app under `/api/v1/`; also `/admin/`, `/api/health/`,
  and OpenAPI schema/Swagger at `/api/schema/` + `/api/docs/`.
- `celery.py` — Celery app; `asgi.py`/`wsgi.py` — ASGI (Channels) / WSGI entry.
- `exception_handler.py` — DRF handler (e.g. renders `402 insufficient_credits`).

### Identity & profile

| App | Function | Key models | Mount |
|---|---|---|---|
| **accounts** | Auth: registration, JWT, Google OAuth, guest sessions, API tokens. | `UserProfile`, `GuestSession`, `APIToken` | `/auth/` |
| **profiles** | The user's structured career profile — the single source of truth resumes and tailoring build from. | `StructuredProfile`, `Experience`, `Education`, `Skill`, `Project`, `Certification`, `Language`, `Preference` | `/profile/` |
| **resumes** | Uploaded/generated resumes and their versions; parsed JSON feeds matching. | `Resume`, `ResumeVersion` | `/resumes/` |

### Jobs & discovery

| App | Function | Key models | Mount |
|---|---|---|---|
| **jobs** | Core job catalogue: companies, sources, and postings. Includes the Ghost-Job Shield risk scoring and the AI job-breakdown endpoint. | `Company`, `Source`, `JobPosting` | `/jobs/` |
| **ingestion** | Pulls jobs from external **APIs** (no scraping) and upserts them into `JobPosting` via the canonical pipeline. Adapters live in `ingestion/adapters/` (Adzuna, Jooble, JSearch, Greenhouse, Lever). Celery-driven. | `IngestionRun` | `/ingestion/` |
| **portals** | The deterministic **browser-automation scraper** for no-API sites (LinkedIn, Naukri, Wellfound, Indeed, Glassdoor, +more). Playwright loads pages in the user's own cookie session; pure `parse_list()` selectors extract postings. Scrapers in `portals/scrapers/`; registry in `portals/registry.py`. Off by default. | `Portal`, `PortalAccount`, `PortalScrapeRun` | `/portals/` |
| **matching** | Scores a resume against a job (lexical + skill overlap), emitting a match %, missing-skill gaps, and a colour-coded explanation. | `MatchScore` | `/matching/` |

### Application workflow

| App | Function | Key models | Mount |
|---|---|---|---|
| **applications** | The apply pipeline: tiered apply (assist / autofill / autonomous), the Kanban board, plus Todos and Goals. | `Application`, `ApplicationEvent`, `AutoApplySession`, `Todo`, `Goal` | `/applications/` |
| **tailoring** | AI generation of per-JD resumes and cover letters, with a deterministic truthfulness pass and ATS-safe `.txt`/`.docx` export. | `TailoredResume`, `CoverLetter` | `/tailoring/` |
| **interview** | The Interview Grill Agent: company research, tailored question banks, live STAR-rubric scoring, and a persisted report + study plan. Core logic in `interview/grilling.py`. | `InterviewSession`, `InterviewQuestion`, `InterviewTurn`, `InterviewReport` | `/interview/` |

### Networking

| App | Function | Key models | Mount |
|---|---|---|---|
| **networking** | Contacts, per-company hubs, warm-intro ranking, referral suggestions, outreach draft→approve, and the interactive network graph. | `Contact`, `ContactEmployment`, `ContactRelationship`, `CompanyRelationship`, `ReferralOpportunity`, `OutreachMessage`, `ActionQueueItem`, `UserConsentEvent` | `/networking/` |

### AI, agents & realtime

| App | Function | Key models | Mount |
|---|---|---|---|
| **agent** | LangGraph-style agent loop (`agent/graph.py`) with parallel tool batching. Tools in `agent/tools/` (e.g. `search_jobs`, `score_match`) query already-ingested data; `onboarding.py` runs chat-based profile onboarding. | `AgentSession`, `AgentMessage` | `/agent/` |
| **streaming** | Realtime transport (Django Channels): WebSocket `consumers.py` + `routing.py` and a `broadcaster.py` for pushing notifications/interview output live. Mounted via `config/asgi.py`, **not** `/api/v1/`. | — (transport only) | WS: `ws/notifications/`, `ws/interview/<id>/` |

> Note: the shared LLM transport is not an app — it's `ai/providers.py`
> (`get_configured_llm()`), used by tailoring, interview, matching helpers, and
> the jobs breakdown. Scraping/ingestion never call it.

### Trust, credentials & billing

| App | Function | Key models | Mount |
|---|---|---|---|
| **billing** | Credit ledger — charges before expensive LLM work, signup bonus, refunds; Stripe scaffolding. Pricing in `billing/pricing.py`, accounting in `billing/services.py`. | `CreditLedger`, `StripeSubscription` | `/billing/` |
| **credentials** | User-supplied credentials store (BYOK / portal logins), surfaced to the apply flows. | `Credential` | `/credentials/` |
| **vault** | Faultline-style dynamic auth flows and encrypted portal sessions for ATS/portal login (Workday/Greenhouse/Lever). | `AuthFlow`, `PortalSession` | `/vault/` |
| **notifications** | Saved-search + application-event alerts as an in-app feed and browser web-push (VAPID). | `Subscription`, `WebPushDevice`, `Alert` | `/notifications/` |
| **extension_api** | Endpoints for the MV3 browser extension: page-context capture (upserts postings), submit-event tracking, and profile context for warm intros. | — (uses other apps' models) | `/ext/` |

---

## Frontend (`frontend/src/`)

React 19 + Vite + TypeScript SPA.

```
src/
├── App.tsx            Route table (react-router) + ProtectedRoute wrapper
├── main.tsx           App bootstrap
├── api/               endpoints.ts — typed API client (axios)
├── stores/            Zustand stores (auth, billing, applications, jobs, interview…)
├── components/        Shared UI (GhostRiskBadge, Credits, nav, …)
├── lib/               Helpers (e.g. cooldown logic)
└── routes/            One folder per screen area:
    ├── auth/          Login / register / OAuth callback
    ├── onboarding/    Chat-based profile onboarding
    ├── dashboard/     Outcome-first dashboard + saved jobs + tasks
    ├── jobs/          Jobs list, detail (match, AI breakdown, apply tiers), add-job
    ├── applications/  Kanban pipeline (deep-linked tabs)
    ├── companies/     Per-company hub
    ├── network/       Contacts, contact detail, network graph
    ├── interview/     Interview grill setup / live / report
    ├── resumes/       Resume management
    ├── profile/       Structured profile editor
    └── settings/      Account & preferences
```

---

## Other directories

- **`extension/`** — MV3 browser extension (manifest, popup, `src/`, tests). Talks
  to the `extension_api` app for capture and autofill.
- **`infra/`** — `backend.Dockerfile`, `docker-compose.yml` (dev),
  `docker-compose.prod.yml` (prod).
- **`scripts/`** — EC2 bootstrap (`bootstrap-ec2.sh`) and `deploy.sh`; see
  [deployment.md](deployment.md) and [development-server.md](development-server.md).
- **`docs/`** — this file plus architecture, data model, per-domain deep-dives
  (adapters, agent, billing, networking, notifications, portal automation), and
  planning/vision docs. `README.md` has the full index.

---

## How a job flows through the system (end to end)

1. **Discovery** — `ingestion` (APIs) or `portals` (browser scraper) produce
   canonical posting dicts → `ingestion.services.upsert_postings` → `jobs.JobPosting`
   (Ghost-Job Shield scores risk on the way in).
2. **Match** — `matching` scores the posting against the user's `resumes` /
   `profiles` data.
3. **Enrich** — `jobs` AI breakdown + `tailoring` generate role-specific content
   (charged via `billing`).
4. **Apply** — `applications` runs the chosen tier; the `extension` autofills;
   `vault`/`credentials` supply session/login where needed.
5. **Follow-up** — `interview` preps the user; `networking` surfaces warm intros;
   `notifications` pushes alerts; `streaming` carries live agent output.
