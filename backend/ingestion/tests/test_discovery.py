import json

import httpx
import pytest

from ingestion.adapters.base import AdapterContext, BaseAdapter, make_posting
from ingestion.adapters.remotive import RemotiveAdapter
from ingestion.discovery import Plan, discover_for_candidate, relevance_filter
from ingestion.url_import import detect, fetch_job_from_url
from jobs.models import JobPosting
from matching.fit import Candidate

pytestmark = pytest.mark.django_db


class StaticAdapter(BaseAdapter):
    def __init__(self, rows):
        super().__init__()
        self.rows = rows

    def fetch(self, ctx):
        yield from self.rows


class Boom(BaseAdapter):
    def fetch(self, ctx):
        raise RuntimeError('down')


def _p(i, title, company='Acme'):
    return make_posting(external_id=i, title=title, description='Python and Django', company_name=company)


def test_discovery_keeps_relevant_roles_and_survives_failures():
    cand = Candidate(titles=['Backend Engineer'], skills={'python': 'Python'})
    plans = [
        Plan('greenhouse', 'ats_public', StaticAdapter([_p(1, 'Senior Backend Engineer'),
                                                        _p(2, 'Account Executive')]), AdapterContext()),
        Plan('remotive', 'aggregator', Boom(), AdapterContext()),
    ]
    out = discover_for_candidate(cand, plans=plans)
    assert out['new_jobs'] == 1
    assert {s['source']: s['ok'] for s in out['sources']} == {'greenhouse': True, 'remotive': False}
    job = JobPosting.objects.get()
    assert job.title == 'Senior Backend Engineer'
    assert job.skills.get('Python') == 1 and 'Django' in job.skills


def test_relevance_filter_respects_excluded_companies():
    keep = relevance_filter(Candidate(titles=['Data Engineer'], exclude_companies=['evilcorp']))
    assert keep(_p(1, 'Data Engineer'))
    assert not keep(_p(2, 'Data Engineer', company='EvilCorp'))


def test_remotive_adapter_normalises():
    def handler(request):
        assert request.url.params['search'] == 'Backend Engineer'
        return httpx.Response(200, json={'jobs': [{
            'id': 7, 'title': 'Backend Engineer', 'company_name': 'Doist', 'url': 'https://remotive.com/x',
            'description': '<p>Python</p>', 'candidate_required_location': 'Europe',
            'publication_date': '2026-10-01T10:00:00'}]})
    rows = RemotiveAdapter(transport=httpx.MockTransport(handler)).run(AdapterContext(query='Backend Engineer'))
    assert rows[0]['company']['name'] == 'Doist' and rows[0]['remote'] is True


def test_url_import_greenhouse_and_unknown():
    assert detect('https://boards.greenhouse.io/stripe/jobs/123456') == ('greenhouse', 'stripe', '123456')
    assert detect('https://jobs.lever.co/mistral/0d3e5a8e-1111-2222-3333-444455556666')[0] == 'lever'
    assert fetch_job_from_url('https://example.com/careers/1') is None

    def handler(request):
        return httpx.Response(200, content=json.dumps({
            'id': 123456, 'title': 'Payments Engineer', 'content': '&lt;p&gt;Go&lt;/p&gt;',
            'location': {'name': 'Remote - US'}, 'absolute_url': 'https://boards.greenhouse.io/stripe/jobs/123456'}))
    p = fetch_job_from_url('https://boards.greenhouse.io/stripe/jobs/123456', transport=httpx.MockTransport(handler))
    assert p['title'] == 'Payments Engineer' and p['remote'] is True and p['company']['name'] == 'Stripe'


def test_add_job_by_paste_creates_saved_application(auth_client, user):
    r = auth_client.post('/api/v1/jobs/add/', {
        'title': 'Platform Engineer', 'company': 'Tiny Startup', 'location': 'Remote',
        'description': 'We need someone with Python, Kubernetes and Terraform to run our platform.',
        'url': 'https://tinystartup.example/jobs/1'}, format='json')
    assert r.status_code == 201, r.data
    assert r.data['application_id']
    assert 'Kubernetes' in JobPosting.objects.get(pk=r.data['id']).skills
    # visible to the user who added it, not to others
    assert auth_client.get(f"/api/v1/jobs/{r.data['id']}/").status_code == 200


def test_add_job_needs_details_for_unknown_links(auth_client):
    r = auth_client.post('/api/v1/jobs/add/', {'url': 'https://example.com/job'}, format='json')
    assert r.status_code == 400 and r.data['needs_details'] is True


def test_manual_jobs_are_private(auth_client, user, api_client):
    from django.contrib.auth import get_user_model
    r = auth_client.post('/api/v1/jobs/add/', {
        'title': 'Platform Engineer', 'company': 'Tiny', 'description': 'x' * 60}, format='json')
    other = get_user_model().objects.create_user(username='bob', email='b@x.com', password='pw-123456')
    api_client.force_authenticate(other)
    assert api_client.get(f"/api/v1/jobs/{r.data['id']}/").status_code == 404


def test_refresh_requires_target_role(auth_client):
    assert auth_client.post('/api/v1/jobs/refresh/').status_code == 400


def test_unreachable_source_is_reported_not_ok():
    def handler(request):
        raise httpx.ConnectError('blocked')
    cand = Candidate(titles=['Backend Engineer'])
    plans = [Plan('remotive', 'aggregator', RemotiveAdapter(transport=httpx.MockTransport(handler)), AdapterContext())]
    out = discover_for_candidate(cand, plans=plans)
    assert out['sources'][0]['ok'] is False and out['sources'][0]['error'] == 'unreachable'
