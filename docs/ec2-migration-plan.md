# Career Navigator — EC2 Migration + Claude Code on the Box

> **You'll run these commands, not me.** I won't autonomously SSH into your EC2.
> Walk through each step in order, paste me the output if something looks off.

## Target

- **Host:** `ec2-13-207-61-191.ap-south-1.compute.amazonaws.com` (Mumbai region)
- **Public hostname:** `career.kaushaljain.com` (Cloudflare A record → 13.207.61.191, proxied / orange cloud)
- **TLS:** Cloudflare-proxied with a **Cloudflare Origin Certificate** on the EC2 box (Phase 10). Browsers → Cloudflare uses CF's universal cert; Cloudflare → origin uses the origin cert. SSL mode set to **Full (strict)** in the CF dashboard.
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

| Type        | Protocol | Port | Source                |
| ----------- | -------- | ---- | --------------------- |
| SSH         | TCP      | 22   | My IP                 |
| HTTP        | TCP      | 80   | 0.0.0.0/0             |
| HTTPS       | TCP      | 443  | 0.0.0.0/0             |

> **Tightening later:** Once Phase 10 is up, port 80 / 443 can be restricted to
> just Cloudflare's published IP ranges (https://www.cloudflare.com/ips/) so
> the EC2 origin can't be hit directly, only through CF. This blocks direct-IP
> abuse and DDoS. Out of scope for the first deploy.

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
# Public hostname first, then internal EC2 names. Cloudflare sends Host: career.kaushaljain.com.
ALLOWED_HOSTS=career.kaushaljain.com,ec2-13-207-61-191.ap-south-1.compute.amazonaws.com,13.207.61.191
CORS_ALLOWED_ORIGINS=https://career.kaushaljain.com
FRONTEND_URL=https://career.kaushaljain.com
# Force HTTPS redirects + 1-year HSTS. Safe because Cloudflare always terminates HTTPS
# in front of us; the origin only ever sees X-Forwarded-Proto=https from CF.
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
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
# Bake the public HTTPS hostname into the build
VITE_API_BASE=https://career.kaushaljain.com/api/v1 \
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

> **Defer the actual HTTPS listener until Phase 10** — we want the Origin
> Certificate in place before nginx tries to bind to 443. For now, write the
> HTTP-only block below. Phase 10 will replace this file with the full HTTPS
> version.

**`/etc/nginx/conf.d/career-navigator.conf`** (interim, HTTP only):

```nginx
server {
    listen 80 default_server;
    server_name career.kaushaljain.com ec2-13-207-61-191.ap-south-1.compute.amazonaws.com;
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

SELinux on Amazon Linux must allow nginx → proxy to localhost:

```bash
sudo setsebool -P httpd_can_network_connect 1
```

> While Cloudflare is still set to SSL mode "Flexible" (the default for new
> proxied records), `https://career.kaushaljain.com/` will already work from
> the browser side — CF terminates TLS and talks plain HTTP to your origin.
> That's fine for a smoke test but **not** what we want long-term: it leaves
> the CF → origin hop unencrypted. Phase 10 fixes that.

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

## Phase 10 — TLS via Cloudflare Origin Certificate

Goal: HTTPS end-to-end (browser → CF and CF → origin), with CF SSL mode
**Full (strict)** so Cloudflare validates the origin cert on every request.

### 10.1 Generate the certificate (in Cloudflare dashboard — manual step)

1. Open https://dash.cloudflare.com/ → select **kaushaljain.com**.
2. Sidebar → **SSL/TLS → Origin Server → Create Certificate**.
3. Keep defaults:
   - Generate private key + CSR with Cloudflare ✓
   - Key type: **RSA (2048)**
   - Hostnames: `career.kaushaljain.com` (and add `*.kaushaljain.com` if you want one cert to cover future subdomains)
   - Certificate validity: **15 years**
4. Click **Create**. You'll see two PEM blocks. **The private key is shown only once** — leave the tab open while you SSH in.

### 10.2 Install the cert on the EC2 box

```bash
sudo mkdir -p /etc/ssl/cloudflare
sudo chmod 750 /etc/ssl/cloudflare
sudo chown root:root /etc/ssl/cloudflare

# Paste the certificate block into:
sudo nano /etc/ssl/cloudflare/career.kaushaljain.com.pem
# Paste the private key block into:
sudo nano /etc/ssl/cloudflare/career.kaushaljain.com.key

sudo chmod 644 /etc/ssl/cloudflare/career.kaushaljain.com.pem
sudo chmod 600 /etc/ssl/cloudflare/career.kaushaljain.com.key
```

### 10.3 Fetch Cloudflare's Authenticated Origin Pull root cert (optional but recommended)

This lets you also enable **Authenticated Origin Pulls** later, so the origin
only accepts connections from Cloudflare:

```bash
sudo curl -fsSL -o /etc/ssl/cloudflare/cf-authenticated-origin.pem \
    https://developers.cloudflare.com/ssl/static/authenticated_origin_pull_ca.pem
```

### 10.4 Replace the nginx config with the HTTPS version

Overwrite `/etc/nginx/conf.d/career-navigator.conf`:

