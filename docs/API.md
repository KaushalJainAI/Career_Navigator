# API Reference — Code Review Map

A per-endpoint index of the whole HTTP surface, built as a **starting point for
reviewing this codebase**. For every endpoint it records:

0. **URL** + method
1. **What** it does (one line)
2. **Access** — permission (global default is `IsAuthenticated`; only exceptions noted)
3. **Django app** — the app the route lives in
4. **Complexity** — rough cost of one call (see legend)
5. **Tested** — is there a test (see per-app coverage note)
6. **Serializer** — DRF serializer where one is used (`—` = raw / hand-built)
7. **DB tables** — models the request reads or writes
8. **Atomic** — does the write run inside `transaction.atomic()`?
9. **Notes** — the one thing worth knowing before reading the code

> Hand-derived from `config/urls.py`, each app's `urls.py` / `views.py` / `models.py`,
> and each app's `tests/` on 2026-07-24. Everything is mounted under **`/api/v1/`**.
> `urls.py` remains the source of truth — **add a row whenever you add a route.**

## Legend

**Complexity**: `O(1)` single-row · `O(n)` linear · `Aggregate` DB GROUP BY ·
`External` blocking 3rd-party/LLM/scrape call · `Heavy` in-process AI/graph pipeline ·
`Stream` SSE.

**Access**: `Auth` = `IsAuthenticated` (global default) · `Public` = `AllowAny`.
Auth is JWT (`rest_framework_simplejwt`) **or** `accounts.authentication.APITokenAuthentication`.

**Tested**: `✅` app has tests covering this area · `~` thin/indirect · `—` none.

**Atomic**: ⚠ No `views.py` in this backend wraps writes in `transaction.atomic()`.
Multi-step consistency is handled in service layers (`*/services.py`), not the view.
Column omitted per-row; treat view-layer writes as non-atomic unless a service is named.

## Global config

- **Default permission**: `IsAuthenticated`. **Pagination**: PageNumber, `PAGE_SIZE=20`.
- **Throttles**: `anon 100/hr`, `user 2000/hr`, scoped `guest_chat 30/hr`,
  `tailoring 60/hr`, `autonomous_apply 20/hr`.
- **Health**: `GET /api/health/` (public). **Docs**: `/api/schema/`, `/api/docs/`.

## Test coverage by app (≈ #tests)

`accounts` ✅ (views 12, oauth 10, api_tokens 7, password_otp 7) · `ingestion` ✅ (adapters 19, services 6) ·
`portals` ✅ (added_scrapers 12, api 8, scrapers 7, services 5, sessions 4) · `networking` ✅ (relationship 9, graph 8) ·
`jobs` ✅ (ghost 9, refresh 4, manual 4, breakdown 4) · `billing` ✅ (api 9) · `notifications` ✅ (webpush 8, filters 5) ·
`profiles` ✅ (views 7) · `extension_api` ✅ (views 7) · `matching` ✅ (scorer 6) · `interview` ✅ (grilling 6) ·
`applications` ✅ (planner 6, api 6, analytics 5) · `tailoring` ✅ (api 5) · `agent` ~ (graph 4) ·
`ai` ✅ (providers 11 — library, not HTTP) · `credentials`/`vault` — thin.

---

## 1. Accounts / auth — app: `accounts` — [backend/accounts/views.py](../backend/accounts/views.py)

Models: `UserProfile`, `GuestSession`, `PasswordResetOTP`, `APIToken`.

| URL (`/api/v1/auth/…`) | Method | What | Access | Complexity | Tested | Serializer | DB tables | Notes |
|-----|--------|------|--------|-----------|--------|-----------|-----------|-------|
| `register/` | POST | Register | Public | O(1) | ✅ | `RegisterSerializer` | User, UserProfile | |
| `login/` | POST | JWT obtain | Public | O(1) | ✅ | SimpleJWT | User | |
| `refresh/` | POST | Refresh JWT | Public | O(1) | ~ | SimpleJWT | — | |
| `me/` | GET/PATCH | Current user | Auth | O(1) | ✅ | `MeSerializer` | User, UserProfile | |
| `change-password/` | POST | Change password | Auth | O(1) | ✅ | — | User | |
| `google/` | POST | Google login | Public | External | ✅ | — | User, UserProfile | oauth-tested |
| `guest-key/` | POST | Issue anonymous guest key | Public | O(1) | ~ | — | GuestSession | Powers guest chat throttle |
| `password-reset/` | POST | Request reset OTP | Public | O(1)+email | ✅ | — | User, PasswordResetOTP | |
| `password-reset/verify/` | POST | Verify OTP | Public | O(1) | ✅ | — | PasswordResetOTP | |
| `password-reset/confirm/` | POST | Set new password | Public | O(1) | ✅ | — | User, PasswordResetOTP | |
| `api-tokens/` | GET/POST | List/create API tokens | Auth | O(1) | ✅ | `APITokenSerializer` | APIToken | Token shown once |
| `api-tokens/{pk}/revoke/` | POST | Revoke token | Auth (owner) | O(1) | ✅ | — | APIToken | |

