# Job Search Skills & Workflows Plan

This plan turns Career Navigator from a job tracker into an active job-search operator that can discover roles, suggest contacts, draft outreach, prepare applications, and apply or contact people only with the user's explicit approval.

## Product principle

The platform may research, rank, draft, schedule, and prepare actions autonomously. It must not submit an application, send a message, email a contact, use a credentialed portal session, or represent the user externally without a clear human approval gate.

## Built-in skills

### 1. Job Discovery Skill

Finds relevant jobs across aggregators, company boards, saved target companies, forwarded job-alert emails, and user-provided links.

Core behavior:
- Build saved searches from the user's profile, preferences, resume, target titles, locations, salary, visa needs, and excluded companies.
- Pull jobs from Adzuna, Jooble, JSearch, Greenhouse, Lever, company career pages, and forwarded email alerts.
- Deduplicate jobs by company, title, location, source URL, and normalized description.
- Label jobs as `strong_match`, `stretch`, `network_first`, `low_priority`, or `avoid`.
- Explain why a job matches and what is missing.

### 2. Application Readiness Skill

Prepares each target job for application.

Core behavior:
- Score resume-to-JD match.
- Extract must-have skills, nice-to-have skills, seniority signals, salary signals, visa constraints, and red flags.
- Recommend whether to apply directly, seek referral first, contact hiring manager first, or skip.
- Generate a tailored resume, cover letter, recruiter note, and application answers.
- Create a checklist of missing information before apply.

### 3. Referral Contact Finder Skill

Suggests relevant people the user can contact for referrals or informational chats.

Core behavior:
- Identify useful contact types: employees in the target team, alumni, second-degree contacts, recruiters, hiring managers, founders, engineering managers, and recent posters about the role.
- Rank contacts by likely referral value, warmth, seniority, role proximity, location, school/company overlap, and public activity.
- Explain why each contact is suggested.
- Avoid private scraping or invasive enrichment. Use user-authorized imports, public pages, company team pages, professional network exports, and manual user-provided data.

### 4. Outreach Drafting Skill

Creates personalized messages for referrals, recruiter outreach, hiring-manager notes, follow-ups, thank-you notes, and interview scheduling.

Core behavior:
- Draft short, respectful messages in the user's tone.
- Produce variants for LinkedIn, email, X/Twitter DM, and internal referral forms.
- Personalize from public context only when available and cite the basis internally.
- Track message status: `drafted`, `approved`, `sent`, `replied`, `follow_up_due`, `closed`.
- Suggest follow-up timing without spamming.

### 5. Apply Operator Skill

Handles application workflows in assisted, autofill, or autonomous mode.

Core behavior:
- Assisted mode: show user the exact fields and recommended answers.
- Autofill mode: browser extension fills forms after user review.
- Autonomous mode: server-side Playwright prepares the application, pauses before final submit, and asks for approval.
- Capture evidence of what was submitted: resume version, cover letter, answers, timestamp, portal, and confirmation number.
- Roll back safely when a session expires or a portal changes.

### 6. Relationship CRM Skill

Maintains a lightweight job-search CRM.

Core behavior:
- Track contacts, companies, jobs, applications, messages, referrals, interviews, and outcomes.
- Detect stale applications and recommend the next action.
- Show a daily action queue: apply, ask for referral, follow up, prepare interview, update profile.
- Produce weekly analytics: response rate by channel, resume variant, company type, title, and referral status.

### 7. Career Coach Skill

Turns search activity into strategy.

Core behavior:
- Recommend better target titles, company lists, skill upgrades, resume positioning, and outreach angles.
- Identify repeated rejection patterns or low-response segments.
- Generate a weekly plan with a manageable number of high-impact actions.
- Keep advice tied to observed data from the user's pipeline.

## User workflows

### Workflow A: Daily Job Hunt Queue

1. Agent refreshes jobs from configured sources.
2. Matching ranks jobs and groups them into apply-now, referral-first, research-more, and skip.
3. User sees a daily queue with reasons, missing skills, expected effort, and recommended action.
4. User approves jobs to prepare.
5. Application Readiness Skill creates resume, cover letter, and answers.

### Workflow B: Referral-First Application

1. User selects a job or company.
2. Contact Finder ranks possible referral contacts.
3. Outreach Drafting Skill creates short message variants.
4. User approves a contact and message.
5. Platform sends via connected channel only after approval, or copies the message for manual send.
6. CRM schedules follow-up and links the contact to the job.

### Workflow C: Recruiter / Hiring Manager Outreach

1. Agent identifies recruiter or hiring-manager style contacts from authorized sources.
2. Agent drafts a concise pitch tied to the role.
3. User reviews exact recipient, channel, and message.
4. After approval, platform sends or opens the channel for manual send.
5. CRM tracks response and next step.

### Workflow D: Assisted Apply

1. User opens a job.
2. Platform shows match score, red flags, tailored assets, and recommended answers.
3. User downloads or opens generated assets.
4. User applies manually.
5. Platform asks for result and updates the application tracker.

### Workflow E: Autofill Apply

1. User opens an ATS page with the browser extension installed.
2. Extension asks backend for prepared application data.
3. Extension fills fields and highlights uncertain answers.
4. User reviews and submits manually.
5. Extension reports submission metadata back to the backend.

### Workflow F: Autonomous Apply With Approval

