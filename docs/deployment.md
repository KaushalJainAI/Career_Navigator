# Deployment: the `testing.kaushaljain.com` box

Read this when you need to (re)deploy the live demo, or you changed backend code and it isn't showing up.

Career Navigator is served from a small (~912 MB RAM) EC2 host behind nginx + TLS at **https://testing.kaushaljain.com**. The box runs **one project at a time**, switched by a helper script.

For local dev (ports, env keys, test commands) see [development.md](development.md); this doc is only about the shared testing host.

## The `switch` runner

`switch` (`/usr/local/bin/switch` → `~/apps/switch`) picks which project the domain serves. Projects are declared in `~/apps/projects.d/<name>.conf`.

```bash
switch                      # list configured projects + which is active
switch status               # active project, its systemd unit, and `free -h`
switch careernavigator      # make Career Navigator live (serves the existing build)
switch careernavigator --build   # rebuild the frontend, then serve + reload nginx
switch stop                 # tear down; domain shows the placeholder page
```

Switching to a project **stops whatever ran before** (single-project rule). The running backend is a **transient systemd unit** (`testing-app`) capped at `MemoryMax=600M` / `MemorySwapMax=1G` so a runaway process can't take the box down.

### Career Navigator's config (`~/apps/projects.d/careernavigator.conf`)

```
TYPE="fullstack"
WORKDIR="/home/ec2-user/projects/CareerNavigator/backend"
START_CMD="…/python manage.py runserver 127.0.0.1:8000 --noreload"
BUILD_CMD="cd …/frontend && npm ci && npm run build"
STATIC_DIR="…/frontend/dist"
```

**Deploys straight from the working tree** — there is no git checkout in the deploy path. So uncommitted changes on the `agent` branch *are* what's live. "Shipped to testing" ≠ "merged to main".

### How requests are routed

nginx serves the built SPA from `STATIC_DIR` and proxies these path prefixes to the backend on `127.0.0.1:8000`: **`/api /admin /ws /static /media`**.

The API is mounted at **`/api/v1/`** (see `backend/config/urls.py`: `path('api/v1/', include(api_v1))`). So the real URL of, e.g., the company hub is `/api/v1/networking/companies/` — the axios client's `baseURL` already includes `/api/v1`. Testing a bare `/api/networking/...` will 404; that's the wrong prefix, not a missing route.

## Deploying a change

```bash
# frontend or full change:
switch careernavigator --build
```

`--build` does `npm ci && vite build` (uses swap — be patient on this box), reloads nginx, and restarts the backend unit.

### ⚠️ Backend `--noreload` gotcha

The backend runs `runserver … --noreload`, so **a long-lived process never picks up Python changes on its own.** If you edited backend code and the old process is still up (e.g. you only rebuilt the frontend, or the unit didn't cycle), you must restart the unit:

```bash
sudo systemctl stop testing-app
sudo systemctl reset-failed testing-app
sudo systemd-run --unit=testing-app --collect \
  -p MemoryMax=650M -p MemorySwapMax=650M -p MemoryHigh=500M \
  --working-directory=/home/ec2-user/projects/CareerNavigator/backend \
  --uid=ec2-user --gid=ec2-user \
  /usr/bin/env bash -lc "/home/ec2-user/.venvs/shared/bin/python manage.py runserver 127.0.0.1:8000 --noreload"
```

**Symptom:** a brand-new backend route 404s while the SPA loads fine — the frontend rebuilt but the backend is running stale code. Restart the unit and re-test.

Logs: `sudo journalctl -u testing-app -n 50`. Health: `systemctl is-active testing-app`.

## Verifying a deploy

```bash
# mint a JWT for a real user, then curl the live API at the correct prefix:
TOKEN=$(cd backend && DJANGO_SETTINGS_MODULE=config.settings.local \
  ~/.venvs/shared/bin/python -c "import django; django.setup(); \
  from django.contrib.auth import get_user_model; \
  from rest_framework_simplejwt.tokens import RefreshToken; \
  print(RefreshToken.for_user(get_user_model().objects.first()).access_token)")
curl -s -H "Authorization: Bearer $TOKEN" https://testing.kaushaljain.com/api/v1/... 
```

Grep the built bundle for a feature string to confirm the frontend deployed:

```bash
grep -c "Some new UI string" frontend/dist/assets/index-*.js
```

## Demo data

Seed a realistic dataset (jobs, contacts, referrals, outreach, actions, alerts) for a user:

```bash
cd backend && DJANGO_SETTINGS_MODULE=config.settings.local \
  ~/.venvs/shared/bin/python manage.py seed_demo --email <user@email> --clear
```

## Env / secrets

Both `.env` files (repo-root and `backend/.env`) are gitignored. The repo-root `.env` loads first with `override=False`, so real values belong there (see the VAPID note in [notifications.md](notifications.md)).
