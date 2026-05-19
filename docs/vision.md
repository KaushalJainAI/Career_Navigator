# Vision

## The problem

Modern job hunting is a fragmented, demoralising pipeline. A serious candidate runs into the same five frictions on every cycle:

1. **Discovery noise** — LinkedIn churn, Indeed spam, three aggregators, the company's own career page, plus a hidden job market on Twitter/Slack/referrals. Nothing unifies them.
2. **Resume rewriting fatigue** — every JD wants something slightly different, and the candidate either over-tailors (slow) or under-tailors (low conversion).
3. **ATS form drudgery** — Workday, Greenhouse, and Lever ask the same 40 fields in 40 different shapes. Apply to 50 jobs and you've spent a weekend typing your address.
4. **Interview prep guesswork** — generic prep guides don't tell you what *this* company *actually* asks. Glassdoor is half-stale, Blind is anecdote.
5. **No feedback loop** — applications go into a void. You can't tell which resume variant works, which JDs are red flags, which weeks are wasted.

Existing tools tackle slices: **Teal** does tracking, **Jobscan** does keyword matching, **Simplify** does autofill, **Final Round AI** does mock interviews. None of them sit on top of a single agent that *researches the company*, *tailors the resume*, *files the application*, *coaches the interview*, and *learns from outcomes* — with the candidate in the driver's seat.

## The thesis

A single AI agent platform, owned by the candidate, that:

- **Discovers** roles across every source (aggregator APIs + company portals + LinkedIn + email forwards + LLM-driven web search).
- **Researches** the company, role, and team using whatever the open web reveals.
- **Tailors** the master resume and cover letter per posting, with audit-trail diffs.
- **Applies** at three escalating tiers — **assist** (the human submits), **autofill** (extension fills the form), **autonomous** (the agent submits, gated on an approval token).
- **Grills** the candidate on the actual interview questions that company asks, in conversational rounds, and produces a focused study plan.
- **Learns** which resume variants land interviews, which JDs are ghost jobs, which weeks of effort move the needle.

The candidate stays in control. The platform never submits without explicit per-application approval. The platform never sends a tailored resume that misrepresents the candidate. Truthfulness is a hard constraint enforced by the prompt and the data model.

## Who it's for

The primary user is the **mid-career engineer / PM / designer running an active search**: 20–100+ applications per cycle, 4–12 weeks of effort, deep enough in their craft to spot a bad JD but tired enough to want help with the grind.

Secondary users:
- **New grads** — heavy on the Interview Grill agent, light on auto-apply.
- **Career switchers** — heavy on resume tailoring (translating prior experience), match-explainer + skill-gap learning paths.
- **Stealth job seekers** — currently employed, must avoid pinging their current employer's domain or having alerts leak into work email. Stealth mode (`UserProfile.stealth_domains`) is a first-class feature for this user.

## Design principles

These are the invariants that should survive every refactor.

### 1. The candidate stays in control

Every submit goes through a human approval gate by default. The `HITL_HARD_GATE` mechanism in `backend/agent/tools/registry.py` is non-negotiable — *no* tool that takes irreversible action runs without a token issued by an authenticated user action. The default tier on a new application is `assist`, not `autonomous`.

### 2. Truthful tailoring

A tailored resume reorders, rephrases, and emphasises — it never fabricates. Prompts in `backend/tailoring/generators.py` carry "preserving truthfulness" as a hard instruction. The diff between master and tailored is stored on `TailoredResume.diff_from_master` so the candidate can audit what changed.

### 3. Phase-gated capability

The agent has three phases of tools: Phase 1 (read, score, suggest), Phase 2 (autofill, scrape, draft), Phase 3 (submit, outreach, autonomous browse). Free-tier users only see Phase 1. The cap is enforced inside the orchestrator, not just at the API surface — see `AgentState.phase_cap`.

### 4. No vendor lock-in for AI

Every LLM-using function takes an `llm=` callable. NVIDIA NIM is the guest pool, OpenRouter / OpenAI / Anthropic are BYO-key for paid users, and CLI delegates (Claude Code, Codex, Gemini CLI — Faultline-style) are the fallback when no API is available. Swapping the provider should be a one-line change at the call site.

