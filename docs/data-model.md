# Data Model

Authoritative entity map. When in doubt, read the model file; this doc summarises relationships and the non-obvious constraints.

## Entity overview

```
                          User  (django.contrib.auth)
                            │
        ┌───────────────────┼────────────────────────┬───────────────┐
        │                   │                        │               │
        ▼                   ▼                        ▼               ▼
   UserProfile         StructuredProfile        Resume * ──┐     Credential *
   (tier, stealth)     │                                   │
                       ├── Experience *                    └─ ResumeVersion *
                       ├── Education *
                       ├── Skill *
                       ├── Project *
                       └── Preference (1:1)

   User ──┬─ Subscription *  ── Alert *  ── JobPosting
          │                                       ▲
          ├─ Application * ────────────────────── │
          │      │                                │
          │      ├─ TailoredResume (1:1)          │
          │      ├─ CoverLetter   (1:1)           │
          │      ├─ ApplicationEvent *            │
          │      └─ AutoApplySession (1:1)        │
          │                                       │
          ├─ MatchScore * ── JobPosting ──────────┘
          │
          ├─ AgentSession * ── AgentMessage *
          ├─ InterviewSession * ── InterviewQuestion * ── InterviewTurn *
          │                       └─ InterviewReport (1:1)
          ├─ PortalSession * ── AuthFlow
          ├─ CreditLedger *
          └─ WebPushDevice *

  JobPosting ── Company
            └── Source

  AnonymousVisitor → GuestSession (tokens_used)
```

## Per-app detail

### accounts ([models](../backend/accounts/models.py))

| Model | Key fields | Notes |
|---|---|---|
| `UserProfile` | `user (1:1)`, `tier`, `credits_remaining`, `stealth_domains [list]`, `nvidia_guest_key_issued` | Auto-created via `post_save` signal in [accounts/signals.py](../backend/accounts/signals.py). `is_paid` property = tier in {`pro`, `enterprise`}. |
| `GuestSession` | `session_key (unique)`, `tokens_used`, `last_seen_at` | Anonymous NVIDIA pool tracker. |

Tiers: `guest`, `free` (default), `pro`, `enterprise`. Phase-cap (see [agent.md](./agent.md)) derives from tier.

### profiles ([models](../backend/profiles/models.py))

`StructuredProfile (1:1 User)` is the canonical "who is this candidate" record, populated by the onboarding chat. Children:
- `Experience * (FK)` — title, company, dates, bullets (`JSONField list`).
- `Education *`, `Skill *` (unique per profile by name), `Project *` (with `tech_stack JSONField list`).
- `Preference (1:1)` — target titles, locations, salary_min, remote bool, exclude_companies, **`stealth_mode bool`** (separate from `UserProfile.stealth_domains`; this one just toggles the feature, the domains live on UserProfile).

### resumes ([models](../backend/resumes/models.py))

| Model | Key fields | Constraints |
|---|---|---|
| `Resume` | `user`, `file`, `parsed_json`, `is_master`, `parse_status` | **At most one master per user** (partial unique index). |
| `ResumeVersion` | `resume (FK)`, `parsed_json snapshot`, `note` | Immutable; created when a TailoredResume needs to pin against a known master state. |

`parse_status ∈ {pending, done, failed}`. Parsing pipeline lives in [resumes/parsing.py](../backend/resumes/parsing.py).

### jobs ([models](../backend/jobs/models.py))

| Model | Key fields | Constraints |
|---|---|---|
| `Company` | `name`, `domain`, `ats_type`, `careers_url` | Unique on `(name, domain)`. `ats_type ∈ {greenhouse, lever, workday, smartrecruiters, other}`. |
| `Source` | `name (unique)`, `kind`, `config (JSONField)`, `enabled` | `kind ∈ {aggregator, ats_public, scraper, email_forward, web_search, cli_delegate, linkedin}`. |
| `JobPosting` | `source`, `external_id`, `company`, `title`, `description`, `location`, `remote`, `salary_*`, `apply_url`, `posted_at`, `raw (JSONField)` | **Unique on `(source, external_id)`** — this is the idempotency key for re-running ingestion. |

