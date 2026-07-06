# AI Integration

How Career Navigator uses AI — every LLM touch-point, what's wired live today vs.
a hook awaiting a provider, and the design rules that keep the AI safe, testable
and cheap.

> Companion to [architecture.md](architecture.md) and
> [project-structure.md](project-structure.md).

## Guiding principles

1. **One transport, injected everywhere.** All model access goes through
   `ai/providers.py::get_configured_llm()`, which returns a plain
   `Callable[[str], str]` (or `None`). Every feature takes that callable as an
   argument, so tests inject a deterministic stub and never hit the network.
2. **Deterministic fallback, always.** With no provider configured (or in tests),
   each feature degrades to a deterministic path — seed question banks, empty
   breakdowns, hash-based embeddings — rather than failing.
3. **AI reasons; scripts fetch.** Job discovery (ingestion APIs, portal scrapers)
   and the Ghost-Job Shield are **100% deterministic** — no LLM. AI only operates
   on data we've already collected. (See [adapters.md](adapters.md),
   [portal-automation-plan.md](portal-automation-plan.md).)
4. **Charge before spend, refund on failure.** Expensive LLM actions go through
   the credit ledger (`billing/`) *before* the model runs, and refund if it
   produces nothing usable.
5. **Ground in the user's real profile.** Generative features are prompted from
   the `StructuredProfile` / posting text so output stays truthful, not invented.

## The transport layer — `ai/providers.py`

| Piece | Role |
|---|---|
| `get_configured_llm()` | Resolves `AI_PROVIDER` → a completion callable, or `None`. |
| `nvidia_complete()` | **Hosted** NVIDIA NIM guest pool (`nvidia/llama-3.3-nemotron-super-49b-v1`) via the OpenAI-compatible client. The default for SaaS/server deploys. |
| `codex_cli_complete()` | **Local-only** Codex CLI transport (needs `codex login` on the machine); for local dev, not shared use. |
| `with_fallback(primary, fallback)` | Chains a secondary provider when the primary returns empty. |
| `configured_model_label()` | Human-readable model id, stamped onto generated artifacts for provenance. |

Configured via env (`AI_PROVIDER`, `AI_FALLBACK_PROVIDER`, `NVIDIA_API_KEY`,
`NVIDIA_GUEST_MODEL`, `NVIDIA_MAX_TOKENS`, `CODEX_CLI_*`) — see `example.env`.

## Where AI is used

| # | Feature | Module | LLM role | Status |
|---|---|---|---|---|
| 1 | **AI job breakdown** | `jobs/enrichment.py`, `jobs/views.py` | Expand a posting into responsibilities / requirements / benefits / company summary | **Live** |
| 2 | **Resume tailoring** | `tailoring/generators.py::tailor_resume` | Rewrite the master resume for one JD | **Live** |
| 3 | **Cover letter** | `tailoring/generators.py::draft_cover_letter` | Draft a per-JD cover letter | **Live** |
| 4 | **Interview Grill Agent** | `interview/grilling.py`, `interview/views.py` | Company research, question-bank generation, STAR-rubric answer scoring, session summary | **Live** (LLM + deterministic seed fallback) |
| 5 | **Agent orchestrator** | `agent/graph.py`, `agent/tools/` | Plan→execute→observe loop; tools query ingested data (`search_jobs`, `score_match`) | **Hook** — planner is a deterministic reference impl; `_plan_with_llm` is the swap-in point |
| 6 | **Resume↔JD matching** | `matching/scorer.py`, `matching/embeddings.py` | Similarity + skill overlap | **Deterministic today** — hooks for real embeddings / LLM critique, not yet wired |
| 7 | **Chat onboarding** | `agent/onboarding.py` | Extract profile facts from chat text | **Deterministic** — regex/pattern extraction, not an LLM |

