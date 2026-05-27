# Career Navigator — EC2 Migration + Claude Code on the Box

> **You'll run these commands, not me.** I won't autonomously SSH into your EC2.
> Walk through each step in order, paste me the output if something looks off.

## Target

- **Host:** `ec2-13-207-61-191.ap-south-1.compute.amazonaws.com` (Mumbai region)
- **AMI assumed:** Amazon Linux 2023 (the `ec2-user` username is the giveaway).
  If `cat /etc/os-release` says Ubuntu, swap `dnf` → `apt` in the commands below.
- **Deploy style:** **SQLite** + gunicorn + nginx, systemd-managed, on the same single instance. (You earlier picked Postgres; this revision uses SQLite per your latest instruction — simpler, no DB server to operate, fine for one user. Migration to Postgres later is a `dumpdata` / `loaddata` away.)
- **Exposure:** open ports 80 (HTTP) and 22 (SSH) on the EC2 Security Group.
- **Claude Code:** installed system-wide on EC2, authenticated against your Claude.ai subscription via `claude login`.

## Pre-flight (on your laptop)

```powershell
# Fix key permissions — OpenSSH refuses to use a world-readable key.
icacls "my-key.pem" /inheritance:r /grant:r "$($env:USERNAME):(R)"

# Smoke-test the connection.
ssh -i "my-key.pem" ec2-user@ec2-13-207-61-191.ap-south-1.compute.amazonaws.com 'whoami && cat /etc/os-release | head -3'
```

If that prints `ec2-user` + the OS name, you're good. If it times out, the EC2 Security Group is blocking your IP on port 22 — add an inbound rule for your laptop's public IP.

Also check the **Security Group** in AWS Console → EC2 → Security Groups. Add inbound rules:

| Type        | Protocol | Port | Source             |
| ----------- | -------- | ---- | ------------------ |
| SSH         | TCP      | 22   | My IP              |
| HTTP        | TCP      | 80   | 0.0.0.0/0          |
| HTTPS       | TCP      | 443  | 0.0.0.0/0 *(opt.)* |

## Phase 1 — Provision the box

SSH in once, then run everything below as `ec2-user` (sudo where needed).

```bash
ssh -i "my-key.pem" ec2-user@ec2-13-207-61-191.ap-south-1.compute.amazonaws.com
```

Inside the box:

```bash
# System packages (Amazon Linux 2023)
sudo dnf update -y
sudo dnf install -y git python3.11 python3.11-pip python3.11-devel \
    sqlite redis6 nginx gcc \
    nodejs npm

# If python3.11 is unavailable: sudo dnf install -y python3 python3-pip python3-devel

# Start the services we DO need
sudo systemctl enable --now redis6
sudo systemctl enable --now nginx
```

> **No Postgres on this box** — we're using SQLite. No `postgresql-*` packages, no DB
> server, no separate user/role. The DB is a single file at
> `/opt/career-navigator/backend/db.sqlite3` and is owned by `ec2-user`.

## Phase 2 — SQLite directory + permissions

SQLite has no setup step — Django creates the file on first migrate. We only
need to make sure the directory is writable by the gunicorn user and that
nightly backups have somewhere to land.

```bash
sudo mkdir -p /opt/career-navigator
sudo chown ec2-user:ec2-user /opt/career-navigator

# Backup landing pad (used by Phase 9 cron, if you set it up later)
mkdir -p /opt/career-navigator/backups
```

> **Heads-up on SQLite + concurrency:** the project already runs Celery + Channels.
> SQLite serialises writes, so under heavy concurrent writes you'll see brief
> `database is locked` errors. The base settings already set
> `OPTIONS={'timeout': 20}` which is the right knob — Django will retry for 20s
> before giving up. Fine for a single-user dev box. If you ever see locks in
> production, that's the signal to migrate to Postgres.

## Phase 3 — Get the code onto the box

Pick **one** of the two options.

### Option A: clone from GitHub (preferred)

If the repo is on GitHub:

```bash
sudo mkdir -p /opt/career-navigator
sudo chown ec2-user:ec2-user /opt/career-navigator
cd /opt/career-navigator
git clone https://github.com/<your-user>/Carrer-Navigator.git .
```

### Option B: rsync from your laptop

From your **laptop** (PowerShell, with the repo as CWD):

