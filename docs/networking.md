# Networking: contacts, company hub & the graph

Read this when you're touching the `networking` app — contacts, referrals, outreach, the per-company hub, or the interactive network graph.

Entity definitions live in [data-model.md](data-model.md#networking); this doc covers behaviour, endpoints, and the read models layered on top.

All endpoints are under `/api/v1/networking/` and require authentication. Everything is scoped to `request.user` unless noted; `Company` and `CompanyRelationship` are global (shared across users).

## Pieces

| Piece | Where | What it is |
|---|---|---|
| Contacts | `models.Contact` | A person in the user's network. `company` is a nullable FK to `jobs.Company`; a contact may also have richer `ContactEmployment` history. |
| Relationships | `ContactRelationship` | Directed person↔person edge (`colleague`, `manager`, `report`, `reference`, `mutual`, `classmate`, `friend`). Bidirectional kinds are stored as two rows. |
| Employments | `ContactEmployment` | A contact's time at a company; `overlaps()` powers colleague inference. |
| Referrals | `ReferralOpportunity` | A ranked (job, contact) pair — someone who could refer you for a specific job. |
| Outreach | `OutreachMessage` | A draft message, `draft → approved → sent`. **Drafts are never auto-sent**; `approve()` hashes the approved body (HITL gate, see [vision.md](vision.md) principle 9). |
| Action queue | `ActionQueueItem` | The user's prioritised networking next-actions (follow-ups, intros to make). |
| Company hub | `company_hub.py` | A **derived read view** (no table) joining a company to your contacts, its open jobs, and your applications. |
| Graph | `graph.py` | Neighbourhood traversal + warm-intro ranking + colleague inference over the tables above. |

## Endpoints

| Method + path | Purpose |
|---|---|
| `GET/POST /contacts/` · `GET/PATCH/DELETE /contacts/<id>/` | CRUD contacts. Write accepts `company_name` (a string) and get-or-creates the `Company`, setting the FK. |
| `GET/POST /contacts/<id>/employments/` · `DELETE /employments/<id>/` | A contact's employment history. |
| `GET/POST /contacts/<id>/relationships/` · `DELETE /relationships/<id>/` | Person↔person edges. `from_contact` is the URL contact; body carries `to_contact`, `kind`, `strength`. |
| `GET/POST /companies/<id>/relationships/` | Global company graph (parent/subsidiary/competitor/…). |
| `GET /companies/` | Company hub list — every company you have a contact, employment, or application at, with `contact_count` / `job_count` / `application_count`. |
| `GET/PATCH /companies/<id>/` | Company hub detail (below). PATCH updates the shared `careers_url` / `description`. |
| `GET /graph/?root=&depth=` | Node-link neighbourhood for the graph UI (below). |
| `GET /warm-intros/<company_id>/?max_hops=&limit=` | Ranked contacts who could warm-intro you into a company. |
| `GET /jobs/<job_id>/referrals/` · `GET /referrals/` | Referral suggestions for a job / all referrals. |
| `GET/POST /outreach/` · `POST /outreach/<id>/approve/` | List/draft outreach; approve a draft. |
| `GET /queue/?status=open` | The action queue. |

## Company hub (`company_hub.py`)

A cross-app read model — **no new tables, no migration.** It joins `Contact` / `ContactEmployment` (networking), `JobPosting` (jobs), and `Application` (applications) at query time.

- `relevant_company_ids(user)` — companies with a contact placed there, an employment record, or an application to one of the company's jobs.
- `company_summary(user, company)` — the card payload (name, domain, careers URL, counts).
- `company_detail(user, company)` — the full hub: `contacts` (via `Contact.company` FK **or** an employment at the company), `jobs` (open postings), `applications` (yours, derived through `Application → JobPosting → Company`), and `warm_intros` (top 5).

**The company↔application link is derived, never stored.** There is no `Application.company` FK — going through the job means it can't drift.

Frontend: `/companies` (list) and `/companies/:id` (hub) in the **More** menu. The hub also links to `/network?root=company:<id>` to centre the graph on that company.

## The graph (`graph.py`)

`neighborhood(user, root_kind, root_id, depth)` returns `{nodes, edges}` for the SVG viz, capped at ~200 nodes. `root_kind ∈ {user, contact, company}`; `depth` 1–3.

- `user` root: your contacts, plus each contact's **direct `company` FK** surfaced as a company node at depth 1 (not only via employment records).
- `contact` root: employments (→ companies) and outgoing relationships (→ contacts).
- `company` root: contacts employed there + related companies.

Node ids are `"<kind>:<pk>"` (e.g. `contact:42`). Edge `data.kind ∈ {rel, employment, contact_rel, company_rel}`.

Two other helpers share these tables:
- `warm_intros_to_company(...)` — hop-1 (direct employee) and hop-2 (a relationship to an employee) ranking, scored by recency + relationship strength. Also exposed at `/warm-intros/<id>/`.
- `infer_colleague_relationships(...)` — idempotently creates symmetric `colleague` edges from overlapping employments.

### GUI editing (frontend `routes/network/NetworkGraph.tsx`)

The graph is a **dependency-free SVG node-link diagram** (no React-Flow). Nodes are draggable, click-to-inspect, double-click-to-expand. Editing maps to the plain endpoints above:

- **Add person** → `POST /contacts/` with `company_name` (creates the company FK).
- **Connect** mode → click node A, then node B:
  - contact → contact: `POST /contacts/<A>/relationships/` (pick the kind).
  - contact ↔ company: `POST /contacts/<contact>/employments/` with `{company, is_current: true}`.

There is no adjacency-list input anywhere — the graph *is* the editor.
