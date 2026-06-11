# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repo at a glance

Career Navigator is an AI-powered job-hunt SaaS: real-time alerts, structured-profile NL onboarding, resume↔JD match scoring, AI resume + cover-letter tailoring, tiered auto-application (assist → autofill → autonomous), and a dedicated **Interview Grill Chat Agent**. Backend is Django 5 + DRF + Celery + Channels; frontend is Vite + React 19 + Zustand + Tailwind. The repo lives at `c:\Users\91700\Desktop\Carrer Navigator` — note the **misspelt `Carrer`** in the path.

The architecture is patterned on two reference projects on the same disk:
- **AIAAS** at `c:\Users\91700\Desktop\AIAAS` — auth/tier system, LangGraph chat agent (`Backend/chat/graph.py`), AES-encrypted credentials vault (`Backend/credentials/`), Django Channels streaming, Google OAuth flow (`Backend/credentials/oauth.py` + `Backend/core/views.py:185`).
- **Faultline** at `c:\Users\91700\Desktop\Faultline` — plan→execute→observe loop with parallel tool batching (`core/agent.py`), Vault-style dynamic AuthFlow for portal login (`vault/`).

Read those files when porting new functionality. Project policy: **copy verbatim and edit in place** rather than regenerating equivalent code — the source→destination map is in [docs/implementation-plan.md](docs/implementation-plan.md) and partially in the README's app table.

## Commands

All backend commands run from `backend/`; all frontend commands from `frontend/`.

| Task | Command |
|---|---|
| Install backend deps | `pip install -r requirements.txt` |
| Run migrations | `python manage.py makemigrations && python manage.py migrate` |
| Run dev server (HTTP) | `python manage.py runserver` |
| Run dev server (ASGI, for WS) | `daphne -b 0.0.0.0 -p 8000 config.asgi:application` |
| Celery worker | `celery -A config worker -l info` |
| Celery beat | `celery -A config beat -l info -S django` |
| Backend tests | `pytest -q` |
| Single backend test file | `pytest backend/<app>/tests/test_<name>.py -q` |
| Single backend test | `pytest backend/<app>/tests/test_<name>.py::test_<fn> -q` |
| Frontend dev | `npm run dev` |
| Frontend build | `npm run build` |
| Frontend tests | `npm run test` |
| Full stack via Docker | `cd infra && docker compose up` |

Pytest config in `backend/pytest.ini` points at `config.settings.test` (in-memory SQLite, eager Celery, MD5 password hasher). The `conftest.py` at `backend/conftest.py` sets a default `CREDENTIAL_ENCRYPTION_KEY` for tests and exposes `user`, `api_client`, `auth_client` fixtures.

Required env before backend starts: `CREDENTIAL_ENCRYPTION_KEY`. See `backend/.env.example`.

## Architecture invariants worth knowing before editing

These are non-obvious from a single-file read.

### 1. Phase gates + HITL hard-gate in the agent

`backend/agent/tools/registry.py` defines `HITL_NONE`, `HITL_CONFIRM`, `HITL_HARD_GATE`. The orchestrator at `backend/agent/graph.py` enforces both:
- A tool whose `phase` exceeds `AgentState.phase_cap` returns `{'error': 'phase-gated'}` without running.
- A `HITL_HARD_GATE` tool **must** receive an `approval_token` on the tool call or it short-circuits, the state pauses, and the agent halts. The token is issued by `applications/views.py::ApproveAutoApplyView` on the `AutoApplySession.approval_token` field. `agent/tools/builtins.py::submit_application` cross-checks this token before flipping an application to `applied`. **Never bypass this** — there is a test in `backend/agent/tests/test_graph.py` that asserts a HITL-hard-gate tool cannot run without a valid token.

### 2. LLM is always injected, never imported at module top

`tailoring/generators.py`, `interview/grilling.py`, and the planner stub in `agent/graph.py` all accept `llm=` callables. Default is `_default_llm` (a no-op or echo) so unit tests run without API keys. When wiring a real provider, do it inside the view or task that calls these, not at module import time. Same pattern AIAAS uses in `chat/views.py::execute_llm`.

### 3. JobPosting is the canonical job record

