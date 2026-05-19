# The Agent: tool registry, phase gates, HITL

The single most safety-critical subsystem. Everything that calls an LLM with the power to do something on the user's behalf goes through this. Read this before touching anything under [backend/agent/](../backend/agent/), [backend/interview/](../backend/interview/), [backend/tailoring/](../backend/tailoring/), or [backend/applications/views.py](../backend/applications/views.py).

## Mental model

Three concentric defences:

```
       ┌────────────────────────────────────────────────────┐
       │  Phase cap (1 / 2 / 3)                             │   tier-based capability ceiling
       │  enforced in orchestrator                          │
       │   ┌────────────────────────────────────────────┐   │
       │   │  HITL hard-gate                            │   │   per-call approval token
       │   │  enforced in orchestrator + inside the tool│   │
       │   │   ┌────────────────────────────────────┐   │   │
       │   │   │  Tool body                         │   │   │   the actual side effect
       │   │   │  (e.g. submit_application)         │   │   │
       │   │   └────────────────────────────────────┘   │   │
       │   └────────────────────────────────────────────┘   │
       └────────────────────────────────────────────────────┘
```

A tool runs only if **all three** layers say yes. Each is independently testable. Defence in depth means a bug in the orchestrator cannot let `submit_application` send a real application.

## The contract

### Tool spec — `agent/tools/registry.py`

Every tool is registered with `@tool(name, phase, hitl, params_schema, description)`.

```python
HITL_NONE       = 'none'      # safe — read-only, idempotent, or user-visible suggestion
HITL_CONFIRM    = 'confirm'   # the next side-effecting step needs user confirm
HITL_HARD_GATE  = 'gate'      # must have approval_token, defence-in-depth check
```

The registry is process-global. The Django app's `ready()` hook in [agent/apps.py](../backend/agent/apps.py) imports `agent.tools.builtins` so registration happens once at startup. Tests use `registry.clear()` to reset between cases — see [agent/tests/test_graph.py](../backend/agent/tests/test_graph.py).

### Orchestrator — `agent/graph.py`

```python
class AgentState:
    user_id: int | None
    objective: str
    phase_cap: int            # 1, 2, or 3 — capped by user tier
    messages: list[dict]
    pending_tool_calls: list[dict]
    observations: list[dict]
    halt: bool
    paused_for_approval: dict | None
```

Each `step()` runs four nodes:

