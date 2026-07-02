# Notifications: alerts, activity feed & web push

Read this when you're touching saved-search alerts, the in-app activity feed, or browser web-push — including the operational VAPID setup.

All endpoints are under `/api/v1/notifications/` and require authentication.

## Models (`notifications/models.py`)

| Model | What it is |
|---|---|
| `Subscription` | A saved search: `filter_json` (the query DSL), `channels` (which delivery channels), `enabled`. |
| `Alert` | One delivered notification: `(user, job, subscription, channel, read, sent_at)`. |
| `WebPushDevice` | A browser push endpoint: `endpoint`, `auth`, `p256dh` keys (per device). |

Channels (`Channel`): `inapp`, `email`, `webpush`.

## Flow

1. A user saves a `Subscription` with a filter and one or more channels.
2. When ingestion surfaces a matching `JobPosting`, `notifications/services.py` fans out an `Alert` per channel — in-app (a row), email, and/or web push (`webpush.send_web_push` to each of the user's `WebPushDevice`s).
3. The UI reads them back through the alert + activity endpoints.

## Activity feed (`notifications/activity.py`)

`build_activity(user, limit=25)` merges two streams into one reverse-chronological feed for the notification bell:

- **Alerts** → `kind='alert'` (carries `read` + `alert_id`).
- **Application events** (`ApplicationEvent`) → `status` (status changed), `material` (resume/cover letter generated), or `apply` (approval issued / prepared).

Each item is `{key, kind, title, subtitle, url, at, read, alert_id?}`; the endpoint returns `{items, unread}`. This is what powers the bell dropdown, not just raw alerts.

## Endpoints

| Path | Purpose |
|---|---|
| `GET/POST /subscriptions/` · `GET/PATCH/DELETE /subscriptions/<id>/` | Manage saved searches. |
| `GET /alerts/` · `POST /alerts/<id>/read/` | List alerts; mark one read. |
| `GET /activity/` | Unified activity feed (alerts + application events) for the bell. |
| `GET /vapid-public-key/` | The VAPID public key the browser needs to subscribe. |
| `POST /push/register/` · `POST /push/unregister/` | Upsert / remove a `WebPushDevice`. |

## Web push (operational)

**Backend** reads three env vars (`config/settings/base.py`):

```
VAPID_PUBLIC_KEY     # base64url, exposed via /vapid-public-key/
VAPID_PRIVATE_KEY    # base64url, server-only
VAPID_CLAIM_EMAIL    # "mailto:you@example.com" (defaults to a local placeholder)
```

Both `.env` files are gitignored. **Gotcha:** the repo-root `.env` is loaded first with `override=False`, so an empty value there blocks a real value in `backend/.env`. Put the real keys in the **repo-root** `.env`, or push will report `enabled: false` despite `backend/.env` looking correct.

Generate a keypair once with `py_vapid` (installed as a dependency):

```bash
vapid --gen           # writes private/public keys
vapid --applicationServerKey   # prints the base64url public key for VAPID_PUBLIC_KEY
```

**Frontend:** the service worker is `frontend/public/sw.js`; subscription logic is `frontend/src/lib/push.ts`. It fetches `/vapid-public-key/`, converts the base64url key to a `Uint8Array` (over an explicit `ArrayBuffer`, cast to `BufferSource` to satisfy TS 5.7), subscribes via the Push API, and POSTs the endpoint to `/push/register/`.

Push requires HTTPS (or `localhost`) and user permission; a denied permission or missing VAPID key degrades gracefully — the in-app + email channels still deliver.
