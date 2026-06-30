"""Production settings — used on the EC2 deployment.

Reads sensitive values from the environment (loaded via the systemd EnvironmentFile
pointing at /opt/career-navigator/backend/.env). Defaults to SQLite when
DATABASE_URL is empty — the SQLite file path is taken from SQLITE_PATH."""

import os

from .base import *  # noqa: F401,F403

DEBUG = False

# Serve collected static (admin, DRF, Swagger) directly from the ASGI process
# behind nginx — no separate static host needed. WhiteNoise sits right after the
# security middleware. nginx proxies /static/ to this process.
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')  # noqa: F405
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}

# Hosts/CORS come from .env. ALLOWED_HOSTS is already extended from
# the ALLOWED_HOSTS env var in base.py; we just enforce that prod sets it.
if not os.environ.get('ALLOWED_HOSTS'):
    raise RuntimeError(
        'config.settings.prod requires ALLOWED_HOSTS env var to be set.'
    )

# Security hardening for HTTP-only behind nginx (terminating TLS later moves
# these to True). Cookies stay session-bound so the JWT in the auth cookie
# can't be exfiltrated by client-side JS.
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# If/when you put nginx behind a Let's Encrypt cert, flip these via env.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'False') == 'True'
SESSION_COOKIE_SECURE = SECURE_SSL_REDIRECT
CSRF_COOKIE_SECURE = SECURE_SSL_REDIRECT
SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
SECURE_HSTS_PRELOAD = SECURE_HSTS_SECONDS > 0

# Behind a reverse proxy, prefer X-Forwarded-For for client IP attribution.
USE_X_FORWARDED_HOST = True

# Logging: send WARNING+ to /var/log if writable, fall back to stdout (captured
# by journalctl when run under systemd).
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'standard'},
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {
        'django.request': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
        'django.db.backends': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
    },
}
