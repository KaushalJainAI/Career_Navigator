from datetime import timedelta

import httpx
import pytest
from django.utils import timezone

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


def _posting(external_id, *, title='Backend Engineer', description='Build services.',
             salary_min=120000, salary_max=160000, company='Acme'):
    return {
        'external_id': external_id,
        'title': title,
        'description': description,
        'salary_min': salary_min,
        'salary_max': salary_max,
        'company': {'name': company, 'domain': '', 'ats_type': 'other'},
        'raw': {},
    }


def test_upsert_tracks_liveness_and_fingerprint():
    source = Source.objects.create(name='adzuna', kind='aggregator')
    upsert_postings(source, [_posting('a')])
    job = JobPosting.objects.get(external_id='a')
    assert job.content_fingerprint
    assert job.first_seen_at is not None
    assert job.last_seen_at is not None
    assert job.repost_count == 0


def test_unchanged_copy_keeps_first_seen_but_advances_last_seen():
    source = Source.objects.create(name='adzuna', kind='aggregator')
    upsert_postings(source, [_posting('a')])
    job = JobPosting.objects.get(external_id='a')
    original_first_seen = job.first_seen_at

    # force a later run by ageing first_seen into the past
    JobPosting.objects.filter(pk=job.pk).update(
        first_seen_at=original_first_seen - timedelta(days=50),
    )
    upsert_postings(source, [_posting('a')])  # identical copy
    job.refresh_from_db()
    # same copy → first_seen preserved, so staleness accrues and risk rises
    assert job.first_seen_at == original_first_seen - timedelta(days=50)
    assert job.ghost_risk >= 25
    assert any('live for' in r for r in job.ghost_reasons)


def test_changed_copy_resets_first_seen():
    source = Source.objects.create(name='adzuna', kind='aggregator')
    upsert_postings(source, [_posting('a', description='Original copy.')])
    job = JobPosting.objects.get(external_id='a')
    JobPosting.objects.filter(pk=job.pk).update(
        first_seen_at=job.first_seen_at - timedelta(days=50),
    )
    upsert_postings(source, [_posting('a', description='Rewritten fresh copy.')])
    job.refresh_from_db()
    # new copy → first_seen reset to now, staleness reason gone
    assert (timezone.now() - job.first_seen_at) < timedelta(days=1)
    assert not any('live for' in r for r in job.ghost_reasons)


def test_repost_under_new_id_raises_ghost_risk():
    source_a = Source.objects.create(name='greenhouse', kind='ats_public')
    source_b = Source.objects.create(name='lever', kind='ats_public')
    # identical copy, same company, two different (source, external_id) pairs,
    # neither with a salary range → repost signal + missing-salary signal
    payload = _posting('orig', salary_min=None, salary_max=None)
    upsert_postings(source_a, [payload])
    upsert_postings(source_b, [dict(payload, external_id='repost')])

    repost = JobPosting.objects.get(external_id='repost')
    assert repost.repost_count >= 1
    assert repost.ghost_risk >= 50  # 30 repost + 20 missing salary
    assert any('reposted' in r.lower() for r in repost.ghost_reasons)