---

## 2. Profile — app: `profiles` — [backend/profiles/views.py](../backend/profiles/views.py)

Models: `StructuredProfile`, `Experience`, `Education`, `Skill`, `Project`, `Certification`, `Language`, `Preference`.

| URL (`/api/v1/profile/`) | Method | What | Access | Complexity | Tested | Serializer | DB tables | Notes |
|-----|--------|------|--------|-----------|--------|-----------|-----------|-------|
| `` | GET/PUT/PATCH | Read/update the structured profile (nested) | Auth (owner) | O(n) | ✅ | `StructuredProfileSerializer` | StructuredProfile + all child tables | Nested write of experiences/education/skills/etc |

---

## 3. Resumes — app: `resumes` — [backend/resumes/views.py](../backend/resumes/views.py)

Models: `Resume`, `ResumeVersion`.

| URL (`/api/v1/resumes/`) | Method | What | Access | Complexity | Tested | Serializer | DB tables | Notes |
|-----|--------|------|--------|-----------|--------|-----------|-----------|-------|
| `` | GET/POST | List/create resume (upload → parse) | Auth (owner) | Heavy | ~ | `ResumeSerializer` | Resume, ResumeVersion | Upload triggers parse pipeline |
| `{pk}/` | GET/PUT/PATCH/DELETE | Resume CRUD | Auth (owner) | O(1) | ~ | `ResumeSerializer` | Resume, ResumeVersion | |

---

## 4. Jobs — app: `jobs` — [backend/jobs/views.py](../backend/jobs/views.py)

Models: `Company`, `Source`, `JobPosting`.

| URL (`/api/v1/jobs/`) | Method | What | Access | Complexity | Tested | Serializer | DB tables | Notes |
|-----|--------|------|--------|-----------|--------|-----------|-----------|-------|
| `` | GET | List jobs (filters) | Auth | O(n) | ✅ | `JobPostingSerializer` | JobPosting, Company | Also manual-create tested |
| `refresh/` | POST | Trigger ingestion refresh | Auth | External | ✅ | — | JobPosting, Source, IngestionRun | Response carries `sources` (`success`/`partial`/`failed`) + `errors` per source; a broken API key no longer reads as "no new jobs" |
| `{pk}/` | GET | Job detail | Auth | External (first view) | ✅ | `JobPostingSerializer` | JobPosting, Company | Ghost-job detection tested. First view fetches the full JD from `apply_url` and caches it on the row (`jobs/description.py`); one outbound request per posting, retried after 7 days if it failed. Disable with `FETCH_FULL_DESCRIPTIONS=False`. Serializer exposes `full_description` + `has_full_description` |
| `{pk}/breakdown/` | GET | AI breakdown of a posting | Auth | External | ✅ | — | JobPosting | LLM |

---

## 5. Ingestion — app: `ingestion` — [backend/ingestion/views.py](../backend/ingestion/views.py)

Model: `IngestionRun`.

| URL (`/api/v1/ingestion/`) | Method | What | Access | Complexity | Tested | Serializer | DB tables | Notes |
|-----|--------|------|--------|-----------|--------|-----------|-----------|-------|
| `run/{source_name}/` | POST | Run one job source adapter | Auth | External | ✅ | — | IngestionRun, JobPosting, Company | Adapters heavily unit-tested (19) |

---

## 6. Matching — app: `matching` — [backend/matching/views.py](../backend/matching/views.py)

Model: `MatchScore`.

| URL (`/api/v1/matching/`) | Method | What | Access | Complexity | Tested | Serializer | DB tables | Notes |
|-----|--------|------|--------|-----------|--------|-----------|-----------|-------|
| `jobs/{job_id}/` | GET/POST | Score a job against the user's profile | Auth | Heavy | ✅ | — | MatchScore, JobPosting, StructuredProfile | Scorer unit-tested |

---

## 7. Notifications — app: `notifications` — [backend/notifications/views.py](../backend/notifications/views.py)