1. User explicitly chooses autonomous mode for a specific job.
2. Agent opens the portal through Playwright and fills the application.
3. Agent pauses before submit and streams a review screen to the user.
4. User approves, edits, or cancels.
5. Only after approval does the agent submit.
6. Application record stores submitted evidence.

### Workflow G: Weekly Search Review

1. CRM aggregates applications, contacts, responses, interviews, and outcomes.
2. Career Coach Skill finds patterns and bottlenecks.
3. Platform recommends a weekly plan: target changes, contact goals, resume tweaks, and interview prep.
4. User accepts actions into the next week's queue.

## Data model additions

Add or extend these backend entities:

- `Contact`: name, title, company, source, profile URL, email if user-provided or authorized, seniority, relationship strength, notes.
- `CompanyTarget`: company, priority, reasons, excluded flag, target teams, known contacts.
- `ReferralOpportunity`: job, contact, score, reason, status, next action, last interaction.
- `OutreachMessage`: contact, job/company, channel, draft body, approved body, status, sent timestamp, follow-up timestamp.
- `ActionQueueItem`: action type, priority, due date, related job/contact/application, status.
- `ApplicationArtifact`: resume version, cover letter, answers, proof/confirmation metadata.
- `UserConsentEvent`: action type, target, payload hash, approval timestamp, expiry, actor.

## Backend implementation plan

### Phase 1: Data and APIs

- Add `contacts` app or fold contacts into `applications` if keeping app count low.
- Add models for contacts, referral opportunities, outreach messages, and action queue items.
- Add DRF endpoints for contact suggestions, outreach drafts, approvals, and queue actions.
- Add serializers that always separate `draft` from `approved` content.
- Add permissions so users can only access their own pipeline and contacts.

### Phase 2: Agent tools

Register these LangGraph tools behind phase gates:

- `discover_jobs`
- `score_job_fit`
- `prepare_application_assets`
- `find_referral_contacts`
- `rank_contacts`
- `draft_outreach_message`
- `schedule_follow_up`
- `prepare_apply_session`
- `request_user_approval`
- `record_application_submission`

All tools that send messages, submit forms, or use credentials must call `request_user_approval` first and verify the approval token has not expired.

### Phase 3: Contact sources

Start with low-risk sources:

- User-imported CSV contacts.
- Google Contacts with OAuth consent.
- User-provided LinkedIn/profile URLs.
- Company careers/team pages where public.
- Manual contact entry.

Later integrations:

- Gmail search for prior conversations, with explicit OAuth scopes and user controls.
- LinkedIn export import.
- Public search adapter for recruiters and hiring managers, with rate limits and source logging.

### Phase 4: Frontend UX

Add these screens/components:

- Daily action queue.
- Job detail action panel: `Apply`, `Find referral`, `Draft outreach`, `Skip`.
- Contact suggestion drawer with reasons and confidence.
- Outreach review modal showing recipient, channel, draft, editable message, and approval button.
- Application review screen before autonomous submit.
- CRM board with jobs, contacts, referrals, follow-ups, and interviews.
- Weekly search review dashboard.

### Phase 5: Extension support

- Expose prepared application data to the MV3 extension through `extension_api`.
- Add field-confidence metadata so uncertain autofill values are highlighted.
- Add a post-submit report endpoint for confirmation capture.
- Keep final submit manual in autofill mode.

### Phase 6: Observability and safety

- Log every external action as an auditable `UserConsentEvent`.
- Store message/application payload hashes so approvals match the actual outgoing content.
- Add rate limits for outreach and application attempts.
- Add spam/abuse guardrails: no bulk messaging, no misleading identity claims, no invented relationships, no automated unsolicited campaigns.
- Add tests proving irreversible actions cannot bypass HITL approval.

## Prioritized MVP slice

Build first:

1. Contact and outreach data models. **Implemented: `networking` app foundation.**
2. Manual contact import and manual contact entry. **Partially implemented: manual contact API.**
3. Referral Contact Finder using user contacts plus company/job context. **Implemented: service + agent tool.**
4. Outreach drafting with editable approval modal. **Backend implemented: draft + approval API/tool. Frontend pending.**
5. Daily action queue with referral-first recommendations. **Partially implemented: queue model/API.**
6. CRM follow-up tracking. **Partially implemented: follow-up queue item after approved send marker.**

Defer:

- Fully automated message sending.
- LinkedIn session automation.
- Autonomous apply across complex ATS portals.
- Email inbox mining.
- Large-scale public contact enrichment.

## Acceptance criteria

- User can open a matched job and ask for referral suggestions.
- Platform returns ranked contacts with clear reasons.
- User can generate and edit a referral message.
- No message can be sent until the user approves the exact recipient, channel, and content.
- User can track follow-ups and referral status.
- User can prepare application assets from the same workflow.
- HITL tests fail if an external action bypasses approval.

## Suggested milestones

### Milestone 1: Referral CRM foundation

Ship contacts, referral opportunities, outreach drafts, and queue items.

### Milestone 2: Referral-first job workflow

Connect matched jobs to contact ranking, message drafting, and follow-up scheduling.

### Milestone 3: Application workflow integration

Connect referral outcomes to assisted/autofill/autonomous application modes.

### Milestone 4: Search intelligence

Add weekly review, response analytics, contact effectiveness, and strategy recommendations.

### Milestone 5: Controlled external actions

Add opt-in sending integrations and autonomous apply expansion, protected by approval tokens and audit logs.
