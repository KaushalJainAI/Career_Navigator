# Implementation Plan

The phased roadmap that drove the initial scaffold. Read alongside [vision.md](./vision.md) (the *why*) and [architecture.md](./architecture.md) (the *how*).

## Context

Job hunting is fragmented across discovery, tailoring, ATS forms, interview prep, and outcome tracking. Existing tools solve slices; none integrate them behind a single agent that keeps the candidate in control. We're building that platform — patterned on two reference projects on disk (AIAAS for the Django/LangGraph stack, Faultline for the parallel-tool agent loop and Vault-style auth flows) — with the candidate-control invariant enforced by a HITL hard-gate in the orchestrator. See [vision.md](./vision.md) for the full thesis, and [competitive-landscape.md](./competitive-landscape.md) for how each roadmap item positions us against AIHawk, JobSpy, Resume-Matcher, Reactive-Resume/OpenResume, ApplyPilot, the Teal/Huntr/Simplify/Careerflow SaaS set, and Final Round AI — including the user-reported shortcomings of each that we engineer against.

## Locked decisions

- **Stack**: Django 5 + DRF + Celery + Redis + Postgres + React 19 + Vite + Zustand + Tailwind (mirrors AIAAS).
- **Job sources**: aggregator APIs (Adzuna, Jooble, JSearch) + ATS APIs (Greenhouse, Lever) + a **JobSpy-wrapped adapter** for the scrape-hostile big boards (Indeed, LinkedIn, Glassdoor, ZipRecruiter, Google Jobs — compose with the MIT-licensed library rather than re-fighting the anti-bot arms race) + per-company Playwright scrapers for portals JobSpy doesn't cover + user-forwarded email alerts + extension one-click capture + web-search tool + CLI-delegate fallback (Faultline pattern).
- **NVIDIA NIM** shared guest key for unauthenticated/free users (AIAAS pattern); Pro brings own key or uses credits.
- **Auto-apply tier** is per-job user choice: `assist` → `autofill` (extension) → `autonomous` (server Playwright + HITL gate).
- **No embedder.** Lexical scoring + JSONL+ripgrep RAG. See [drop-faiss-and-add-google-auth.md](./drop-faiss-and-add-google-auth.md).

## Phased roadmap

### Phase 1 — MVP (scaffolded)

- Django/React scaffold mirroring AIAAS.
- `accounts` with NVIDIA guest-key issuance + tier model + Google OAuth (mirrors AIAAS `credentials/oauth.py`).
- Onboarding chat (LangGraph agent, tool: `update_profile_field`) → fills `StructuredProfile`.
- Resume upload + parse (PDF/DOCX → JSON via LLM-injectable pipeline).
- Single-source ingestion: Adzuna + Greenhouse public boards (Celery beat).
- Match scorer: lexical token-overlap + skill-overlap (BM25 replacement planned — see drop-embedder doc).
- Resume tailoring generator (one-shot LLM call with JD + master resume).
- Notifications: email (Resend) + web-push (VAPID) + in-app via Channels.
- Saved jobs (manual).
- Stripe basic Free vs Pro tier (Phase 1.5+).
- **Stretch**: match-score explainer with skill-gap learning path; stealth-mode toggle.

### Phase 2 — Discovery & tracking

Ordering within Phase 2 follows the gap analysis in [competitive-landscape.md](./competitive-landscape.md) §4–5: compose where the capability is commoditized (board scraping), build where we're differentiated (Ghost-Job Shield, Grill agent, outcome analytics).