Models: `Subscription`, `WebPushDevice`, `Alert`.

| URL (`/api/v1/notifications/`) | Method | What | Access | Complexity | Tested | Serializer | DB tables | Notes |
|-----|--------|------|--------|-----------|--------|-----------|-----------|-------|
| `subscriptions/` | GET/POST | Alert subscriptions | Auth (owner) | O(1) | ✅ | `SubscriptionSerializer` | Subscription | Filter tests |
| `subscriptions/{pk}/` | GET/PUT/DELETE | Subscription detail | Auth (owner) | O(1) | ✅ | `SubscriptionSerializer` | Subscription | |
| `alerts/` | GET | List alerts | Auth (owner) | O(n) | ✅ | `AlertSerializer` | Alert | |
| `alerts/{pk}/read/` | POST | Mark alert read | Auth (owner) | O(1) | ~ | — | Alert | |
| `activity/` | GET | Activity feed | Auth | O(n) | ~ | — | Alert, ApplicationEvent | |
| `vapid-public-key/` | GET | Web-push VAPID key | Auth | O(1) | ✅ | — | — | |
| `push/register/` | POST | Register web-push device | Auth | O(1) | ✅ | — | WebPushDevice | webpush-tested |
| `push/unregister/` | POST | Unregister device | Auth | O(1) | ✅ | — | WebPushDevice | |

---

## 8. Applications — app: `applications` — [backend/applications/views.py](../backend/applications/views.py)

Models: `AutoApplySession`, `Application`, `ApplicationEvent`, `Todo`, `Goal`.

| URL (`/api/v1/applications/`) | Method | What | Access | Complexity | Tested | Serializer | DB tables | Notes |
|-----|--------|------|--------|-----------|--------|-----------|-----------|-------|
| `` | GET/POST | List/create applications | Auth (owner) | O(n) | ✅ | `ApplicationSerializer` | Application, ApplicationEvent | |
| `stats/` | GET | Dashboard stats | Auth | Aggregate | ✅ | — | Application | |
| `analytics/` | GET | Response analytics | Auth | Aggregate | ✅ | — | Application, ApplicationEvent | analytics-tested |
| `prepare/` | POST | Prepare an application (AI) | Auth | Heavy | ~ | — | Application, StructuredProfile, JobPosting | planner-tested |
| `todos/` | GET/POST | Todo list | Auth (owner) | O(1) | ~ | `TodoSerializer` | Todo | |
| `todos/{pk}/` | GET/PUT/DELETE | Todo detail | Auth (owner) | O(1) | ~ | `TodoSerializer` | Todo | |
| `goals/` | GET/POST | Goals | Auth (owner) | O(1) | ~ | `GoalSerializer` | Goal | |
| `goals/{pk}/` | GET/PUT/DELETE | Goal detail | Auth (owner) | O(1) | ~ | `GoalSerializer` | Goal | |
| `{pk}/` | GET/PUT/DELETE | Application detail | Auth (owner) | O(1) | ✅ | `ApplicationSerializer` | Application | |
| `{pk}/approve/` | POST | Approve an auto-apply run | Auth (owner) | External | ~ | — | AutoApplySession, Application | `autonomous_apply` throttle |

---

## 9. Networking — app: `networking` — [backend/networking/views.py](../backend/networking/views.py)

Models: `Contact`, `ReferralOpportunity`, `OutreachMessage`, `ActionQueueItem`,
`ContactEmployment`, `ContactRelationship`, `CompanyRelationship`, `UserConsentEvent`.
(Company hub reuses `jobs.Company`.)

