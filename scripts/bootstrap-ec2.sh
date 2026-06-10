#!/usr/bin/env bash
# bootstrap-ec2.sh — one-shot, idempotent installer for Career Navigator on Amazon Linux 2023.
#
# Run on the EC2 box from ANY directory:
#   bash bootstrap-ec2.sh
#
# Safe to re-run. Each step detects whether it's already done and prints
# [DONE] / [SKIP] / [DO] / [WARN] / [ERR] so you can see what changed.
#
# Optional env knobs (export before running):
#   REPO_URL       (default https://github.com/KaushalJainAI/Career_Navigator.git)
#   APP_DIR        (default /opt/career-navigator)
#   PUBLIC_HOST    (default career.kaushaljain.com)
#   API_BASE       (default https://career.kaushaljain.com/api/v1)
#   CF_CERT        (path to Cloudflare Origin Cert PEM; if present, HTTPS is enabled)
#   CF_KEY         (path to Cloudflare Origin private key)
#   ENV_OVERRIDES  (path to a file of KEY=value lines that get appended to .env;
#                   useful for API keys you don't want regenerated)

set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/KaushalJainAI/Career_Navigator.git}"
APP_DIR="${APP_DIR:-/opt/career-navigator}"
PUBLIC_HOST="${PUBLIC_HOST:-career.kaushaljain.com}"
API_BASE="${API_BASE:-https://${PUBLIC_HOST}/api/v1}"
CF_CERT="${CF_CERT:-/tmp/cn-cf-cert.pem}"
CF_KEY="${CF_KEY:-/tmp/cn-cf-key.pem}"
ENV_OVERRIDES="${ENV_OVERRIDES:-/tmp/cn-env-overrides.txt}"

# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------
say()  { printf "\033[36m[..] %s\033[0m\n"  "$*"; }
do_()  { printf "\033[33m[DO] %s\033[0m\n" "$*"; }
done_(){ printf "\033[32m[OK] %s\033[0m\n" "$*"; }
skip() { printf "\033[34m[SK] %s\033[0m\n" "$*"; }
warn() { printf "\033[33m[!!] %s\033[0m\n" "$*"; }
err()  { printf "\033[31m[ER] %s\033[0m\n" "$*"; exit 1; }
hr()   { printf "\033[37m%s\033[0m\n" "----------------------------------------"; }

# ---------------------------------------------------------------------------
# Status panel — what's already done on this box?
# ---------------------------------------------------------------------------
status_panel() {
  hr
  printf "\033[1mPRE-FLIGHT STATUS\033[0m\n"
  hr
  local rows=(
    "OS|$(grep -E '^PRETTY_NAME' /etc/os-release 2>/dev/null | cut -d= -f2 | tr -d '\"')"
    "user|$(whoami)"
    "node|$(node --version 2>/dev/null || echo 'not installed')"
    "git|$(git --version 2>/dev/null | awk '{print $3}' || echo 'not installed')"
    "nginx|$(nginx -v 2>&1 | awk -F/ '{print $2}' || echo 'not installed')"
    "redis|$(systemctl is-active redis6 2>/dev/null || echo 'not installed')"
    "sqlite|$(sqlite3 --version 2>/dev/null | awk '{print $1}' || echo 'not installed')"
    "claude|$(claude --version 2>/dev/null || echo 'not installed')"
    "code at ${APP_DIR}|$([ -d ${APP_DIR}/.git ] && echo present || echo missing)"
    ".env|$([ -f ${APP_DIR}/backend/.env ] && echo present || echo missing)"
    "venv|$([ -d ${APP_DIR}/backend/.venv ] && echo present || echo missing)"
    "db.sqlite3|$([ -f ${APP_DIR}/backend/db.sqlite3 ] && echo present || echo missing)"
    "frontend dist|$([ -d ${APP_DIR}/frontend/dist ] && echo present || echo missing)"
    "cn-backend.service|$(systemctl is-active cn-backend 2>/dev/null || echo inactive)"
    "cn-asgi.service|$(systemctl is-active cn-asgi 2>/dev/null || echo inactive)"
    "cn-celery.service|$(systemctl is-active cn-celery 2>/dev/null || echo inactive)"
    "nginx site|$([ -f /etc/nginx/conf.d/career-navigator.conf ] && echo present || echo missing)"
    "CF origin cert|$([ -f /etc/ssl/cloudflare/${PUBLIC_HOST}.pem ] && echo installed || echo missing)"
  )
  for row in "${rows[@]}"; do
    printf "  %-22s %s\n" "${row%%|*}" "${row##*|}"
  done
  hr
}

