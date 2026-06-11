import httpx
import pytest

from ingestion.adapters.base import AdapterContext
from ingestion.adapters.lever import LeverAdapter
from ingestion.services import run_adapter, upsert_postings
from jobs.models import Company, JobPosting, Source

pytestmark = pytest.mark.django_db


def test_upsert_postings_creates_and_updates():
    source = Source.objects.create(name='adzuna', kind='aggregator')
    postings = [
        {
            'external_id': 'abc',
            'title': 'Backend Engineer',
            'description': 'Build stuff',
            'location': 'Remote',
            'remote': True,
            'company': {'name': 'Acme', 'domain': 'acme.com', 'ats_type': 'other'},
            'raw': {},
        },
        {
            'external_id': '',  # invalid
            'title': '',
            'company': {'name': 'X'},
        },
    ]
    stats = upsert_postings(source, postings)
    assert stats == {'created': 1, 'updated': 0, 'skipped': 1}
    assert JobPosting.objects.count() == 1

    # rerun → update
    postings[0]['title'] = 'Senior Backend Engineer'
    stats = upsert_postings(source, postings)
    assert stats['updated'] == 1
    assert JobPosting.objects.get(external_id='abc').title == 'Senior Backend Engineer'


def test_run_adapter_integration_fetch_to_db():
    """Full chain: HTTP response → adapter normalise → upsert → IngestionRun/JobPosting rows."""
    source = Source.objects.create(name='lever', kind='ats_public')
    board = [
        {
            'id': 'lv-9',
            'text': 'Backend Engineer',
            'categories': {'location': 'Remote — India'},
            'descriptionPlain': 'Build APIs.',
            'salaryRange': {'min': 2400000, 'max': 3600000, 'currency': 'INR'},
            'hostedUrl': 'https://jobs.lever.co/acme/lv-9',
            'createdAt': 1764547200000,
        },
        {'id': '', 'text': ''},  # invalid row — must be skipped, not crash the run
    ]
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=board))
    adapter = LeverAdapter(tokens=['acme'], transport=transport)

    run = run_adapter(source, adapter, AdapterContext())

    assert run.status == 'success'
    assert run.stats == {'created': 1, 'updated': 0, 'skipped': 1}
    posting = JobPosting.objects.get(source=source, external_id='lv-9')
    assert posting.title == 'Backend Engineer'
    assert posting.salary_min == 2400000
    assert posting.company == Company.objects.get(name='Acme')

    # rerun is idempotent — same row updates, nothing duplicates
    rerun = run_adapter(source, adapter, AdapterContext())
    assert rerun.stats == {'created': 0, 'updated': 1, 'skipped': 1}
    assert JobPosting.objects.count() == 1
