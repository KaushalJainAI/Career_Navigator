#!/usr/bin/env bash
# deploy.sh — pull latest code, install deps, migrate, rebuild frontend, restart services.
# Run on the EC2 box from /opt/career-navigator:
#
#   bash scripts/deploy.sh
#
# Safe to re-run. Fails fast on any error.

set -euo pipefail

ROOT="/opt/career-navigator"
cd "$ROOT"

echo "==> Pulling latest from origin..."
git pull --ff-only

echo "==> Backend: pip install + migrate + collectstatic"
cd "$ROOT/backend"
source .venv/bin/activate
pip install -q -r requirements.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput

echo "==> Frontend: build"
cd "$ROOT/frontend"
npm ci
VITE_API_BASE="${VITE_API_BASE:-http://ec2-13-207-61-191.ap-south-1.compute.amazonaws.com/api/v1}" \
  npm run build

echo "==> Restarting services"
sudo systemctl restart cn-backend cn-asgi cn-celery
sudo systemctl reload nginx

echo "==> Health check"
sleep 2
curl -sf -o /dev/null -w "backend status: %{http_code}\n" http://127.0.0.1:8000/api/v1/auth/me/ \
    || echo "WARN: backend health check failed — check 'journalctl -u cn-backend -n 50'"
curl -sf -o /dev/null -w "nginx status:   %{http_code}\n" http://127.0.0.1/ \
    || echo "WARN: nginx health check failed"

echo "==> Done. db.sqlite3 size: $(du -h "$ROOT/backend/db.sqlite3" 2>/dev/null | cut -f1 || echo '<missing>')"