| URL (`/api/v1/networking/`) | Method | What | Access | Complexity | Tested | Serializer | DB tables | Notes |
|-----|--------|------|--------|-----------|--------|-----------|-----------|-------|
| `contacts/` | GET/POST | Contacts | Auth (owner) | O(n) | ✅ | `ContactSerializer` | Contact | |
| `contacts/{pk}/` | GET/PUT/DELETE | Contact detail | Auth (owner) | O(1) | ✅ | `ContactSerializer` | Contact | |
| `contacts/{pk}/employments/` | GET/POST | Contact employments | Auth | O(n) | ✅ | `ContactEmploymentSerializer` | ContactEmployment | relationship-api tested |
| `contacts/{pk}/relationships/` | GET/POST | Contact relationships | Auth | O(n) | ✅ | `ContactRelationshipSerializer` | ContactRelationship | |
| `employments/{pk}/` | GET/PUT/DELETE | Employment detail | Auth | O(1) | ✅ | `ContactEmploymentSerializer` | ContactEmployment | |
| `relationships/{pk}/` | GET/PUT/DELETE | Relationship detail | Auth | O(1) | ✅ | `ContactRelationshipSerializer` | ContactRelationship | |
| `companies/` | GET | Company hubs | Auth | O(n) | ~ | — | Company | |
| `companies/{pk}/` | GET | Company hub detail | Auth | O(1) | ~ | — | Company, CompanyRelationship | |
| `companies/{pk}/relationships/` | GET/POST | Company relationships | Auth | O(n) | ✅ | `CompanyRelationshipSerializer` | CompanyRelationship | |
| `graph/` | GET | Network graph neighborhood | Auth | Heavy | ✅ | — | Contact, *Relationship | graph-tested |
| `warm-intros/{company_id}/` | GET | Warm-intro paths to a company | Auth | Heavy | ✅ | — | Contact, ContactEmployment | |
| `jobs/{job_id}/referrals/` | GET | Referral suggestions for a job | Auth | Heavy | ~ | — | ReferralOpportunity, Contact | |
| `referrals/` | GET | Referral opportunities | Auth | O(n) | ~ | `ReferralOpportunitySerializer` | ReferralOpportunity | |
| `outreach/` | GET/POST | Outreach messages | Auth (owner) | O(n) | ~ | `OutreachMessageSerializer` | OutreachMessage | |
| `outreach/{pk}/` | GET/PUT/DELETE | Outreach detail | Auth (owner) | O(1) | ~ | `OutreachMessageSerializer` | OutreachMessage | |
| `outreach/{pk}/approve/` | POST | Approve/send outreach | Auth (owner) | External | ~ | — | OutreachMessage, UserConsentEvent | |
| `queue/` | GET | Action queue | Auth | O(n) | ~ | `ActionQueueItemSerializer` | ActionQueueItem | |

---

## 10. Tailoring — app: `tailoring` — [backend/tailoring/views.py](../backend/tailoring/views.py)

Models: `TailoredResume`, `CoverLetter`.

| URL (`/api/v1/tailoring/`) | Method | What | Access | Complexity | Tested | Serializer | DB tables | Notes |
|-----|--------|------|--------|-----------|--------|-----------|-----------|-------|
| `resume/` | POST | Tailor a resume to a job (AI) | Auth (60/hr) | Heavy | ✅ | — | TailoredResume, Resume, JobPosting | `tailoring` throttle |
| `resume/export/` | POST | Export tailored resume (PDF/docx) | Auth | Heavy | ~ | — | TailoredResume | |
| `cover-letter/` | POST | Draft a cover letter (AI) | Auth | External | ✅ | — | CoverLetter, JobPosting | |

---

## 11. Agent (career copilot) — app: `agent` — [backend/agent/views.py](../backend/agent/views.py)

Models: `AgentSession`, `AgentMessage`.

| URL (`/api/v1/agent/`) | Method | What | Access | Complexity | Tested | Serializer | DB tables | Notes |
|-----|--------|------|--------|-----------|--------|-----------|-----------|-------|
| `sessions/` | GET/POST | Agent sessions | Auth (owner) | O(1) | ~ | `AgentSessionSerializer` | AgentSession | |
| `sessions/{session_id}/chat/` | POST | Chat turn (LangGraph agent) | Auth (owner) | Heavy/External | ~ | — | AgentSession, AgentMessage | graph-tested |

---

## 12. Interview prep — app: `interview` — [backend/interview/views.py](../backend/interview/views.py)

Models: `InterviewSession`, `InterviewQuestion`, `InterviewTurn`, `InterviewReport`.

| URL (`/api/v1/interview/`) | Method | What | Access | Complexity | Tested | Serializer | DB tables | Notes |
|-----|--------|------|--------|-----------|--------|-----------|-----------|-------|
| `sessions/` | GET/POST | Interview sessions | Auth (owner) | O(1) | ~ | `InterviewSessionSerializer` | InterviewSession, InterviewQuestion | |
| `sessions/{pk}/` | GET/DELETE | Session detail | Auth (owner) | O(1) | ~ | `InterviewSessionSerializer` | InterviewSession, InterviewTurn | |
| `sessions/{session_id}/answer/` | POST | Submit an answer (AI grades) | Auth (owner) | External | ✅ | — | InterviewTurn | grilling-tested |
| `sessions/{session_id}/report/` | GET | Final report | Auth (owner) | Heavy | ~ | — | InterviewReport | |

---