```powershell
# Need scp/rsync via WSL or git-bash. If using OpenSSH only:
scp -i "my-key.pem" -r . ec2-user@ec2-13-207-61-191.ap-south-1.compute.amazonaws.com:/tmp/cn-staging
```

Then on the box:

```bash
sudo mkdir -p /opt/career-navigator
sudo chown ec2-user:ec2-user /opt/career-navigator
mv /tmp/cn-staging/* /opt/career-navigator/
cd /opt/career-navigator
```

## Phase 4 — Backend setup

```bash
cd /opt/career-navigator/backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# Generate strong secrets
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(50))"
python -c "import secrets; print('CREDENTIAL_ENCRYPTION_KEY=' + secrets.token_urlsafe(32))"
```

Write `/opt/career-navigator/backend/.env` from `.env.example`:

```bash
cp .env.example .env
nano .env
```

Set at minimum:

```
DJANGO_SETTINGS_MODULE=config.settings.prod
SECRET_KEY=<generated above>
DEBUG=False
ALLOWED_HOSTS=ec2-13-207-61-191.ap-south-1.compute.amazonaws.com,13.207.61.191
CORS_ALLOWED_ORIGINS=http://ec2-13-207-61-191.ap-south-1.compute.amazonaws.com
# Leave DATABASE_URL empty — that activates the SQLite fallback in
# config/settings/base.py at SQLITE_PATH below.
DATABASE_URL=
SQLITE_PATH=/opt/career-navigator/backend/db.sqlite3
REDIS_URL=redis://127.0.0.1:6379/0
USE_REDIS_CHANNEL_LAYER=True
CREDENTIAL_ENCRYPTION_KEY=<generated above>
```

> `config/settings/prod.py` is committed in this repo at
> [backend/config/settings/prod.py](backend/config/settings/prod.py) (added in the
> same commit that produced this plan). It thinly wraps `base.py` and enables
> production-safe defaults (`DEBUG=False`, secure cookies). You don't need to
> hand-write it.

Run migrations, collect static, create superuser:

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

## Phase 5 — Frontend build

```bash
cd /opt/career-navigator/frontend
npm install
# Bake the EC2 hostname into the build
VITE_API_BASE=http://ec2-13-207-61-191.ap-south-1.compute.amazonaws.com/api/v1 \
  npm run build
# Output in frontend/dist/ — nginx will serve it.
```

## Phase 6 — systemd units

Create three service files.

**`/etc/systemd/system/cn-backend.service`** (gunicorn for HTTP):

```ini
[Unit]
Description=Career Navigator backend (gunicorn)
After=network.target redis6.service

[Service]
User=ec2-user
WorkingDirectory=/opt/career-navigator/backend
EnvironmentFile=/opt/career-navigator/backend/.env
ExecStart=/opt/career-navigator/backend/.venv/bin/gunicorn \
    --workers 3 --bind 127.0.0.1:8000 \
    --access-logfile - --error-logfile - \
    config.wsgi:application
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**`/etc/systemd/system/cn-asgi.service`** (daphne for WebSockets):

```ini
[Unit]
Description=Career Navigator ASGI (daphne, WebSockets)
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/opt/career-navigator/backend
EnvironmentFile=/opt/career-navigator/backend/.env
ExecStart=/opt/career-navigator/backend/.venv/bin/daphne -b 127.0.0.1 -p 8001 config.asgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

**`/etc/systemd/system/cn-celery.service`** (worker + beat):

```ini
[Unit]
Description=Career Navigator Celery worker
After=network.target redis6.service

[Service]
User=ec2-user
WorkingDirectory=/opt/career-navigator/backend
EnvironmentFile=/opt/career-navigator/backend/.env
ExecStart=/opt/career-navigator/backend/.venv/bin/celery -A config worker -B -l info -S django
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable them:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now cn-backend cn-asgi cn-celery
sudo systemctl status cn-backend   # should be 'active (running)'
```

## Phase 7 — Nginx reverse proxy

**`/etc/nginx/conf.d/career-navigator.conf`**:

```nginx
server {
    listen 80 default_server;
    server_name ec2-13-207-61-191.ap-south-1.compute.amazonaws.com;
    client_max_body_size 25M;

    # Frontend SPA
    root /opt/career-navigator/frontend/dist;
    index index.html;

    location / {
        try_files $uri /index.html;
    }

    # Backend HTTP
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /admin/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }

    location /static/ {
        alias /opt/career-navigator/backend/staticfiles/;
    }

    # WebSockets
    location /ws/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

Need SELinux on Amazon Linux to allow nginx → proxy to localhost:

```bash
sudo setsebool -P httpd_can_network_connect 1
```

You should now be able to reach `http://ec2-13-207-61-191.ap-south-1.compute.amazonaws.com/` from your browser.

