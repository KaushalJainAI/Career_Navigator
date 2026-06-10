import json

import httpx

from ingestion.adapters.adzuna import AdzunaAdapter
from ingestion.adapters.base import AdapterContext
from ingestion.adapters.greenhouse import GreenhouseAdapter
from ingestion.adapters.jooble import JoobleAdapter
from ingestion.adapters.jsearch import JSearchAdapter
from ingestion.adapters.lever import LeverAdapter


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


def test_jooble_normalise_basic():
    row = {
        'id': 987,
        'title': 'Data Engineer — Remote',
        'snippet': 'Build pipelines.',
        'location': 'Bengaluru, India',
        'company': 'Acme Data',
        'link': 'https://jooble.org/jdp/987',
        'updated': '2026-06-01T08:00:00Z',
    }
    out = JoobleAdapter._normalise(row)
    assert out['external_id'] == '987'
    assert out['title'] == 'Data Engineer — Remote'
    assert out['remote'] is True
    assert out['company']['name'] == 'Acme Data'
    assert out['apply_url'] == 'https://jooble.org/jdp/987'
    assert out['posted_at'] is not None


def test_jooble_fetch_paginates_and_stops_on_empty():
    pages = {
        1: {'totalCount': 2, 'jobs': [{'id': 1, 'title': 'A'}, {'id': 2, 'title': 'B'}]},
        2: {'totalCount': 2, 'jobs': []},
    }
    seen_pages = []

    def handler(request):
        body = json.loads(request.content)
        seen_pages.append(body['page'])
        return httpx.Response(200, json=pages[body['page']])

    adapter = JoobleAdapter(api_key='k', transport=httpx.MockTransport(handler))
    out = adapter.run(AdapterContext(query='python', max_pages=5))
    assert [p['external_id'] for p in out] == ['1', '2']
    assert seen_pages == [1, 2]


def test_jooble_without_key_yields_nothing():
    assert JoobleAdapter(api_key='').run() == []


def test_jsearch_normalise_basic():
    row = {
        'job_id': 'abc123',
        'job_title': 'Platform Engineer',
        'employer_name': 'Globex',
        'employer_website': 'https://globex.com/',
        'job_description': 'Run the platform.',
        'job_city': 'Austin',
        'job_state': 'TX',
        'job_country': 'US',
        'job_is_remote': True,
        'job_min_salary': 140000,
        'job_max_salary': 180000,
        'job_salary_currency': 'USD',
        'job_apply_link': 'https://globex.com/careers/abc123',
        'job_posted_at_datetime_utc': '2026-06-02T00:00:00Z',
    }
    out = JSearchAdapter._normalise(row)
    assert out['external_id'] == 'abc123'
    assert out['location'] == 'Austin, TX, US'
    assert out['remote'] is True
    assert out['salary_min'] == 140000
    assert out['salary_max'] == 180000
    assert out['company'] == {'name': 'Globex', 'domain': 'globex.com', 'ats_type': 'other'}


def test_jsearch_fetch_sends_rapidapi_headers():
    captured = {}

    def handler(request):
        captured['key'] = request.headers.get('X-RapidAPI-Key')
        captured['host'] = request.headers.get('X-RapidAPI-Host')
        return httpx.Response(200, json={'data': [{'job_id': 'j1', 'job_title': 'Dev'}]})

    adapter = JSearchAdapter(api_key='rk', transport=httpx.MockTransport(handler))
    out = adapter.run(AdapterContext(query='django', max_pages=1))
    assert captured == {'key': 'rk', 'host': 'jsearch.p.rapidapi.com'}
    assert [p['external_id'] for p in out] == ['j1']


def test_lever_normalise_basic():
    row = {
        'id': 'lv-1',
        'text': 'Staff Engineer',
        'categories': {'location': 'Remote — Europe', 'team': 'Infra'},
        'descriptionPlain': 'Own infra.',
        'workplaceType': 'remote',
        'salaryRange': {'min': 90000, 'max': 120000, 'currency': 'EUR'},
        'hostedUrl': 'https://jobs.lever.co/acme/lv-1',
        'applyUrl': 'https://jobs.lever.co/acme/lv-1/apply',
        'createdAt': 1764547200000,
    }
    out = LeverAdapter._normalise(row, 'acme-co')
    assert out['external_id'] == 'lv-1'
    assert out['title'] == 'Staff Engineer'
    assert out['remote'] is True
    assert out['salary_min'] == 90000
    assert out['salary_currency'] == 'EUR'
    assert out['apply_url'] == 'https://jobs.lever.co/acme/lv-1/apply'
    assert out['company'] == {'name': 'Acme Co', 'domain': '', 'ats_type': 'lever'}
    assert out['posted_at'].year == 2025


def test_lever_fetch_iterates_tokens_and_skips_failures():
    def handler(request):
        if 'badco' in str(request.url):
            return httpx.Response(404)
        return httpx.Response(200, json=[{'id': 'p1', 'text': 'Eng'}])

    adapter = LeverAdapter(tokens=['badco', 'goodco'], transport=httpx.MockTransport(handler))
    out = adapter.run()
    assert [p['external_id'] for p in out] == ['p1']
    assert out[0]['company']['name'] == 'Goodco'
