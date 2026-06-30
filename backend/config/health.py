"""Liveness/readiness probe for load balancers and compose healthchecks.

Mirrors AIAAS's `GET /api/health/`: returns 200 with a small JSON body when the
process is up and the default DB connection answers a trivial query, 503 when the
DB is unreachable. No auth — the reverse proxy/ALB hits this before routing.
"""

from django.db import connection
from django.http import JsonResponse


def health(_request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        db_ok = True
    except Exception:  # noqa: BLE001 — any DB error means not-ready
        db_ok = False

    status = 200 if db_ok else 503
    return JsonResponse({'status': 'ok' if db_ok else 'degraded', 'database': db_ok}, status=status)
