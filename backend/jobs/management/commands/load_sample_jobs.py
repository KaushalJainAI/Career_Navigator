"""Load a small set of SAMPLE job postings for local development and demos.

Real deployments get jobs from `POST /api/v1/jobs/refresh/` (public boards and
job APIs). Use this only when you're offline or behind a firewall. The
postings are stored under the source "sample" so they're easy to spot and
remove with --clear.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from ingestion.adapters.base import make_posting
from ingestion.services import upsert_postings
from jobs.models import JobPosting, Source

FIXTURE = Path(__file__).resolve().parents[2] / 'fixtures' / 'sample_jobs.json'


class Command(BaseCommand):
    help = 'Load sample job postings (source="sample") for local development.'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Delete sample jobs instead of loading them.')

    def handle(self, *args, **opts):
        source, _ = Source.objects.get_or_create(name='sample', defaults={'kind': 'scraper'})
        if opts['clear']:
            n, _ = JobPosting.objects.filter(source=source).delete()
            self.stdout.write(f'Deleted {n} sample rows.')
            return
        rows = json.loads(FIXTURE.read_text())
        postings = [make_posting(external_id=r['external_id'], title=r['title'], description=r['description'],
                                 location=r['location'], remote=r['remote'], apply_url=r['apply_url'],
                                 company_name=r['company'], raw={'sample': True}) for r in rows]
        stats = upsert_postings(source, postings)
        self.stdout.write(self.style.SUCCESS(f'Sample jobs: {stats}'))
