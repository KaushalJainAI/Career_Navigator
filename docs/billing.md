# Billing: the credit model

Read this when you're touching anything that spends credits, or wiring a new paid action.

Career Navigator uses a **simple, honest credit model — no Stripe yet.** Every user gets a welcome bonus; AI-heavy actions cost a fixed number of credits; everything else is free. Credits are *rolling* — they never expire.

All endpoints are under `/api/v1/billing/` and require authentication.

## What's free vs paid

**Always free:** browsing/searching jobs, match scoring, Ghost-Job Shield, the applications Kanban + Todos/Goals, response analytics, contacts & the network graph, saved-search alerts.

**Paid (per action):**

| Reason key | Action | Cost |
|---|---|---|
| `tailor_resume` | AI-tailored resume for one job (+ truthfulness pass) | 5 |
| `cover_letter` | Tailored cover letter | 3 |
| `mock_interview` | Interview grill session (question bank + graded round + study plan) | 8 |
| `autonomous_apply` | Agent prepares a full application (pauses for one-tap approval) | 10 |

Source of truth: `billing/pricing.py` (`PRICING`, `CATALOG`, `SIGNUP_BONUS = 100`). The `CATALOG` carries human-facing labels + blurbs so cost is visible **before** the user spends. These keys match `CreditLedger.REASONS`, so every spend is auditable.

## The ledger

`billing.models.CreditLedger` is **append-only**: each row is a signed `delta` + a `reason`. Balance = `sum(delta)`. Reasons: `signup_bonus`, `tailor_resume`, `cover_letter`, `autonomous_apply`, `mock_interview`, `top_up`, `stripe_purchase`, `refund`. See [data-model.md](data-model.md#billing).

## Services (`billing/services.py`)

```python
balance(user) -> int
charge(user, reason, *, meta=None)   -> CreditLedger | None   # writes a negative delta
grant(user, reason, amount, *, meta=None) -> CreditLedger     # positive delta
grant_signup_bonus(user)             -> CreditLedger | None    # +SIGNUP_BONUS, idempotent
```

- **`charge` raises `InsufficientCredits` (HTTP 402)** when the balance can't cover `cost_of(reason)`. A free action (`cost 0`) is a no-op returning `None`.
- **Charge *before* the expensive work.** Call `charge()` first so a broke user gets a clean 402 instead of half a service (a burned LLM call with no result). The pattern:

  ```python
  charge(request.user, 'tailor_resume')   # 402s here if short
  result = run_expensive_llm_tailoring(...)  # only runs if the charge succeeded
  ```

- **Signup bonus** is granted by a `post_save` signal on user creation (`billing/signals.py::award_signup_bonus`), so first-run flows — and tests — are always funded. Tests that assert a balance must account for the +100 grant.

## Endpoints

| Path | Returns |
|---|---|
| `GET /summary/` | Balance + `signup_bonus` + catalogue for the billing screen. |
| `GET /pricing/` | The `CATALOG` (labels, costs, blurbs). |
| `GET /ledger/` | The user's ledger rows. |
| `POST /top-up/` | Manual credit grant (dev / no-Stripe stand-in for a purchase). |

## Adding a new paid action

1. Add the key + cost to `PRICING` and an entry to `CATALOG` in `pricing.py` (the key must also exist in `CreditLedger.REASONS`).
2. Call `charge(user, '<reason>')` at the **top** of the view, before the expensive work.
3. Surface the cost in the UI with the shared `CreditCost` component (reads `/pricing/`).

## Not built yet

Stripe checkout/webhooks and `StripeSubscription` activation. The model and `stripe_purchase` reason exist as a seam; `/top-up/` stands in for a purchase in the meantime.