### 5. Embedder-free retrieval

We do not run vector databases. Job↔resume matching uses lexical BM25 + skill overlap with optional LLM rerank. "RAG" for company research / interview-question banks uses JSONL on disk + ripgrep. Decision and rationale: [drop-faiss-and-add-google-auth.md](./drop-faiss-and-add-google-auth.md). This keeps the deployment story simple — one Postgres, one Redis, no embedding service, no FAISS index sync job.

### 6. Copy don't regenerate

Two reference projects on disk — **AIAAS** and **Faultline** — already solve auth, the LangGraph chat loop, encrypted credentials, parallel tool batching, and dynamic portal AuthFlows. Always check those first; copy the file and edit in place rather than asking the LLM to regenerate equivalent code.

### 7. Tests alongside code

Every Django app ships unit tests in the same commit as the feature. Tests never reach the network. Adapters use `httpx.MockTransport`. LLM-using code uses injectable `llm=` stubs. The Google OAuth view exposes a `provider_factory` for the same reason.

### 8. Stealth by default for sensitive flows

Currently-employed users add their employer domain to `stealth_domains`; postings from that domain are filtered out of every list endpoint *at the query level*. Email digests, web-push, the dashboard, and the agent's job-search tool all honour the same filter. Easy to break, easy to test, hugely trust-building when it works.

## The Interview Grill Chat Agent (north star feature)

The single most differentiated feature in the product. Existing interview-prep tools give you a generic list of "behavioural questions." The Grill agent:

1. **Researches** the target company, role, and stage (recruiter / phone / system design / behavioural / role-specific) from Glassdoor/Levels/Blind + LLM-driven web search.
2. **Generates a tailored question bank** specific to that company's known interview patterns.
3. **Runs a live grilling session**: asks one question, evaluates the answer on a STAR-style rubric (structure / specificity / outcome), drills deeper on weak spots, then moves on.
4. **Summarises** strengths, gaps, and a 5-item study plan.

Phase 2 ships text mode. Phase 3 adds a voice mode (Deepgram or NVIDIA Riva) for realistic pacing. The voice agent reuses the same `interview/grilling.py` core — only the I/O layer changes.

## Phased roadmap (high level)

- **Phase 1 (MVP)** — Discovery (Adzuna + Greenhouse), profile chat onboarding, resume parse + match scoring, basic tailoring, email + push notifications, Google OAuth, NVIDIA guest pool.
- **Phase 2** — More sources (Jooble, JSearch, Lever, Playwright scrapers, email forwards), browser extension for autofill, cover letters, Kanban tracker, **Interview Grill Chat Agent (text)**, JD red-flag detector, resume A/B analytics.
- **Phase 3** — Autonomous apply behind HITL gates, portal AuthFlows for Workday/Greenhouse/Lever (Faultline-style), LinkedIn integration, salary intelligence, networking-outreach agent, **voice mode** for Interview Grill, salary negotiation rehearsal.

## What we are not building

- A full LinkedIn scraper army. We respect ToS; LinkedIn integration is best-effort RSS + user-session-cookie based.
- A recruiter-side product. The platform is candidate-owned. Recruiters who want to use the data should pay candidates directly.
- A general-purpose AI assistant. The agent's tool registry is intentionally narrow and phase-gated.
- A vector database. See principle 5.

## How we'll know it's working

Per-user health metrics (Phase 2):
- **Time-to-tailored-resume**: < 30 seconds from clicking a JD.
- **Applications/week vs interviews/week**: response-rate per resume variant.
- **Time-to-first-interview**: from first application to first scheduled phone screen.
- **Approval drop-off rate**: how often the user rejects an autonomous-apply proposal — too high means the agent is being annoying, too low means the user isn't reading.
- **Grill→interview lift**: did completing N Grill sessions correlate with better interview outcomes?

The product succeeds when an active job seeker can go from "I want to switch" to "I have an offer" with the platform doing the grind and the human doing only the judgement calls.