`JobListView` honours `request.user.cn_profile.stealth_domains` — see [jobs/views.py](../backend/jobs/views.py). Any new list/search endpoint that returns jobs must apply the same filter.

### ingestion ([models](../backend/ingestion/models.py))

`IngestionRun (FK Source)` records each adapter execution. Statuses: `running`, `success`, `failed`. `stats JSONField` carries `{created, updated, skipped}` produced by [services.upsert_postings](../backend/ingestion/services.py).

### matching ([models](../backend/matching/models.py))

`MatchScore` is unique on `(user, job)`, indexed on `(user, -score)` so "top matches today" is a fast lookup. Contains `score (float)`, `breakdown (JSONField with semantic/skill_overlap)`, `gaps (JSONField list)`, `model_version`.

### notifications ([models](../backend/notifications/models.py))

| Model | Notes |
|---|---|
| `Subscription` | `filter_json` is the DSL described in [notifications/filters.py](../backend/notifications/filters.py); `channels` is `[email, webpush, in_app]`. |
| `WebPushDevice` | VAPID endpoint/auth/p256dh per browser registration. |
| `Alert` | Unique on `(user, job, channel)` so we don't double-send. |

### applications ([models](../backend/applications/models.py))

The Kanban core.

| Model | Key fields | Notes |
|---|---|---|
| `Application` | `user`, `job`, `status`, `tier_used`, `auto_apply_session (1:1)`, `notes` | Unique on `(user, job)`. Status enum: saved → tailored → ready → applied → phone → onsite → offer/rejected/withdrawn. |
| `ApplicationEvent` | `application`, `type`, `payload (JSONField)` | Audit log per application. |
| `AutoApplySession` | `user`, `state`, `approval_token`, `expires_at` | Holds the HITL hard-gate token. State enum: queued → running → waiting_approval → done/failed. `issue_approval_token()` generates a `secrets.token_urlsafe(32)` and flips state. |

The orchestrator-level HITL check + the in-tool re-check both compare against `AutoApplySession.approval_token` — see [agent.md](./agent.md).

### networking ([models](../backend/networking/models.py))

Referral graph + warm-intro outreach. Outreach is draft-only and gated by the same approval-token pattern as auto-apply (see vision principle 9).

| Model | Key fields | Notes |
|---|---|---|
| `Contact` | `user`, `company`, `name`, `title`, `source`, `relationship_strength`, `tags` | Indexed on `(user, name)` and `(user, email)`. `source` enum: manual/csv/google/profile_url/public_page. |
| `ContactEmployment` | `contact`, `company`, `started_at`, `ended_at`, `is_current` | A contact's employment over time; `overlaps()` powers colleague inference. Unique on `(contact, company, title, started_at)`. |
| `ContactRelationship` | `from_contact`, `to_contact`, `kind`, `strength`, `inferred` | Directed edge; bidirectional kinds stored as two rows. |
| `CompanyRelationship` | `from_company`, `to_company`, `kind` | Global (not per-user) company graph: acquired/parent/subsidiary/competitor/etc. |
| `ReferralOpportunity` | `user`, `job`, `contact`, `score`, `status` | Unique on `(user, job, contact)`; ranked by score. |
| `OutreachMessage` | `user`, `contact`, `job`, `channel`, `draft_body`, `approved_body`, `payload_hash`, `status` | `approve()` hashes the approved body — drafts are never auto-sent. |
| `ActionQueueItem` | `user`, `action_type`, `priority`, `due_at`, `status` | Surfaced as the user's next-actions queue. |
| `UserConsentEvent` | `user`, `action_type`, `payload_hash`, `approval_token`, `expires_at`, `used_at` | Mirrors the `AutoApplySession` token pattern for outreach/credentials consent; `is_valid` checks unused + unexpired. |

### tailoring ([models](../backend/tailoring/models.py))

`TailoredResume (1:1 Application)` stores the generated content + `diff_from_master (JSONField)` so the candidate can audit what changed.
`CoverLetter (1:1 Application)` stores the generated text + which model produced it.