- Adapters: Jooble, JSearch (RapidAPI), Lever ✅; **JobSpy wrapper adapter** (largest coverage gain for the least code — feeds `upsert_postings` like any other adapter; per-source rate budgets + proxy config on the `Source` model, `hours_old`-style freshness params); Playwright scraper framework for what JobSpy doesn't cover; email-forward parser.
- **Ghost-Job Shield** (promoted to flagship — see landscape §6.5): content-hash repost fingerprinting across ingestion runs, `first_seen`/`last_seen` staleness tracking (>45–60 days unchanged), missing-salary + evergreen-req heuristics; ghost-risk score on every job card; auto-apply queues deprioritize high-risk postings. Subsumes and extends the JD red-flag detector (toxic language, unrealistic reqs).
- **Match-score explainability**: the scorer already returns a `gaps` (missing-skill) list and a `breakdown`; extend to structured `{matched_skills, missing_skills, jd_keywords_absent}`, render it on job detail (Resume-Matcher's lesson: the guidance is the product, the number is secondary), and wire the missing-keyword output as the direct input to tailoring prompts.
- **Truthfulness verification pass** in `tailoring/` (landscape §6.1): deterministic post-generation checks — identity fields exactly match profile, claimed skills exist in profile, no AI edit applied without the user seeing the diff. Fails closed; no LLM required; ships with tests.
- **ATS-safe resume export**: canonical JSON resume schema for tailored output (diff the JSON, not the PDF) → 2–3 single-column server-rendered templates → round-trip test that our own `resumes/` parser can read our exports (OpenResume's trick).
- Subscription model with filter DSL (role, location, remote, salary, seniority, keywords, exclude-companies).
- Browser extension: MV3 autofill tier ✅, plus **one-click job capture** from any careers page into `JobPosting` via `/api/v1/ext/` (Teal/Huntr's most-loved feature; feeds the hidden job market our adapters never see); **`PortalRecipe` data-driven field maps** served from the server so new-portal support is a data update, not an extension release (start with Greenhouse/Lever where URL→portal detection is trivial); per-field confidence marking on autofill (landscape §6.6); profile-schema audit against AIHawk's `plain_text_resume.yaml` for long-tail ATS fields (work authorization per country, notice period, relocation); agent-answered free-text form questions behind `HITL_CONFIRM`.
- Cover-letter generator ✅ (now subject to the truthfulness verification pass).
- Applications Kanban (Saved → Tailored → Applied → Phone → Onsite → Offer/Reject) ✅.
- **Interview Grill Chat Agent (text)** — research → tailored question bank → live grilling loop with per-answer evaluation + drilldown → **persisted rubric-scored post-session report** (per-competency scores, weakest answers verbatim, 5-item study plan) that seeds the next session's difficulty ramp. Web-search tool feeds company-specific question banks (the Final Round AI capability, minus the live-copilot direction we explicitly reject).
- Response-rate analytics per resume variant — **the primary dashboard view, not a buried report** (landscape §6.4): response rate per variant, time-to-first-interview, stage conversion. Never "applications sent" as the headline metric.

### Phase 3 — Autonomous apply & intelligence

- Autonomous-apply agent: Playwright + Faultline vault-style AuthFlow per portal.
- HITL approval gates before form submit (Channels prompt, 24h TTL).
- "King" supervisor LLM (AIAAS `executor/king.py` pattern) watching quality per submission.
- LinkedIn session-cookie integration (best-effort RSS + scrape).
- Salary intelligence (Levels.fyi/Glassdoor scrape + LLM normalisation).
- Networking outreach agent (CSV/LinkedIn contacts import, draft warm intros).
- Weekly career-coach digest.
- **Voice mode** for Interview Grill Chat Agent (Deepgram or NVIDIA Riva) — transcription-first (user speaks, agent reads) as the cheap 80% before speech-to-speech. Preparation only; no live-interview copilot, ever (see vision "What we are not building").
- Salary negotiation rehearsal.
- **Stripe billing with trust requirements** (landscape §6.3, non-negotiable at launch): one-click self-serve cancel, credits roll over while subscribed, one-sentence refund policy honoured programmatically, no rebilling after cancellation. These ship in the same commit as checkout — billing hostility is the #1 one-star theme across every paid competitor.
- **BYOK / local-model option** surfaced as a user-facing setting via the credentials vault (the `llm=` injection already supports it) — privacy differentiation for stealth-mode users, following Resume-Matcher's local-first pivot.

## Backend apps — details

See [data-model.md](./data-model.md) for per-app entity details; [architecture.md](./architecture.md) for app responsibilities. Apps shipped in Phase 1:

`accounts` · `profiles` · `resumes` · `jobs` · `ingestion` · `matching` · `notifications` · `applications` · `networking` · `tailoring` · `agent` · `interview` · `credentials` · `extension_api` · `vault` · `billing` · `streaming` · `ai`.

## Agent / tool design

LangGraph plan→execute→observe→supervisor loop with parallel tool batching (asyncio.gather, semaphore=8). Phase-gated registry; HITL hard-gates on irreversible actions. Full tool table and the canary test live in [agent.md](./agent.md).

## Critical integrations

- **NVIDIA NIM** (guest pool, AIAAS pattern) — default LLM for free tier.
- **OpenRouter / OpenAI / Anthropic** — BYO-key for Pro.
- **Claude Code / Codex / Gemini CLI** — Faultline-style delegate fallback when APIs absent.
- **Playwright** — portal automation + scraping (separate Celery queue, headless containers).
- **Stripe** — billing.
- **VAPID web-push** — browser notifications.
- **Resend** — email.
- **Adzuna / Jooble / JSearch / Greenhouse / Lever** — job APIs.
- **Deepgram or NVIDIA Riva** (Phase 3) — voice for mock interviews.

## Implementation strategy — copy, don't regenerate

To minimise token usage and accelerate development, copy source files verbatim from AIAAS / Faultline (on disk at `c:\Users\91700\Desktop\AIAAS` and `c:\Users\91700\Desktop\Faultline`) and edit in place. Workflow per module:

1. Identify the closest analogue in AIAAS or Faultline.
2. Copy the file/folder into the Career Navigator tree.
3. Edit with targeted diffs — rename, repurpose, strip unused.
4. Run the unit test for that module immediately.

Source → destination highlights:

| Source | Destination | Edits |
|---|---|---|
| `AIAAS/Backend/core/models.py` | `backend/accounts/models.py` | rename app, strip workflow-specific fields, add `stealth_domains` |
| `AIAAS/Backend/credentials/oauth.py` | `backend/accounts/oauth.py` | swap aiohttp for httpx (fixes a latent sync-call-of-async bug) |
| `AIAAS/Backend/chat/graph.py` | `backend/agent/graph.py` | replace tool registry, keep loop structure |
| `AIAAS/Backend/credentials/` | `backend/credentials/` | near-verbatim |
| `AIAAS/Backend/streaming/` | `backend/streaming/` | near-verbatim |
| `AIAAS/Backend/workflow_backend/settings/` | `backend/config/settings/` | rename project, swap apps list |
| `Faultline/core/agent.py` | `backend/agent/graph.py` (pattern) | parallel batching + tiered context window + CLI-delegate fallback |
| `Faultline/vault/` | `backend/vault/` | base verbatim; per-portal AuthFlow defs are Phase 3 |
| `AIAAS/better-n8n-frontend/src/api/client.ts` | `frontend/src/api/client.ts` | swap base URLs |

**Rule**: if a target file is >70% similar to an existing AIAAS/Faultline file, copy + edit. Only hand-write files with no analogue.

## Testing policy

Tests ship with the code; tests don't hit the network. Full policy: [testing.md](./testing.md). HITL gate canary lives at [backend/agent/tests/test_graph.py](../backend/agent/tests/test_graph.py).

## Verification

End-to-end smoke check after a fresh setup:

```bash
cd backend && pytest -q              # backend tests
cd frontend && npm run test          # frontend tests
cd backend && python manage.py runserver   # boot the API
# Then: visit http://localhost:5173, register a user, upload a resume,
# browse jobs (after seeding a Source), trigger a match score.
```

For ingestion smoke testing without Celery:

```bash
python manage.py shell -c "from ingestion.tasks import run_source; print(run_source('adzuna', query='python'))"
```

## Phase status (current)

- Phase 1: **implemented beyond scaffold**. All 18 apps are wired; Google OAuth, API tokens, deterministic onboarding profile updates, profile readiness, resume upload/parse, skill extraction, matching, real dashboard stats, applications Kanban with job details, tailoring, cover letters, notification subscriptions, credits ledger, and Interview Grill text mode are present.
- Phase 2: **partially implemented**. Apply workflow now has distinct `assist`, `autofill`, and `autonomous` preparation paths, application audit events, HITL approval-token issuance for autonomous mode, frontend review panels for next actions plus generated resume/cover-letter materials, and manual network contact seeding. Extension APIs/parsers exist, but full extension install/autofill/submit validation remains pending.
- Phase 3: **pending**. Server-side Playwright autonomous submission, portal AuthFlows, LinkedIn session integration, salary intelligence, Stripe checkout/webhooks, advanced analytics, and voice interview mode are not complete.

## Staged functionality completed

The staged functionality pass converted several scaffolded surfaces into working flows:

1. **Dashboard and applications**
   - Added `/api/v1/applications/stats/` for real dashboard KPIs.
   - Application serializers now include `job_detail` so cards display job/company/location context.
   - Frontend dashboard and Kanban consume those real values.

2. **Onboarding**
   - Onboarding chat now updates `StructuredProfile` and `Skill` records using a deterministic extractor.
   - The chat returns user-facing save confirmations instead of raw observation JSON.

3. **Resume parsing and matching**
   - Fallback resume parsing extracts common technical skills.
   - Match scoring infers job-description skills when explicit JD skills are not supplied.

4. **Apply workflow**
   - Added `/api/v1/applications/prepare/`.
   - `assist` saves the application and records `assist_prepared`.
   - `autofill` marks the application ready and records `autofill_prepared`.
   - `autonomous` marks the application ready, creates/uses an `AutoApplySession`, issues an approval token, and records `autonomous_prepared`.

5. **Tailoring materials**
   - Job detail can generate and display tailored resume and cover letter materials.
   - Tailored resume generation moves saved applications to `tailored`.
   - Tailoring endpoints write `tailored_resume_generated` and `cover_letter_generated` events.

6. **Onboarding completion and profile readiness**
   - Profile responses now include readiness checks, a readiness score, missing sections, and a ready flag.
   - The profile page displays readiness and missing pieces.
   - Settings/profile routes are available from the authenticated shell.

7. **Notifications workflow**
   - Added detail/update/delete support for notification subscriptions.
   - Settings includes an alert subscription manager for name, keywords, location, remote-only filtering, enable/pause, and delete.

8. **Network workflow**
   - Network graph page now supports adding contacts manually.
   - Added contacts refresh the graph so users can seed their own network without using the extension.

9. **Billing and credits**
   - Billing now exposes `/api/v1/billing/summary/`, `/api/v1/billing/ledger/`, and `/api/v1/billing/top-up/`.
   - Added serializers and API tests for the credit ledger.
   - Added a Billing & credits frontend page linked from Settings.
   - Stripe remains intentionally disabled until checkout/webhooks are implemented.

Latest verification:

```bash
cd backend && pytest -q              # 131 passed
cd frontend && npm run test -- --run # 5 tests passed
cd frontend && npm run build         # passed
```

## Related plans

- [dynamic-data-pipeline-plan.md](dynamic-data-pipeline-plan.md) — live data ingestion with
  freshness/liveness expiry, scheduled refresh + sweeps, and a precomputed per-user
  personalized feed (replaces the frontend's dummy data). Proposed; not yet implemented.
