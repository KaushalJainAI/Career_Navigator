# Development

How to run this thing locally and what knobs exist.

## Prerequisites

| Tool | Version | Why |
|---|---|---|
| Python | 3.12+ | Backend |
| Node | 20+ | Frontend |
| Redis | 7+ | Channels + Celery (optional in dev) |
| Postgres | 16+ | Optional — SQLite is the default in dev |
| ripgrep | any | Will be required by the future JSONL+grep retrieval layer |

The path to the repo on disk is `c:\Users\91700\Desktop\Carrer Navigator` — note the misspelt `Carrer`.

## First-time setup

```bash
# 1. Backend
cd backend
python -m venv venv
# Windows
.\venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
#  ─ edit .env: at minimum set CREDENTIAL_ENCRYPTION_KEY to a long random string
#    python -c "import secrets; print(secrets.token_urlsafe(32))"

python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser

# 2. Frontend (separate shell)
cd frontend
cp .env.example .env
#  ─ edit .env: VITE_GOOGLE_CLIENT_ID only needed if you want Google sign-in locally
npm install
```

## Running

In the simplest dev mode you just need two processes:

```bash
# Terminal 1: backend
cd backend && source venv/bin/activate
python manage.py runserver
# Serves HTTP on http://localhost:8000

# Terminal 2: frontend
cd frontend && npm run dev
# Serves React on http://localhost:5173
```

For WebSocket development (notifications + interview live grilling) swap `runserver` for daphne:

```bash
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

If you're testing ingestion / autonomous-apply paths you need Celery + Redis:

```bash
# Terminal 3
redis-server  # or `docker run -p 6379:6379 redis`

# Terminal 4
cd backend && celery -A config worker -l info

# Terminal 5 (only if testing scheduled ingestion)
cd backend && celery -A config beat -l info -S django

# And set in backend/.env:
USE_REDIS_CHANNEL_LAYER=True
RUN_INGESTION_ASYNC=True
```

Otherwise `RUN_INGESTION_ASYNC=False` keeps everything synchronous — fine for most feature work.

## Full stack via Docker

```bash
cd infra
cp ../backend/.env.example ../backend/.env
docker compose up
```

This brings up Postgres, Redis, backend (daphne), Celery worker, Celery beat, and the Vite dev server. Hot-reload works on both backend and frontend volumes.

## Configuration

### Settings layers

[backend/config/settings/](../backend/config/settings/):

- `base.py` — everything, env-driven.
- `local.py` — `from .base import *`, `DEBUG=True`, CORS=*.
- `test.py` — in-memory SQLite, eager Celery, fast hasher, default encryption key.

Pick which one via `DJANGO_SETTINGS_MODULE`. Defaults: dev = `local`, tests = `test` (set in [pytest.ini](../backend/pytest.ini)).

### Env keys (backend)

See [backend/.env.example](../backend/.env.example). Highlights:

| Key | When you need it |
|---|---|
| `CREDENTIAL_ENCRYPTION_KEY` | **Always.** AES-GCM master key for the credentials vault. |
| `DATABASE_URL` | Optional. Falls back to SQLite. |
| `REDIS_URL` | If using Celery / channel layer. |
| `RUN_INGESTION_ASYNC` | `True` to route ingestion through Celery; `False` for sync dev. |
| `USE_REDIS_CHANNEL_LAYER` | `True` in prod / multi-process; `False` uses in-memory. |
| `NVIDIA_API_KEY` | For the guest-mode pool. |
| `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` | Required to ingest Adzuna. |
| `GREENHOUSE_TOKENS` | Comma-separated company tokens (e.g. `stripe,airbnb,figma`). |
| `GOOGLE_OAUTH_CLIENT_ID` / `..._SECRET` / `..._REDIRECT_URI` | For Google sign-in. |
| `RESEND_API_KEY` | Email notifications. |
| `VAPID_*` | Web-push notifications. |
| `STRIPE_*` | Phase 1.5+ billing. |

### Env keys (frontend)

See [frontend/.env.example](../frontend/.env.example):

| Key | Notes |
|---|---|
| `VITE_API_URL` | Default `http://localhost:8000/api/v1`. |
| `VITE_WS_URL` | Default `ws://localhost:8000`. |
| `VITE_GOOGLE_CLIENT_ID` | The OAuth client id used by the front-channel redirect. |
| `VITE_GOOGLE_REDIRECT_URI` | Must match the value registered with Google AND the backend's `GOOGLE_OAUTH_REDIRECT_URI`. |

## Common dev tasks

### Add a Django app

The 15 apps in this repo were not made via `startapp` — they're hand-laid because we wanted custom layouts (`tests/` subdir, etc.). Mimic an existing thin app like [billing](../backend/billing/) or [vault](../backend/vault/):

```
backend/<app>/
  __init__.py
  apps.py
  models.py
  serializers.py
  views.py
  urls.py
  admin.py
  migrations/__init__.py
  tests/__init__.py
  tests/test_models.py
```

Register in `INSTALLED_APPS` and `config/urls.py`.

### Run a single test

```bash
cd backend
pytest backend/agent/tests/test_graph.py -q
pytest backend/agent/tests/test_graph.py::test_hitl_hard_gate_pauses_without_approval_token -q
```

See [testing.md](./testing.md) for the full policy.

### Open the OpenAPI explorer

`python manage.py runserver` → http://localhost:8000/api/docs/

### Inspect ingestion runs

```bash
python manage.py shell
>>> from ingestion.models import IngestionRun
>>> IngestionRun.objects.order_by('-started_at')[:5].values('source__name', 'status', 'stats')
```

### Issue an autonomous-apply approval token by hand (dev / testing)

```bash
python manage.py shell
>>> from applications.models import Application, AutoApplySession
>>> app = Application.objects.first()
>>> session = AutoApplySession.objects.create(user=app.user)
>>> app.auto_apply_session = session; app.save()
>>> print(session.issue_approval_token())
```

Then call `submit_application(application_id=app.id, approval_token=…)` via the agent. Without that token the tool refuses — see [agent.md](./agent.md).

### Encrypt a credential by hand

```bash
python manage.py shell
>>> from credentials.models import Credential
>>> u = ...
>>> c = Credential(user=u, provider='openrouter', label='default')
>>> c.set_secret('sk-or-v1-xxx'); c.save()
```

`Credential.reveal()` decrypts on demand. The ciphertext is the only field on disk.

## Editor configuration

- Pyright/Pylance: point Python interpreter at `backend/venv`.
- Tailwind IntelliSense: enabled by default if you open the workspace at the repo root; `frontend/tailwind.config.js` and `frontend/index.html` drive the content paths.

## Troubleshooting

| Symptom | Likely fix |
|---|---|
| `ImproperlyConfigured: CREDENTIAL_ENCRYPTION_KEY must be set` | Set it in `backend/.env` (any string ≥ 1 char; SHA-256 normalises). |
| WebSocket connection 4401 immediately | The user is anonymous on the WS — Channels middleware needs a valid JWT in the query string or cookies. The frontend extension still has to ship Phase 2. |
| Adzuna returns 0 rows | Confirm `ADZUNA_APP_ID` + `ADZUNA_APP_KEY` are set and the `Source` row has `enabled=True`. |
| Google sign-in 400 with "Token exchange failed" | The redirect_uri in the backend `.env` and the frontend `.env` and the Google Cloud Console must be byte-identical. |
| Tests fail with "Apps aren't loaded yet" | Run pytest from `backend/`, not from the repo root, and confirm `DJANGO_SETTINGS_MODULE=config.settings.test` is picked up via `pytest.ini`. |