### agent ([models](../backend/agent/models.py))

| Model | Notes |
|---|---|
| `AgentSession` | `user`, `kind ∈ {onboarding, general, tailoring, autonomous_apply}`, `status`, `state (JSONField)`, `pending_approval (JSONField)`. |
| `AgentMessage` | `session`, `role ∈ {user, assistant, tool, system}`, `content`, `tool_calls (JSONField list)`, `tool_name`. Ordered by `created_at`. |

### interview ([models](../backend/interview/models.py))

| Model | Notes |
|---|---|
| `InterviewSession` | `user`, `company`, `job`, `role`, `stage ∈ {recruiter, tech_phone, system_design, behavioral, role_specific}`, `difficulty`, `research (JSONField)`, `status`. |
| `InterviewQuestion` | `session`, `prompt`, `category`, `difficulty`, `expected_signals (JSONField list)`, `order`. |
| `InterviewTurn` | `question (FK)`, `user_answer`, `evaluation (JSONField)`, `score (float)`, `feedback`, `drilldown_of (FK self)`. Self-FK supports follow-up questions. |
| `InterviewReport` | `session (1:1)`, `strengths (list)`, `gaps (list)`, `study_plan (list of {topic, action})`, `overall_score`, `summary`. |

### credentials ([models](../backend/credentials/models.py))

`Credential` is unique on `(user, provider, label)`. The plaintext lives **only** in the AES-GCM ciphertext stored in `ciphertext`. Helpers `set_secret(plaintext)` and `reveal()` go through [credentials/crypto.py](../backend/credentials/crypto.py). Serializers accept `secret` as write-only and never expose it on read.

### vault ([models](../backend/vault/models.py))

Phase 3.

| Model | Notes |
|---|---|
| `AuthFlow` | `portal (unique)`, `steps (JSONField)` — ordered list of step dicts: `navigate`, `fill`, `click`, `wait_for`, `mfa_prompt`. Faultline-style. |
| `PortalSession` | `user`, `auth_flow`, `cookies_ciphertext`, `expires_at`. Unique on `(user, auth_flow)`. |

### billing ([models](../backend/billing/models.py))

`CreditLedger` is append-only: `delta` (signed int), `reason ∈ {signup_bonus, tailor_resume, cover_letter, autonomous_apply, mock_interview, top_up, stripe_purchase, refund}`. Balance = sum of deltas.
`StripeSubscription` is 1:1 with User.

## Indexes worth knowing

- `JobPosting`: ordered by `-posted_at, -created_at`; FK indexes on `source`, `company`; multi-column unique on `(source, external_id)`.
- `MatchScore`: composite index `(user, -score)` for the "top N for this user" query.
- `AgentMessage`: ordered by `created_at` per session — Django adds the implicit FK index, plus the natural sort order.
- `Alert`: unique `(user, job, channel)` doubles as the dedup index.

## JSONField conventions

We use `JSONField` liberally. Conventions:

- **Lists of primitives** for tag-like data (`skills`, `tech_stack`, `gaps`, `target_titles`).
- **Lists of dicts** for structured but schema-flexible data (`bullets`, `study_plan`, `tool_calls`, `expected_signals`).
- **Single dict** for adapter raw payloads (`JobPosting.raw`), audit event details (`ApplicationEvent.payload`), or LLM evaluation breakdowns (`InterviewTurn.evaluation`, `MatchScore.breakdown`).

Never store secrets or per-user PII in a JSONField that ends up serialised to clients — DRF serializers control egress, but keep the model layer paranoid too.

## Migrations

Phase-1 ships zero hand-written migrations. The first `python manage.py makemigrations` after `pip install` will generate them all. Run [development.md](./development.md) for the bootstrap sequence.

Future schema changes:
- **Embedding column removal** (when we ship BM25; see [drop-faiss-and-add-google-auth.md](./drop-faiss-and-add-google-auth.md)) — not yet done.
- **Application approval-token expiry** (Phase 2) — add `used_at` and check it in the tool body.
