# Architecture

How the pieces fit. For *why* we built it this way see [vision.md](./vision.md).

## System diagram (text)

```
┌──────────────┐    HTTPS     ┌───────────────────────────────────┐
│  Browser     │ ───────────▶ │  daphne (ASGI) / Django + DRF     │
│  (React SPA) │              │                                   │
│              │ ◀──────────  │   ┌─────────────────────────────┐ │
│              │   JWT/JSON   │   │ API views (15 Django apps)  │ │
│              │              │   └─────────────────────────────┘ │
│              │              │   ┌─────────────────────────────┐ │
│              │  WebSocket   │   │ Channels consumers          │ │
│              │ ◀──────────▶ │   │ (notifications, interview)  │ │
└──────────────┘              │   └─────────────────────────────┘ │
                              └────────────┬──────────────────────┘
                                           │
                              ┌────────────┴──────────────────────┐
                              │                                   │
                       ┌──────▼─────┐                     ┌───────▼──────┐
                       │ Postgres   │                     │ Redis        │
                       │ (data)     │                     │ (broker +    │
                       └──────┬─────┘                     │  channels)   │
                              │                           └───────┬──────┘
                              │                                   │
                       ┌──────▼───────────────────────────────────▼──────┐
                       │  Celery workers                                  │
                       │   - ingestion (Adzuna, Greenhouse, …)            │
                       │   - applications (autonomous Playwright submit)  │
                       │   - matching (rescore on-demand)                 │
                       │  Celery beat: scheduled ingestion runs           │
                       └──────────────────────────────────────────────────┘

   ┌──────────────────────────────┐
   │  MV3 browser extension       │  ──── HTTPS ────▶  /api/v1/ext/...
   │  (Phase 2: autofill tier)    │
   └──────────────────────────────┘

   External integrations (per-call, no persistent connections):
     - LLM providers: NVIDIA NIM (guest pool), OpenRouter, OpenAI, Anthropic, CLI delegates
     - Job APIs: Adzuna, Jooble, JSearch (Phase 2), Greenhouse, Lever (Phase 2)
     - Notifications: Resend (email), web-push (VAPID)
     - Payments: Stripe (Phase 1.5+)
     - Google OAuth (sign-in)
```

## Process layout (production)

Five runnable processes — all defined in [infra/docker-compose.yml](../infra/docker-compose.yml):

| Process | Role | Image |
|---|---|---|
| `backend` | daphne ASGI serving HTTP + WebSocket | python:3.12-slim + project |
| `celery` | async tasks (ingestion runs, Playwright submits, parsing) | same |
| `celery_beat` | scheduler for periodic ingestion + maintenance | same |
| `postgres` | relational state | postgres:16-alpine |
| `redis` | Celery broker + Channels group layer | redis:7-alpine |
| `frontend` | Vite dev server (replaced by static hosting in prod) | node:20-alpine |

In local dev without Docker you can skip Celery entirely — `RUN_INGESTION_ASYNC=False` keeps ingestion synchronous in the request cycle.

## Apps overview

15 Django apps. Each is a self-contained boundary with its own `models.py`, `views.py`, `serializers.py`, `urls.py`, `tests/`.

