"""Live smoke for keyless public-board adapters (Greenhouse, Lever).

Hits real endpoints — run manually, never from the test suite:
    cd backend && python scripts/smoke_adapters.py [greenhouse_token] [lever_token]
Defaults to well-known public boards (stripe, netflix).
"""
import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
os.environ.setdefault('CREDENTIAL_ENCRYPTION_KEY', 'smoke-only-not-a-real-key')
django.setup()

from ingestion.adapters.base import AdapterContext  # noqa: E402
from ingestion.adapters.greenhouse import GreenhouseAdapter  # noqa: E402
from ingestion.adapters.lever import LeverAdapter  # noqa: E402

gh_token = sys.argv[1] if len(sys.argv) > 1 else 'stripe'
lv_token = sys.argv[2] if len(sys.argv) > 2 else 'netflix'

failures = 0
for label, adapter in (
    (f'greenhouse/{gh_token}', GreenhouseAdapter(tokens=[gh_token])),
    (f'lever/{lv_token}', LeverAdapter(tokens=[lv_token])),
):
    postings = adapter.run(AdapterContext(max_pages=1))
    valid = [p for p in postings if p['external_id'] and p['title']]
    sample = valid[0]['title'][:60] if valid else 'NONE'
    print(f'{label}: {len(postings)} postings, {len(valid)} contract-valid, sample: {sample}')
    if not valid:
        failures += 1

sys.exit(1 if failures else 0)