1. **plan** — call the LLM (or test stub) to produce `pending_tool_calls`.
2. **execute** — `_execute_tools` walks the list, runs each call under a semaphore (max 8 concurrent, Faultline-style), and for each:
   - `if spec.phase > state.phase_cap` → return `{'error': 'phase-gated'}`. **Never runs the body.**
   - `if spec.requires_approval() and not call.get('approval_token')` → write to `state.paused_for_approval`, set `state.halt = True`. **Never runs the body.**
   - Otherwise run `spec.fn(**call.get('args', {}))` on a thread (so blocking ORM calls don't stall the event loop).
3. **observe** — store results in `state.observations`.
4. **king** — `king_review` reads the observations and recommends `continue` or `halt-and-ask-user`. This is the Faultline supervisor pattern; replace its deterministic body with an LLM critique when wiring real providers.

### Tool body — `agent/tools/builtins.py`

The body itself **re-checks** the approval token. This is the third defence — if a future bug in the orchestrator forgets to gate, the tool still refuses:

```python
@tool('submit_application', phase=3, hitl=HITL_HARD_GATE, ...)
def submit_application(*, application_id, approval_token=''):
    app = Application.objects.get(pk=application_id)
    if not approval_token or app.auto_apply_session is None:
        return {'ok': False, 'error': 'missing approval_token'}
    if app.auto_apply_session.approval_token != approval_token:
        return {'ok': False, 'error': 'invalid approval_token'}
    # only now mutate
    app.status = 'applied'
    app.save(update_fields=['status', 'updated_at'])
    return {'ok': True, ...}
```

### Token issuance — `applications/views.py`

The token is created **only** by an authenticated POST to `/api/v1/applications/<id>/approve/`. It lives on the `AutoApplySession` row associated with that application, is `secrets.token_urlsafe(32)`, and is one-shot in practice (we should expire it after use — Phase 2 TODO).

## Phase table (Phase 1 + Phase 2 + Phase 3)

From [agent/tools/builtins.py](../backend/agent/tools/builtins.py) plus the future tools listed in the original implementation plan.

| Tool | Phase | HITL | Notes |
|---|---|---|---|
| `search_jobs(filters)` | 1 | none | Read JobPosting; honours stealth_domains (Phase 2) |
| `web_search(q)` | 1 | none | Provider-routed; rate-limited per tier |
| `fetch_company_info(domain)` | 1 | none | Wraps `jobs.Company` + LLM enrichment |
| `parse_resume(file_id)` | 1 | none | Calls resumes.parsing + LLM |
| `score_match(resume_id, job_id)` | 1 | none | Calls matching.scorer |
| `tailor_resume(resume_id, job_id)` | 1 | none | Calls tailoring.generators; result is suggestion only |
| `update_profile_field(user_id, field, value)` | 1 | none | Mutates StructuredProfile; constrained by allowed-field whitelist |
| `draft_cover_letter(application_id)` | 2 | none | Calls tailoring.generators |
| `scrape_portal(url)` | 2 | none | Playwright, runs in separate Celery queue |
| `salary_lookup(role, location, company)` | 3 | none | Phase 3; external data + LLM normalise |
| `autofill_form(application_id)` | 2 | confirm | Returns payload to extension; user clicks "fill" |
| `request_user_approval(prompt, ttl)` | 3 | yes | Pushes a Channels event; waits up to `ttl` seconds |
| **`submit_application(application_id)`** | **3** | **HARD GATE** | The only tool that mutates an application to `applied` |
| `outreach_draft(contact_id, context)` | 3 | yes | Drafts a message but does not send |
| `research_company(name_or_domain)` | 2 | none | Used by Interview Grill |
| `fetch_interview_experiences(company, role)` | 2 | none | Used by Interview Grill |
| `generate_question_bank(role, stage, difficulty)` | 2 | none | Used by Interview Grill |
| `evaluate_answer(question, answer, rubric)` | 2 | none | Used by Interview Grill |
| `drill_followup(weakness)` | 2 | none | Used by Interview Grill |

The Interview Grill tools currently live as direct functions in [interview/grilling.py](../backend/interview/grilling.py); they will be promoted into the shared registry when the general agent gains awareness of interview prep.

## Adding a new tool

1. Decide its phase. **Default to the highest plausible phase** — under-gating is harder to fix than over-gating.
2. Decide HITL. If the tool causes any irreversible external action (submit, send, post, delete) it is `HITL_HARD_GATE`. If it produces a draft that the user will manually trigger, `HITL_CONFIRM`. Otherwise `HITL_NONE`.
3. Add the function in `agent/tools/builtins.py` (or a new module under `agent/tools/`).
4. Register with `@tool(...)`. Provide `params_schema` so the planner LLM gets typed hints.
5. Inside the body, re-check any HITL precondition. Don't trust the orchestrator alone.
6. Add a test in `agent/tests/test_graph.py` that asserts the gate works. Pattern:
   ```python
   def test_my_tool_is_phase_gated(): ...
   def test_my_tool_pauses_without_token(): ...   # if HITL_HARD_GATE
   def test_my_tool_runs_with_valid_token(): ...
   ```

## Memory & context (vs RAG)

The agent's durable memory is **DB-backed**:
- [agent/models.py](../backend/agent/models.py) `AgentSession` holds the conversation, pending approval, status (`active` | `paused_hitl` | `done` | `failed`).
- `AgentMessage` rows are ordered by `created_at` per session; `tool_calls` and `tool_name` fields carry the structured trace.

Inside a single turn the orchestrator builds an in-prompt **trajectory** from `state.observations` and prior messages, the same shape AIAAS uses in [AIAAS/Backend/chat/graph.py:150](../../AIAAS/Backend/chat/graph.py):

```
--- PREVIOUS ACTIONS & TOOL RESULTS IN THIS TURN ---
Assistant Action: <content>
Calls: search_jobs({...}), score_match({...})
Tool 'search_jobs' Result: [{...}, {...}]
--- END PREVIOUS ACTIONS ---
```

That is how the agent "remembers" within a turn without us managing a separate context store.

**No RAG.** We don't build a vector index over chat history. If long-conversation recall becomes a problem, the plan is to spill older turns to a JSONL transcript per session that the agent can `grep` via a `kb_search` tool — see [drop-faiss-and-add-google-auth.md](./drop-faiss-and-add-google-auth.md) §3.

## The Interview Grill Chat Agent

Lives in [backend/interview/](../backend/interview/). Architectural note: it is conceptually an agent but does not currently share the LangGraph orchestrator — the loop is more linear (research → bank → loop(ask, evaluate, drill) → report) and the gating story is simpler (everything is Phase 2, no hard gates).

Core functions in [interview/grilling.py](../backend/interview/grilling.py):

```python
research(company, role, stage, *, llm=…) -> dict
generate_question_bank(role, stage, *, difficulty, research_notes, llm=…) -> list[dict]
evaluate_answer(question, answer, *, llm=…) -> dict   # 0..1 scores + drill_focus
drill_followup(weakness) -> dict                       # Phase 2 extension
summarise_session(turns) -> dict                       # strengths, gaps, study_plan
```

All four accept `llm=` injection. The default falls back to a deterministic heuristic so tests pass without a provider. The Django models in [interview/models.py](../backend/interview/models.py) persist `InterviewSession`, `InterviewQuestion`, `InterviewTurn`, `InterviewReport`. Live grilling streams via the `/ws/interview/<session_id>/` Channels consumer ([streaming/consumers.py::InterviewConsumer](../backend/streaming/consumers.py)).

## Failure modes & guardrails (checklist before merging agent-related changes)

- [ ] No tool body imports an LLM library at module top level.
- [ ] No new tool defaults to `phase=1` unless it is genuinely read-only.
- [ ] No HITL hard-gate tool relies solely on the orchestrator check.
- [ ] The orchestrator's `_execute_tools` is the only path that calls tool bodies. (No view directly invokes `spec.fn`.)
- [ ] The approval-token path is end-to-end: API view issues → frontend passes → planner emits → orchestrator forwards → tool re-checks.
- [ ] Phase 2 changes don't accidentally promote a Phase 3 tool to Phase 2.
- [ ] Tests in `agent/tests/test_graph.py` still pass — the gate tests are the canary.

If you're not sure whether something needs HITL, ask. The cost of one extra confirmation is small; the cost of an unwanted submitted application is large.