| App | Purpose | Key files |
|---|---|---|
| `accounts` | User, tier, NVIDIA guest-key issuance, JWT, Google OAuth | [models](../backend/accounts/models.py) · [oauth](../backend/accounts/oauth.py) · [views](../backend/accounts/views.py) |
| `profiles` | StructuredProfile + Experience/Education/Skill/Project/Preference | [models](../backend/profiles/models.py) |
| `resumes` | Upload + parse (PDF/DOCX) + versioning | [models](../backend/resumes/models.py) · [parsing](../backend/resumes/parsing.py) |
| `jobs` | Company, Source, JobPosting | [models](../backend/jobs/models.py) · [views](../backend/jobs/views.py) |
| `ingestion` | Source adapters + upsert pipeline + Celery tasks | [services](../backend/ingestion/services.py) · [adapters/](../backend/ingestion/adapters/) |
| `matching` | Resume↔JD scoring (BM25 + skill overlap; LLM rerank optional) | [scorer](../backend/matching/scorer.py) |
| `notifications` | Subscription DSL + Alert + WebPushDevice + Channels broadcast | [filters](../backend/notifications/filters.py) |
| `applications` | Application + AutoApplySession + ApplicationEvent | [models](../backend/applications/models.py) · [views](../backend/applications/views.py) |
| `tailoring` | TailoredResume + CoverLetter generators (LLM-injectable) | [generators](../backend/tailoring/generators.py) |
| `agent` | LangGraph orchestrator + phase-gated tool registry + HITL | [graph](../backend/agent/graph.py) · [tools/](../backend/agent/tools/) |
| `interview` | Interview Grill Chat Agent: research → bank → grill → report | [grilling](../backend/interview/grilling.py) |
| `credentials` | AES-GCM encrypted vault for provider keys | [crypto](../backend/credentials/crypto.py) |
| `extension_api` | Endpoints consumed by the MV3 extension | [views](../backend/extension_api/views.py) |
| `vault` | Faultline-style AuthFlow per portal (Phase 3) | [models](../backend/vault/models.py) |
| `billing` | Stripe + credit ledger (Phase 1.5+) | [models](../backend/billing/models.py) |
| `streaming` | Channels WebSocket consumers (notifications, interview) | [consumers](../backend/streaming/consumers.py) · [routing](../backend/streaming/routing.py) |

## URL structure

Mounted in [config/urls.py](../backend/config/urls.py):

```
/admin/                             Django admin
/api/v1/auth/...                    accounts (register, login, me, google, guest-key)
/api/v1/profile/                    profiles
/api/v1/resumes/                    resumes
/api/v1/jobs/                       jobs (search + detail)
/api/v1/ingestion/run/<src>/        ingestion (admin)
/api/v1/matching/jobs/<id>/         matching
/api/v1/notifications/...           subscriptions, alerts, push
/api/v1/applications/...            applications + approve
/api/v1/tailoring/resume|cover-letter/    tailoring
/api/v1/agent/sessions/...          general chat agent
/api/v1/interview/sessions/...      Interview Grill agent
/api/v1/credentials/                provider keys
/api/v1/ext/...                     browser extension
/api/v1/billing/                    Stripe (Phase 1.5+)
/api/schema/ · /api/docs/           OpenAPI + Swagger UI

/ws/notifications/                  per-user push
/ws/interview/<session_id>/         live grilling stream
```

## Data flow walkthroughs

### A. User uploads a resume

```
React ResumesPage  ─POST multipart─▶  ResumeListCreateView
                                          │
                                          ├─ save Resume(file=…, parse_status='pending')
                                          ├─ resumes.parsing.extract_text(file)
                                          ├─ resumes.parsing.naive_structured_parse(text)  ⊕ LLM (future)
                                          └─ save parsed_json, parse_status='done'
```

The current parser is rule-based so tests don't need an LLM. Production path will call the user's configured LLM via the same injectable pattern as tailoring.

### B. Background ingestion of new postings

```
Celery beat ──▶ ingestion.tasks.run_source('adzuna')
                  │
                  ├─ AdzunaAdapter().fetch(ctx)          ──▶ httpx GET … paginate
                  │   yields normalised dicts
                  ├─ ingestion.services.upsert_postings(source, postings)
                  │   ├─ Company.objects.get_or_create(name, domain)
                  │   └─ JobPosting.objects.update_or_create((source, external_id))
                  └─ IngestionRun(status='success', stats={...})

Then (Phase 2): for each new posting,
        notifications.tasks.dispatch_alerts(posting)
                  ├─ for each Subscription whose filter_json matches: create Alert
                  ├─ stealth_domains: skip postings on a user's blacklist
                  └─ streaming.broadcaster.push_to_user(user_id, {...})
```

### C. User asks the agent for matches

