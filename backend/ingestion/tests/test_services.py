import pytest

from ingestion.services import upsert_postings
from jobs.models import JobPosting, Source

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