## 13. Credentials — app: `credentials` — [backend/credentials/views.py](../backend/credentials/views.py)

Model: `Credential` (encrypted). IDOR-sensitive — verify per-user scoping.

| URL (`/api/v1/credentials/`) | Method | What | Access | Complexity | Tested | Serializer | DB tables | Notes |
|-----|--------|------|--------|-----------|--------|-----------|-----------|-------|
| `` | GET/POST | List/create credentials | Auth (owner) | O(1) | ~ | `CredentialSerializer` | Credential | Secrets encrypted at rest |
| `{pk}/` | GET/PUT/DELETE | Credential CRUD | Auth (owner) | O(1) | ~ | `CredentialSerializer` | Credential | |

---

## 14. Browser extension API — app: `extension_api` — [backend/extension_api/views.py](../backend/extension_api/views.py)

Consumed by the Chrome extension (API-token auth typical).

| URL (`/api/v1/ext/`) | Method | What | Access | Complexity | Tested | Serializer | DB tables | Notes |
|-----|--------|------|--------|-----------|--------|-----------|-----------|-------|
| `page-context/` | POST | Push current page context | Auth | O(1) | ✅ | — | (transient) | views-tested |
| `autofill/` | POST | Get autofill values for a form | Auth | Heavy | ✅ | — | StructuredProfile | |
| `submit-event/` | POST | Record an application-submit event | Auth | O(1) | ✅ | — | Application, ApplicationEvent | |
| `profile-context/` | GET | Profile context for the extension | Auth | O(1) | ✅ | — | StructuredProfile | |

---

## 15. Vault — app: `vault` — [backend/vault/urls.py](../backend/vault/urls.py)

Models: `AuthFlow`, `PortalSession`. **`urls.py` is currently empty — no routes mounted.**
The models back the portals-session flow; flag as dormant/internal when reviewing.

---

## 16. Portals (job-portal automation) — app: `portals` — [backend/portals/views.py](../backend/portals/views.py)

Models: `Portal`, `PortalAccount`, `PortalScrapeRun`.

| URL (`/api/v1/portals/`) | Method | What | Access | Complexity | Tested | Serializer | DB tables | Notes |
|-----|--------|------|--------|-----------|--------|-----------|-----------|-------|
| `` | GET | List supported portals | Auth | O(n) | ✅ | `PortalSerializer` | Portal | |
| `runs/` | GET | Scrape-run history | Auth (owner) | O(n) | ✅ | `PortalScrapeRunSerializer` | PortalScrapeRun | |
| `{name}/session/` | GET/POST | Establish/read a portal session | Auth | External | ✅ | — | PortalAccount, PortalSession | session-tested |
| `{name}/scrape/` | POST | Run a portal scrape | Auth | External | ✅ | — | PortalScrapeRun, JobPosting | scrapers heavily tested |

---

## 17. Billing — app: `billing` — [backend/billing/views.py](../backend/billing/views.py)

Models: `CreditLedger`, `StripeSubscription`.

| URL (`/api/v1/billing/`) | Method | What | Access | Complexity | Tested | Serializer | DB tables | Notes |
|-----|--------|------|--------|-----------|--------|-----------|-----------|-------|
| `summary/` | GET | Credit + subscription summary | Auth | Aggregate | ✅ | — | CreditLedger, StripeSubscription | api-tested |
| `pricing/` | GET | Pricing table | Auth | O(1) | ✅ | — | — | |
| `ledger/` | GET | Credit ledger entries | Auth (owner) | O(n) | ✅ | `CreditLedgerSerializer` | CreditLedger | |
| `top-up/` | POST | Manual credit top-up | Auth | External | ✅ | — | CreditLedger | Stripe |

---

## Cross-cutting notes for reviewers

- **No view-level transactions.** Grep confirms zero `transaction.atomic` in `views.py`.
  Consistency for multi-write flows (ingestion, scraping, tailoring, matching) lives in
  `*/services.py` — review those.
- **All public endpoints are in `accounts`** (register/login/refresh/google/guest-key +
  3 password-reset routes). Everything else requires auth. `guest-key` mints the token
  that gates guest-chat throttling — a good first review target.
- **`vault` app has no routes** (empty `urls.py`); `ai` app is a provider library, not
  HTTP-mounted. Neither appears under `/api/v1/`.
- **External-heavy surfaces** (scraping, autonomous-apply, tailoring, agent chat) carry
  dedicated throttles (`tailoring 60/hr`, `autonomous_apply 20/hr`, `guest_chat 30/hr`) —
  verify they're applied on the right views.