```
React Onboarding/AgentChat ─POST─▶ AgentChatView
                                       │
                                       ├─ AgentMessage(role='user', content=...)
                                       ├─ AgentState(user_id, objective, phase_cap)
                                       └─ agent.graph.run(state, planner=_plan_with_llm)
                                              │
                                              loop while not state.halt:
                                                ├─ planner → list of tool calls
                                                ├─ _execute_tools (asyncio.gather, sem=8)
                                                │   ├─ each call:
                                                │   │   • spec = registry.get(name)
                                                │   │   • if spec.phase > state.phase_cap → 'phase-gated'
                                                │   │   • if HITL_HARD_GATE and no approval_token → halt
                                                │   │   • else asyncio.to_thread(spec.fn, **args)
                                                │   └─ collect observations
                                                ├─ king_review → verdict
                                                └─ if recommend halt → state.halt = True
                                       ├─ AgentMessage(role='assistant', content=str(messages[-1]))
                                       └─ if paused_for_approval → session.status='paused_hitl'
```

See [agent.md](./agent.md) for the phase-gate + HITL contract in depth.

### D. User submits an application autonomously

```
1. React JobDetail → Applications.create(job_id, tier='autonomous')
2. React Auto-Apply panel → Applications.approve(app_id)
       └─ AutoApplySession.issue_approval_token() → returns token
3. Agent run with phase_cap=3 plans submit_application(app_id, approval_token=…)
       └─ agent.tools.builtins.submit_application:
             • verify app.auto_apply_session.approval_token == token
             • set app.status='applied'
4. Notifications channel-layer push 'application_submitted' to user_<id>
```

No path bypasses step 2. The hard gate is in the orchestrator (`agent/graph.py::_execute_tools`) *and* in the tool itself — defence in depth.

### E. Interview Grill session

```
React InterviewGrill → POST /interview/sessions/  {role, stage, difficulty}
       │
       └─ SessionListCreateView.perform_create:
             ├─ research(company, role, stage)                  → session.research
             ├─ generate_question_bank(role, stage, difficulty) → InterviewQuestion rows
             └─ status='ready'

While ready:
   React POST /interview/sessions/<id>/answer/  {answer}
       │
       └─ AnswerView:
             ├─ next unanswered question (order ASC)
             ├─ evaluate_answer(question, answer)               → InterviewTurn
             └─ status='in_progress'

When done:
   React POST /interview/sessions/<id>/report/
       │
       └─ ReportView:
             ├─ summarise_session([turn.evaluation, ...])       → InterviewReport
             └─ status='done'
```

Voice mode in Phase 3 will swap the React text inputs for Deepgram/Riva streams; the server logic is unchanged.

## Configuration & environments

- Base settings: [config/settings/base.py](../backend/config/settings/base.py)
- `local`: `DEBUG=True`, CORS=*, in-memory channels
- `test`: in-memory SQLite, eager Celery, fast password hasher, default `CREDENTIAL_ENCRYPTION_KEY`
- `prod` (TBD): subclass `base.py`, require Redis channel layer, force `RUN_INGESTION_ASYNC=True`, set `ALLOWED_HOSTS`/`CORS_ALLOWED_ORIGINS`

Env keys live in [backend/.env.example](../backend/.env.example).

## Frontend architecture

- **Routing**: react-router under [src/App.tsx](../frontend/src/App.tsx). Each route lives in `src/routes/<area>/<Page>.tsx`.
- **State**: Zustand stores under [src/stores/](../frontend/src/stores/) — one per domain: auth, jobs, applications, interview. Stores hold the canonical list, expose async actions that call the API client, and never live outside the store.
- **API**: [src/api/client.ts](../frontend/src/api/client.ts) for the axios instance with JWT interceptor; [src/api/endpoints.ts](../frontend/src/api/endpoints.ts) for all REST calls grouped by domain (`Auth`, `Profile`, `Resumes`, `Jobs`, `Applications`, `Tailoring`, `Interview`, `Agent`, `Notifications`).
- **Styling**: Tailwind 3.4 via `index.css` + `tailwind.config.js`. No component library.
- **Testing**: vitest + `@testing-library/react`, JSDOM env. Store tests live under `src/stores/__tests__/`.

## Where to look next

- The **tool/HITL contract** that nothing should violate — [agent.md](./agent.md)
- The **data model** if you're adding a field — [data-model.md](./data-model.md)
- The **adapter contract** if you're wiring a new job source — [adapters.md](./adapters.md)
- How to **run things locally** — [development.md](./development.md)
- The **testing rules** before you open a PR — [testing.md](./testing.md)