## Phase 8 — Install Claude Code on the EC2 box

```bash
# Node is already installed in Phase 1. Confirm version (need 18+):
node --version

# Install Claude Code globally
sudo npm install -g @anthropic-ai/claude-code

# Verify
claude --version
```

### Authenticate with your Claude.ai subscription

```bash
claude
# Inside the Claude Code prompt:
/login
```

The CLI prints a URL + a code. On your **laptop**, open the URL in a browser, sign in to Claude.ai, paste the code, approve. Then back on the EC2 terminal — it'll confirm auth and drop you into a session.

> Don't put `ANTHROPIC_API_KEY` in your shell rc — having both API key env var and subscription auth set sometimes confuses the CLI into using the wrong one.

### Detach so it survives SSH disconnect

Two options:

**(a) tmux — for interactive sessions you can detach/reattach:**

```bash
sudo dnf install -y tmux
tmux new -s claude
# Inside the tmux session:
cd /opt/career-navigator
claude
# Detach with Ctrl+B then D
# Reattach later: tmux attach -t claude
```

**(b) Just run `claude` over SSH each time** — simpler if you're always going to be at a terminal.

## Phase 9 — Remote control workflow

From your laptop, any time you want to drive Claude on the EC2 box:

```powershell
ssh -i "my-key.pem" ec2-user@ec2-13-207-61-191.ap-south-1.compute.amazonaws.com -t "tmux attach -t claude || tmux new -s claude 'cd /opt/career-navigator && claude'"
```

Drop that into a `claude-remote.ps1` script so you can run it with one command.

## Verification checklist

- [ ] `ssh ec2-user@…` from your laptop → lands in shell.
- [ ] `sudo systemctl status cn-backend cn-asgi cn-celery nginx redis6` → all `active (running)`. (No `postgresql` — we're on SQLite.)
- [ ] `ls -la /opt/career-navigator/backend/db.sqlite3` → file exists, owned by `ec2-user`.
- [ ] `curl -I http://13.207.61.191/` → 200 OK with HTML.
- [ ] `curl http://13.207.61.191/api/v1/auth/me/` → 401 (means routing works, auth is required — expected).
- [ ] Open `http://ec2-13-207-61-191.ap-south-1.compute.amazonaws.com/` in browser → app loads.
- [ ] On EC2: `claude --version` prints a version; `claude` opens the REPL; `/login` completes; `claude "say hi"` returns a response.
- [ ] `tmux attach -t claude` works after a fresh SSH login.

## What's out of scope (do later)

- **HTTPS / Let's Encrypt** — needs a real domain you own pointed at the EC2 IP, then `sudo dnf install certbot python3-certbot-nginx && sudo certbot --nginx -d your.domain`.
- **Backups** — `sqlite3 db.sqlite3 ".backup '/opt/career-navigator/backups/db-$(date +%Y%m%d).sqlite3'"` from a cron job, plus EBS snapshot schedule. Snippet for `/etc/cron.daily/cn-db-backup`:

  ```bash
  #!/bin/bash
  set -e
  /usr/bin/sqlite3 /opt/career-navigator/backend/db.sqlite3 \
      ".backup '/opt/career-navigator/backups/db-$(date +%Y%m%d).sqlite3'"
  find /opt/career-navigator/backups -name 'db-*.sqlite3' -mtime +14 -delete
  ```
  Then `sudo chmod +x /etc/cron.daily/cn-db-backup`.
- **Auto-deploy on push** — GitHub Actions → SSH → `git pull && systemctl restart cn-backend`. Out of scope for v1.
- **Monitoring** — CloudWatch logs, CPU/RAM alerts.
- **Secrets** — for v1 they live in `.env`. Long-term, AWS SSM Parameter Store.

## Where I can help inline

- Paste me the output of any step that fails — I'll diagnose.
- I can write the `claude-remote.ps1` wrapper, a deploy script for future redeploys, or a backup cron job when you want them.
- I cannot run the actual SSH session, type your Claude.ai login code, or set up the EC2 Security Group — those are your hands on your laptop / console.