```nginx
# Cloudflare → origin real-IP restoration so Django sees the real client IP,
# not Cloudflare's edge IP, in X-Forwarded-For. CF IP ranges:
# https://www.cloudflare.com/ips/   (refresh occasionally; rare changes)
set_real_ip_from 173.245.48.0/20;
set_real_ip_from 103.21.244.0/22;
set_real_ip_from 103.22.200.0/22;
set_real_ip_from 103.31.4.0/22;
set_real_ip_from 141.101.64.0/18;
set_real_ip_from 108.162.192.0/18;
set_real_ip_from 190.93.240.0/20;
set_real_ip_from 188.114.96.0/20;
set_real_ip_from 197.234.240.0/22;
set_real_ip_from 198.41.128.0/17;
set_real_ip_from 162.158.0.0/15;
set_real_ip_from 104.16.0.0/13;
set_real_ip_from 104.24.0.0/14;
set_real_ip_from 172.64.0.0/13;
set_real_ip_from 131.0.72.0/22;
set_real_ip_from 2400:cb00::/32;
set_real_ip_from 2606:4700::/44;
set_real_ip_from 2803:f800::/32;
set_real_ip_from 2405:b500::/32;
set_real_ip_from 2405:8100::/32;
set_real_ip_from 2a06:98c0::/29;
set_real_ip_from 2c0f:f248::/32;
real_ip_header CF-Connecting-IP;

# Redirect any plain-HTTP that gets through to HTTPS.
server {
    listen 80 default_server;
    server_name career.kaushaljain.com ec2-13-207-61-191.ap-south-1.compute.amazonaws.com;
    return 301 https://career.kaushaljain.com$request_uri;
}

server {
    listen 443 ssl http2 default_server;
    server_name career.kaushaljain.com;
    client_max_body_size 25M;

    ssl_certificate     /etc/ssl/cloudflare/career.kaushaljain.com.pem;
    ssl_certificate_key /etc/ssl/cloudflare/career.kaushaljain.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    # HSTS — Cloudflare will also send its own; this is the origin response.
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Frontend SPA
    root /opt/career-navigator/frontend/dist;
    index index.html;
    location / {
        try_files $uri /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        # Critical: tell Django that the original request was HTTPS, so
        # SECURE_SSL_REDIRECT in prod.py doesn't bounce-loop.
        proxy_set_header X-Forwarded-Proto https;
    }

    location /admin/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
    }

    location /static/ {
        alias /opt/career-navigator/backend/staticfiles/;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

Test + reload:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

### 10.5 Switch Cloudflare SSL mode to Full (strict)

Cloudflare dashboard → **SSL/TLS → Overview** → set mode to **Full (strict)**.

Also under **SSL/TLS → Edge Certificates**:

- **Always Use HTTPS:** ON
- **Automatic HTTPS Rewrites:** ON
- **Minimum TLS Version:** 1.2
- **HTTP Strict Transport Security:** enable with 6-month max-age (you can extend after a week of stable operation)

### 10.6 Smoke-test the chain

From your laptop:

```powershell
# Should return HTTP/2 200 from CF (cf-ray header present), no certificate warnings.
curl.exe -I https://career.kaushaljain.com/

# API: returns 401 Unauthorized (proves routing + Django reached, auth required).
curl.exe -I https://career.kaushaljain.com/api/v1/auth/me/

# Plain HTTP redirects to HTTPS.
curl.exe -I http://career.kaushaljain.com/
```

If anything 5xx's: `sudo journalctl -u nginx -n 50` on the box for nginx
errors, `sudo journalctl -u cn-backend -n 50` for Django errors.

### 10.7 Tighten the env + restart

The `.env` already has `SECURE_SSL_REDIRECT=True` and HSTS from Phase 4.
Restart so prod.py re-reads them:

```bash
sudo systemctl restart cn-backend cn-asgi
```

> **Important about SECURE_SSL_REDIRECT:** prod.py reads
> `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')`. The nginx
> config above sends `X-Forwarded-Proto: https` on every proxied request, so
> Django correctly identifies the request as secure and the redirect doesn't
> infinite-loop. If you ever see a redirect loop, that header is the thing to
> check.

## Verification checklist

- [ ] `ssh ec2-user@…` from your laptop → lands in shell.
- [ ] `sudo systemctl status cn-backend cn-asgi cn-celery nginx redis6` → all `active (running)`. (No `postgresql` — we're on SQLite.)
- [ ] `ls -la /opt/career-navigator/backend/db.sqlite3` → file exists, owned by `ec2-user`.
- [ ] `curl -I https://career.kaushaljain.com/` → 200 OK with HTML, `cf-ray` header present (proves Cloudflare path).
- [ ] `curl -I http://career.kaushaljain.com/` → 301 redirect to https://.
- [ ] `curl https://career.kaushaljain.com/api/v1/auth/me/` → 401 (means routing works, auth is required — expected).
- [ ] Open `https://career.kaushaljain.com/` in browser → app loads with green padlock, no mixed-content warnings.
- [ ] In CF dashboard, SSL/TLS Overview shows current mode = **Full (strict)** and origin certificate status = **Active**.
- [ ] On EC2: `claude --version` prints a version; `claude` opens the REPL; `/login` completes; `claude "say hi"` returns a response.
- [ ] `tmux attach -t claude` works after a fresh SSH login.

## What's out of scope (do later)

- ~~**HTTPS / Let's Encrypt**~~ — done via Cloudflare Origin Cert in Phase 10. Let's Encrypt direct on the origin is unnecessary while CF terminates TLS in front.
- **Authenticated Origin Pulls** — Phase 10.3 fetched the CA cert. To finish the lockdown: in CF dashboard SSL/TLS → Origin Server → enable *Authenticated Origin Pulls*, then add `ssl_client_certificate /etc/ssl/cloudflare/cf-authenticated-origin.pem; ssl_verify_client on;` to the nginx 443 server block. Origin will then refuse any request that didn't come through Cloudflare.
- **Restrict EC2 Security Group to CF IPs only** — replace the `0.0.0.0/0` rules for ports 80/443 with the CF IPv4/IPv6 ranges. Pairs well with Authenticated Origin Pulls.
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