### 1. AI job breakdown — *live*
`generate_breakdown()` prompts the model for a strict-JSON breakdown of a
posting, parses it tolerantly (strips code fences, isolates the JSON object),
and rejects all-empty results so we never cache junk. Wired to billing in
`JobBreakdownView`: cached once per job (shared, so cache hits are free),
charged 2 credits on a real generation, **refunded** if generation fails, and
`503` when no LLM is configured. Model label is stored on the result for
provenance.

### 2–3. Resume tailoring & cover letters — *live*
`tailor_resume()` and `draft_cover_letter()` take the parsed master profile + JD
and produce tailored text, prompting the model to **preserve truthfulness**
(the profile is the grounding source). Both accept an injectable `llm` so tests
run deterministically. Credit-charged via `tailoring/views.py`.
> Note: truthfulness is currently enforced at the *prompt* level. A stronger
> deterministic verification pass (identity/skills must match the profile, fail
> closed) is a documented intent in the vision, not yet a separate code path.

### 4. Interview Grill Agent — *live, with deterministic floor*
`interview/grilling.py` splits into unit-testable stages, each taking an optional
`llm`:
- `research()` — company/role/interview-process notes;
- `generate_question_bank()` — tailored questions by stage + difficulty (falls
  back to `_seed_bank()` deterministic questions with no LLM);
- `evaluate_answer()` — scores an answer against a STAR rubric;
- `summarise_session()` — builds the report + study plan.

`interview/views.py` wires the real provider via `get_configured_llm()`.
Credit-charged (`mock_interview`).

### 5. Agent orchestrator — *hook*
`agent/graph.py` is a deliberately simple, deterministic plan→execute→observe→
"King" supervisor loop mirroring the AIAAS/Faultline pattern. It's the seam where
a real planner LLM plugs in (`_plan_with_llm`); the tools in `agent/tools/`
(`search_jobs`, `score_match`) already run against the live database. Today the
loop is a reference implementation, not a production planner.

### 6. Matching — *deterministic today*
`score_resume_against_job()` combines an embedding cosine similarity (0.6) with
skill-overlap (0.4), returning a score, breakdown, matched skills, gaps, and a
colour-coded explanation. `embed()` currently uses `hash_embed` — a deterministic
hash-bucket vector — with a documented hook to swap in sentence-transformers or
NIM embeddings. The docstring's "optional LLM critique" is a planned enhancement,
**not wired** into the live scorer.

### 7. Chat onboarding — *deterministic*
`agent/onboarding.py` extracts profile facts (name, links, phone, skills…) from
chat messages using regex/pattern matching — **no LLM**. Worth calling out
because the UX *feels* AI-driven but the extraction is deterministic and free.

## What is deliberately NOT AI

- **Job discovery** — `ingestion/adapters/*` (API calls) and `portals/scrapers/*`
  (Playwright + fixed CSS/XPath selectors). Parsing is pure and unit-tested.
- **Ghost-Job Shield** — `jobs/ghost.py` fingerprinting + heuristics.
- **Matching core & onboarding extraction** — see above.
- **ATS export** — server-side `.txt`/`.docx` rendering from one shared builder.

Keeping these deterministic makes them cheap, reproducible, and testable without
a model, and avoids paying an LLM for work that doesn't need judgement.

## Testing posture

Because every AI feature takes an injected `llm` callable and has a deterministic
fallback, the **entire suite runs with no provider and no network** — stubs
return canned strings, seed banks stand in for question generation, and
`hash_embed` stands in for embeddings. The live provider path is exercised
separately (e.g. the job-breakdown smoke test against NVIDIA NIM).

## Models & configuration

- **Default (hosted):** `AI_PROVIDER=nvidia`, model
  `nvidia/llama-3.3-nemotron-super-49b-v1` via NVIDIA NIM.
- **Local dev:** `AI_PROVIDER=codex_cli` (requires `codex login`).
- **BYOK / local-model** friendly by design — swap the provider without touching
  feature code, since everything depends on the `get_configured_llm()` seam.