status_panel

# ---------------------------------------------------------------------------
# 1. System packages
# ---------------------------------------------------------------------------
say "Phase 1 — system packages"

PKGS=(git python3.11 python3.11-pip python3.11-devel sqlite redis6 nginx gcc nodejs npm tmux jq)
NEEDED=()
for p in "${PKGS[@]}"; do
  if ! rpm -q "$p" >/dev/null 2>&1; then NEEDED+=("$p"); fi
done

if [ ${#NEEDED[@]} -eq 0 ]; then
  skip "all packages already installed"
else
  do_ "installing: ${NEEDED[*]}"
  sudo dnf install -y "${NEEDED[@]}"
fi

# Try to make sure python3.11 actually exists; fall back gracefully.
if ! command -v python3.11 >/dev/null 2>&1; then
  warn "python3.11 not available, using python3"
  PY=python3
else
  PY=python3.11
fi

for svc in redis6 nginx; do
  if systemctl is-enabled "$svc" >/dev/null 2>&1; then
    skip "$svc already enabled"
  else
    do_ "enabling $svc"
    sudo systemctl enable --now "$svc"
  fi
done

# ---------------------------------------------------------------------------
# 2. App directory + code
# ---------------------------------------------------------------------------
say "Phase 2 — application directory + code"

if [ ! -d "$APP_DIR" ]; then
  do_ "creating $APP_DIR"
  sudo mkdir -p "$APP_DIR"
  sudo chown "$(whoami)":"$(whoami)" "$APP_DIR"
fi

if [ -d "$APP_DIR/.git" ]; then
  skip "repo already cloned at $APP_DIR; pulling latest"
  cd "$APP_DIR"
  git pull --ff-only || warn "git pull failed (continuing with current code)"
elif [ -d /tmp/cn-staging ] && [ "$(ls -A /tmp/cn-staging 2>/dev/null)" ]; then
  do_ "moving code from /tmp/cn-staging (scp'd from laptop) → $APP_DIR"
  shopt -s dotglob
  mv /tmp/cn-staging/* "$APP_DIR/"
  shopt -u dotglob
  cd "$APP_DIR"
else
  do_ "cloning $REPO_URL → $APP_DIR"
  cd "$APP_DIR"
  git clone "$REPO_URL" .
fi

mkdir -p "$APP_DIR/backups"

# ---------------------------------------------------------------------------
# 3. .env (generate prod env if missing)
# ---------------------------------------------------------------------------
say "Phase 3 — backend .env"

ENV_PATH="$APP_DIR/backend/.env"
if [ -f "$ENV_PATH" ] && grep -q '^DJANGO_SETTINGS_MODULE=config.settings.prod' "$ENV_PATH"; then
  skip ".env already has prod settings"
else
  do_ "generating $ENV_PATH"
  SECRET_KEY=$($PY -c "import secrets; print(secrets.token_urlsafe(50))")
  CRED_KEY=$($PY -c "import secrets; print(secrets.token_urlsafe(32))")
  cat > "$ENV_PATH" <<EOF
DJANGO_SETTINGS_MODULE=config.settings.prod
SECRET_KEY=${SECRET_KEY}
DEBUG=False
ALLOWED_HOSTS=${PUBLIC_HOST},$(hostname -f),$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo 127.0.0.1)
CORS_ALLOWED_ORIGINS=https://${PUBLIC_HOST}
FRONTEND_URL=https://${PUBLIC_HOST}
SECURE_SSL_REDIRECT=False
SECURE_HSTS_SECONDS=0
DATABASE_URL=
SQLITE_PATH=${APP_DIR}/backend/db.sqlite3
REDIS_URL=redis://127.0.0.1:6379/0
USE_REDIS_CHANNEL_LAYER=True
CREDENTIAL_ENCRYPTION_KEY=${CRED_KEY}
NVIDIA_API_KEY=
ADZUNA_APP_ID=
ADZUNA_APP_KEY=
GREENHOUSE_TOKENS=
LEVER_TOKENS=
JOOBLE_API_KEY=
JSEARCH_RAPIDAPI_KEY=
RESEND_API_KEY=
VAPID_PUBLIC_KEY=
VAPID_PRIVATE_KEY=
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
GOOGLE_OAUTH_REDIRECT_URI=https://${PUBLIC_HOST}/auth/google/callback
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
EOF
  chmod 600 "$ENV_PATH"
fi

# Append/override values from /tmp/cn-env-overrides.txt if present
if [ -f "$ENV_OVERRIDES" ]; then
  do_ "applying overrides from $ENV_OVERRIDES"
  while IFS= read -r line; do
    [ -z "$line" ] || [ "${line:0:1}" = "#" ] && continue
    key="${line%%=*}"
    if grep -q "^${key}=" "$ENV_PATH"; then
      # Replace existing
      sed -i "s|^${key}=.*|${line}|" "$ENV_PATH"
    else
      echo "$line" >> "$ENV_PATH"
    fi
  done < "$ENV_OVERRIDES"
fi

# ---------------------------------------------------------------------------
# 4. Python venv + deps + migrations
# ---------------------------------------------------------------------------
say "Phase 4 — Python venv + deps + migrations"

cd "$APP_DIR/backend"
if [ -d .venv ]; then
  skip "venv exists"
else
  do_ "creating venv"
  $PY -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --quiet --upgrade pip
do_ "pip install -r requirements.txt (this can take a few minutes the first time)"
pip install --quiet -r requirements.txt
pip install --quiet gunicorn

do_ "applying migrations"
python manage.py migrate --noinput
do_ "collecting static"
python manage.py collectstatic --noinput

# ---------------------------------------------------------------------------
# 5. Frontend build
# ---------------------------------------------------------------------------
say "Phase 5 — frontend build"

cd "$APP_DIR/frontend"
if [ -d node_modules ]; then
  skip "node_modules exists; running npm ci anyway to lock versions"
fi
npm ci --silent || npm install --silent
VITE_API_BASE="$API_BASE" npm run build

# ---------------------------------------------------------------------------
# 6. systemd units
# ---------------------------------------------------------------------------
say "Phase 6 — systemd units"

USER_NAME="$(whoami)"

write_unit() {
  local path="$1"
  local body="$2"
  if [ -f "$path" ] && [ "$(sudo cat "$path")" = "$body" ]; then
    skip "$path unchanged"
  else
    do_ "writing $path"
    echo "$body" | sudo tee "$path" > /dev/null
  fi
}

write_unit /etc/systemd/system/cn-backend.service "$(cat <<EOF
[Unit]
Description=Career Navigator backend (gunicorn)
After=network.target redis6.service

[Service]
User=${USER_NAME}
WorkingDirectory=${APP_DIR}/backend
EnvironmentFile=${APP_DIR}/backend/.env
ExecStart=${APP_DIR}/backend/.venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 --access-logfile - --error-logfile - config.wsgi:application
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
)"

write_unit /etc/systemd/system/cn-asgi.service "$(cat <<EOF
[Unit]
Description=Career Navigator ASGI (daphne)
After=network.target

[Service]
User=${USER_NAME}
WorkingDirectory=${APP_DIR}/backend
EnvironmentFile=${APP_DIR}/backend/.env
ExecStart=${APP_DIR}/backend/.venv/bin/daphne -b 127.0.0.1 -p 8001 config.asgi:application
Restart=always

[Install]
WantedBy=multi-user.target
EOF
)"

write_unit /etc/systemd/system/cn-celery.service "$(cat <<EOF
[Unit]
Description=Career Navigator Celery worker
After=network.target redis6.service

[Service]
User=${USER_NAME}
WorkingDirectory=${APP_DIR}/backend
EnvironmentFile=${APP_DIR}/backend/.env
ExecStart=${APP_DIR}/backend/.venv/bin/celery -A config worker -B -l info -S django
Restart=always

[Install]
WantedBy=multi-user.target
EOF
)"

sudo systemctl daemon-reload
for svc in cn-backend cn-asgi cn-celery; do
  if systemctl is-enabled "$svc" >/dev/null 2>&1; then
    sudo systemctl restart "$svc" || warn "restart of $svc failed (check journalctl -u $svc)"
  else
    do_ "enabling+starting $svc"
    sudo systemctl enable --now "$svc"
  fi
done

# ---------------------------------------------------------------------------
# 7. Nginx config (HTTP first; upgrades to HTTPS in Phase 8 if cert present)
# ---------------------------------------------------------------------------
say "Phase 7 — nginx (HTTP)"

NGINX_CONF=/etc/nginx/conf.d/career-navigator.conf

HTTP_BLOCK="$(cat <<EOF
server {
    listen 80 default_server;
    server_name ${PUBLIC_HOST} _;
    client_max_body_size 25M;

    root ${APP_DIR}/frontend/dist;
    index index.html;

    location / { try_files \$uri /index.html; }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /admin/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static/ { alias ${APP_DIR}/backend/staticfiles/; }

    location /ws/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
    }
}
EOF
)"

if [ -f "$CF_CERT" ] && [ -f "$CF_KEY" ]; then
  say "Cloudflare Origin Cert detected — building HTTPS nginx config"
  sudo mkdir -p /etc/ssl/cloudflare
  sudo cp "$CF_CERT" "/etc/ssl/cloudflare/${PUBLIC_HOST}.pem"
  sudo cp "$CF_KEY"  "/etc/ssl/cloudflare/${PUBLIC_HOST}.key"
  sudo chmod 644 "/etc/ssl/cloudflare/${PUBLIC_HOST}.pem"
  sudo chmod 600 "/etc/ssl/cloudflare/${PUBLIC_HOST}.key"

  CF_REAL_IPS="$(cat <<'EOF'
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
real_ip_header CF-Connecting-IP;
EOF
)"

  FULL_BLOCK="$(cat <<EOF
${CF_REAL_IPS}

server {
    listen 80 default_server;
    server_name ${PUBLIC_HOST} _;
    return 301 https://${PUBLIC_HOST}\$request_uri;
}

server {
    listen 443 ssl http2 default_server;
    server_name ${PUBLIC_HOST};
    client_max_body_size 25M;

    ssl_certificate     /etc/ssl/cloudflare/${PUBLIC_HOST}.pem;
    ssl_certificate_key /etc/ssl/cloudflare/${PUBLIC_HOST}.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    root ${APP_DIR}/frontend/dist;
    index index.html;
    location / { try_files \$uri /index.html; }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
    location /admin/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-Proto https;
    }
    location /static/ { alias ${APP_DIR}/backend/staticfiles/; }
    location /ws/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-Proto https;
    }
}
EOF
)"
  echo "$FULL_BLOCK" | sudo tee "$NGINX_CONF" > /dev/null

  # Now that HTTPS is in place, flip SECURE_SSL_REDIRECT on in .env and restart Django.
  if grep -q "^SECURE_SSL_REDIRECT=False" "$ENV_PATH"; then
    sed -i 's|^SECURE_SSL_REDIRECT=False|SECURE_SSL_REDIRECT=True|' "$ENV_PATH"
    sed -i 's|^SECURE_HSTS_SECONDS=0|SECURE_HSTS_SECONDS=31536000|' "$ENV_PATH"
    sudo systemctl restart cn-backend cn-asgi
  fi
  done_ "HTTPS configured at https://${PUBLIC_HOST}"
else
  warn "no Cloudflare Origin Cert at $CF_CERT / $CF_KEY — writing HTTP-only nginx"
  warn "after generating the cert in Cloudflare dashboard, scp them up and re-run this script"
  echo "$HTTP_BLOCK" | sudo tee "$NGINX_CONF" > /dev/null
fi

# SELinux: allow nginx to proxy to localhost backends
if command -v getsebool >/dev/null 2>&1; then
  if [ "$(getsebool httpd_can_network_connect 2>/dev/null | awk '{print $3}')" != "on" ]; then
    do_ "setting SELinux httpd_can_network_connect on"
    sudo setsebool -P httpd_can_network_connect 1 || warn "setsebool failed (may not have SELinux)"
  fi
fi

sudo nginx -t
sudo systemctl reload nginx
done_ "nginx reloaded"

# ---------------------------------------------------------------------------
# 8. Claude Code (install only; auth is interactive — you do that)
# ---------------------------------------------------------------------------
say "Phase 8 — Claude Code"

if command -v claude >/dev/null 2>&1; then
  skip "claude already installed ($(claude --version 2>/dev/null))"
else
  do_ "npm install -g @anthropic-ai/claude-code"
  sudo npm install -g @anthropic-ai/claude-code
fi

# ---------------------------------------------------------------------------
# 9. tmux session for Claude (so it survives SSH disconnect)
# ---------------------------------------------------------------------------
say "Phase 9 — tmux session"

if tmux has-session -t claude 2>/dev/null; then
  skip "tmux 'claude' session already running (tmux attach -t claude)"
else
  do_ "creating detached tmux session 'claude' in $APP_DIR"
  tmux new-session -d -s claude -c "$APP_DIR" 'claude || bash'
fi

# ---------------------------------------------------------------------------
# 10. Health checks
# ---------------------------------------------------------------------------
hr
say "Health checks"
hr

echo -n "  cn-backend ............ "; systemctl is-active cn-backend || true
echo -n "  cn-asgi ............... "; systemctl is-active cn-asgi || true
echo -n "  cn-celery ............. "; systemctl is-active cn-celery || true
echo -n "  nginx ................. "; systemctl is-active nginx || true
echo -n "  redis6 ................ "; systemctl is-active redis6 || true
echo -n "  local backend ......... "
curl -sf -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/api/v1/auth/me/ || echo "down"
echo -n "  local nginx ........... "
curl -sfk -o /dev/null -w "%{http_code}\n" http://127.0.0.1/ || echo "down"
if [ -f /etc/ssl/cloudflare/${PUBLIC_HOST}.pem ]; then
  echo -n "  local HTTPS ........... "
  curl -sfk -o /dev/null -w "%{http_code}\n" https://127.0.0.1/ || echo "down"
fi

hr
done_ "bootstrap complete"
hr
cat <<EOF

NEXT STEPS YOU MUST DO MANUALLY
------------------------------------
1. Cloudflare Origin Certificate (only if [SK]/[WARN] said no cert):
     a. Dashboard → kaushaljain.com → SSL/TLS → Origin Server → Create Certificate
     b. Save cert PEM block to your laptop as cloudflare-cert.pem
     c. Save private key PEM block as cloudflare-key.pem
     d. From your laptop, scp them up:
          scp -i "my-key.pem" cloudflare-cert.pem ec2-user@<host>:/tmp/cn-cf-cert.pem
          scp -i "my-key.pem" cloudflare-key.pem  ec2-user@<host>:/tmp/cn-cf-key.pem
     e. Re-run this script — it will detect the certs and configure HTTPS.
     f. In Cloudflare → SSL/TLS → Overview, set mode to Full (strict).

2. Claude Code login (interactive — only you can do this):
     tmux attach -t claude
     /login              # paste the code from your browser
     /exit               # leave the REPL
     # Detach without killing: Ctrl+B then D

3. AWS Security Group:
     Make sure ports 80 and 443 are open inbound (0.0.0.0/0).
     Port 22 should be restricted to your laptop's IP.

App URL (once Cloudflare proxy + cert are in place):
   https://${PUBLIC_HOST}/

To redeploy after pushing code changes:
   cd ${APP_DIR} && bash scripts/deploy.sh
EOF
