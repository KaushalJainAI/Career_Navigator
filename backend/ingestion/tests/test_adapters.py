from ingestion.adapters.adzuna import AdzunaAdapter
from ingestion.adapters.greenhouse import GreenhouseAdapter


def test_adzuna_normalise_basic():
    row = {
        'id': 12345,
        'title': 'Senior Engineer (Remote)',
        'description': '...',
        'location': {'display_name': 'New York, NY'},
        'company': {'display_name': 'Acme'},
        'salary_min': 100000,
        'salary_max': 150000,
        'salary_currency': 'USD',
        'redirect_url': 'https://example.com/apply',
        'created': '2026-05-19T12:34:56Z',
    }
    out = AdzunaAdapter._normalise(row)
    assert out['external_id'] == '12345'
    assert out['title'] == 'Senior Engineer (Remote)'
    assert out['remote'] is True
    assert out['salary_min'] == 100000
    assert out['company']['name'] == 'Acme'


def test_greenhouse_normalise_basic():
    row = {
        'id': 42,
        'title': 'Backend Engineer',
        'content': 'desc',
        'location': {'name': 'Remote — US'},
        'absolute_url': 'https://boards.greenhouse.io/acme/jobs/42',
        'updated_at': '2026-04-01T10:00:00Z',
    }
    out = GreenhouseAdapter._normalise(row, 'acme')
    assert out['external_id'] == '42'
    assert out['title'] == 'Backend Engineer'
    assert out['remote'] is True
    assert out['company']['ats_type'] == 'greenhouse'
    assert out['company']['name'] == 'Acme'