`jobs/models.py::JobPosting` is keyed `(source, external_id)` and upserted by `ingestion/services.upsert_postings`. Every adapter under `ingestion/adapters/` returns a normalised dict (shape documented in `adapters/base.py`); never persist a `JobPosting` directly from an adapter — always go through `upsert_postings` so the Company row is reused and rerunning a source is idempotent.

### 4. Embedder is being removed

Despite `faiss-cpu` and `sentence-transformers` being in `backend/requirements.txt`, neither is imported anywhere. The matching layer uses a pure-Python deterministic `hash_embed` + cosine in `matching/embeddings.py`. The team's direction (documented in `docs/drop-faiss-and-add-google-auth.md`) is to replace this entirely with **BM25 + skill-overlap** for resume↔JD scoring and **JSONL + ripgrep** for any "RAG" need. Do not add new code that depends on embeddings or vector DBs.

### 5. Chat memory mirrors AIAAS, not RAG

`agent/models.py::AgentSession` + `AgentMessage` rows are the durable memory. Inside a turn, rebuild a textual trajectory from recent messages and inject it as `--- PRIOR STEPS ---` into the next LLM prompt — the same pattern as `AIAAS/Backend/chat/graph.py::agent_node` lines ~150-170. Plain chat does not use RAG.

### 6. Credentials are encrypted, never returned

`credentials/crypto.py` does AES-GCM with the env-derived 32-byte key. `Credential.set_secret()` / `.reveal()` are the only entry points; the ciphertext is the only thing persisted. Serializers in `credentials/serializers.py` accept `secret` as write-only and never expose it on read. Never log a revealed secret.

### 7. Stealth mode filters at query time

`accounts/UserProfile.stealth_domains` is honoured in `jobs/views.py::JobListView.get_queryset` — postings whose `company.domain` is in the list are excluded. New job-list endpoints (Phase 2 adapters, the extension API, etc.) must apply the same filter.

### 8. URLs are versioned under `/api/v1/`

`config/urls.py` mounts every app under `api/v1/<app>/`. Browser extension talks to `/api/v1/ext/...`. WebSockets live at `/ws/notifications/` and `/ws/interview/<id>/` (routing in `streaming/routing.py`).

## Testing policy

Every Django app ships unit tests under `<app>/tests/test_*.py` in the same commit as the code. Pytest config auto-discovers them. Tests must not require external network — adapters use injectable HTTP clients (`httpx.MockTransport`), LLM-using code uses injectable `llm=` callables, and the Google OAuth view has a `provider_factory` injection point used by `accounts/tests/test_oauth.py`. Frontend tests live under `frontend/src/**/__tests__/` and run via `vitest`.

## Implementation phases (current state)

- **Phase 1 (MVP) — implemented beyond scaffold**: accounts (incl. Google OAuth + API tokens), profiles, resumes, jobs, ingestion (Adzuna + Greenhouse), matching, notifications, applications, networking, tailoring (incl. cover letters), agent, interview (Grill text mode + post-session report), credentials, extension_api, vault skeleton, billing (credit ledger; Stripe checkout still disabled), streaming, ai (LLM provider transports). 18 apps total.
- **Phase 2 — partially implemented**: Jooble/JSearch/Lever adapters landed (code + tests; live-key smoke pending); tiered apply (assist/autofill/autonomous) with HITL approval tokens; MV3 extension autofill bridge + CI; **Ghost-Job Shield** (flagship — `jobs/ghost.py` deterministic risk scorer wired into the ingestion upsert, exposed on the jobs API + UI, deprioritized in apply-prepare; subsumes the JD red-flag detector); expanded Playwright E2E across the core flows. **Still pending**: JobSpy-wrapped adapter, Playwright scraper, email-forward parser, web-search tool, extension one-click job capture, match-explainability UI, truthfulness verification pass, ATS-safe resume export, response-rate analytics. See [docs/competitive-landscape.md](docs/competitive-landscape.md) for the prioritisation rationale.
- **Phase 3 — pending**: autonomous-apply with portal AuthFlows, LinkedIn integration, salary intelligence, Stripe checkout/webhooks (with billing-trust requirements), voice mode for the interview agent.
