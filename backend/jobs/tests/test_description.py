"""Full-JD fetch: aggregator descriptions are truncated teasers, so the real
page is fetched once from apply_url and cached on the row."""

import itertools

import httpx
import pytest

from jobs.description import ensure_full_description, fetch_full_description, html_to_text
from jobs.models import Company, JobPosting, Source

pytestmark = pytest.mark.django_db


JD_HTML = """
<html><head><title>Role</title><style>.x{color:red}</style></head>
<body>
  <nav>Home Jobs Login</nav>
  <main>
    <h1>Senior Backend Engineer</h1>
    <p>You will build and operate distributed Python services on AWS.</p>
    <ul><li>5+ years of Python</li><li>Django and PostgreSQL</li>
        <li>Kubernetes, Terraform, CI/CD</li></ul>
    <p>We offer equity, health cover and a learning budget. Apply today.</p>
    <h2>About the role</h2>
    <p>You will join a small platform team that owns ingestion, storage and the
    public API. Day to day you will design services, review code, run incidents
    and mentor engineers. We deploy many times a day behind feature flags and
    expect strong testing habits from everyone on the team.</p>
    <h2>What we look for</h2>
    <p>Depth in one backend language, comfort with relational data modelling,
    and the judgement to know when a simpler design is the right one. You will
    be trusted with production access from your first month.</p>
  </main>
  <footer>(c) Acme. Privacy policy.</footer>
  <script>track();</script>
</body></html>
"""


_next_id = itertools.count(1)


def _job(apply_url='https://boards.example.com/jobs/1', description='teaser'):
    source, _ = Source.objects.get_or_create(name='adzuna', defaults={'kind': 'aggregator'})
    company, _ = Company.objects.get_or_create(name='Acme', domain='acme.com')
    return JobPosting.objects.create(
        source=source, external_id=str(next(_next_id)), company=company,
        title='Senior Backend Engineer', description=description, apply_url=apply_url,
    )


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_html_to_text_keeps_main_content_and_drops_chrome():
    text = html_to_text(JD_HTML)
    assert 'distributed Python services' in text
    assert 'Kubernetes, Terraform, CI/CD' in text
    assert 'Login' not in text        # <nav> stripped
    assert 'Privacy policy' not in text  # <footer> stripped
    assert 'track()' not in text      # <script> stripped


def test_html_to_text_handles_empty_and_malformed_input():
    assert html_to_text('') == ''
    assert html_to_text('   ') == ''
    assert 'hello' in html_to_text('<p>hello')  # unclosed tag is tolerated


def test_fetch_returns_text_for_html_response():
    job = _job()
    client = _client(lambda request: httpx.Response(
        200, text=JD_HTML, headers={'content-type': 'text/html; charset=utf-8'}))
    assert 'distributed Python services' in fetch_full_description(job, client=client)


def test_fetch_returns_empty_on_http_error_and_on_non_html():
    job = _job()
    assert fetch_full_description(job, client=_client(
        lambda r: httpx.Response(403, text='no'))) == ''
    assert fetch_full_description(job, client=_client(
        lambda r: httpx.Response(200, text='{}', headers={'content-type': 'application/json'}))) == ''


def test_fetch_skips_non_http_apply_url():
    """No apply_url means nothing to fetch — must not raise or hit the network."""
    assert fetch_full_description(_job(apply_url='')) == ''
    assert fetch_full_description(_job(apply_url='mailto:jobs@acme.com')) == ''


def test_ensure_caches_and_does_not_refetch():
    job = _job()
    calls = []

    def handler(request):
        calls.append(request.url)
        return httpx.Response(200, text=JD_HTML, headers={'content-type': 'text/html'})

    text = ensure_full_description(job, client=_client(handler))
    assert 'Kubernetes' in text
    job.refresh_from_db()
    assert job.full_description_fetched_at is not None
    assert job.best_description == job.full_description

    ensure_full_description(job, client=_client(handler))
    assert len(calls) == 1, 'cached result must not trigger a second request'


def test_failed_fetch_is_stamped_and_not_retried_immediately():
    """A page we cannot read costs one request, not one per view — and the
    teaser stays in place so the job is still usable."""
    job = _job(description='short teaser')
    calls = []

    def handler(request):
        calls.append(request.url)
        return httpx.Response(500, text='boom')

    assert ensure_full_description(job, client=_client(handler)) == 'short teaser'
    ensure_full_description(job, client=_client(handler))
    assert len(calls) == 1
    job.refresh_from_db()
    assert job.full_description == ''
    assert job.best_description == 'short teaser'


def test_shorter_scrape_does_not_replace_a_longer_teaser():
    """Consent walls and stubs return less text than the API already gave us."""
    job = _job(description='x' * 500)
    stub = '<html><body><main>Please enable JavaScript.</main></body></html>'
    result = ensure_full_description(job, client=_client(
        lambda r: httpx.Response(200, text=stub, headers={'content-type': 'text/html'})))
    assert result == 'x' * 500
    job.refresh_from_db()
    assert job.full_description == ''


def test_best_description_prefers_full_text():
    job = _job(description='teaser')
    assert job.best_description == 'teaser'
    job.full_description = 'the whole job description'
    assert job.best_description == 'the whole job description'


def test_candidate_urls_prefers_readable_adzuna_details_page():
    """Adzuna's redirect_url is a JS interstitial that extracts to nothing;
    /details/<id> renders the JD server-side."""
    from jobs.description import candidate_urls

    job = _job(apply_url='https://www.adzuna.com/land/ad/999?se=tok')
    job.raw = {'id': '999'}
    urls = candidate_urls(job)
    assert urls[0] == 'https://www.adzuna.com/details/999'
    assert urls[1] == 'https://www.adzuna.com/land/ad/999?se=tok'


def test_fetch_falls_through_to_next_candidate_when_first_is_blocked():
    job = _job(apply_url='https://boards.example.com/jobs/1')
    job.raw = {'id': '999'}
    job.save(update_fields=['raw'])
    seen = []

    def handler(request):
        seen.append(str(request.url))
        if 'adzuna.com' in str(request.url):
            return httpx.Response(403, text='blocked')
        return httpx.Response(200, text=JD_HTML, headers={'content-type': 'text/html'})

    text = fetch_full_description(job, client=_client(handler))
    assert 'Kubernetes' in text
    assert len(seen) == 2, 'must try the fallback after the first URL fails'


@pytest.mark.parametrize('body', [
    '<html><body><main>403 ERROR. The request could not be satisfied. '
    'Request blocked. ' + 'padding text ' * 60 + '</main></body></html>',
    '<html><body><main>Please enable JavaScript to view this page. '
    + 'padding text ' * 60 + '</main></body></html>',
])
def test_block_pages_are_rejected_even_when_longer_than_the_teaser(body):
    """A CloudFront 403 body extracts to ~550 chars and would otherwise
    overwrite a 500-char Adzuna teaser with garbage."""
    job = _job(description='x' * 500)
    result = ensure_full_description(job, client=_client(
        lambda r: httpx.Response(200, text=body, headers={'content-type': 'text/html'})))
    assert result == 'x' * 500
    job.refresh_from_db()
    assert job.full_description == ''


def test_short_but_clean_page_is_rejected_as_a_stub():
    from jobs.description import looks_unusable

    assert looks_unusable('too short')
    assert not looks_unusable('A real job description. ' * 40)


def test_failed_fetch_is_retried_after_the_backoff_window():
    """Blocks are often transient — a board that rate-limits a burst serves
    the same URL happily later, so failure must not be permanent."""
    from django.utils import timezone

    from jobs.description import RETRY_FAILED_AFTER

    job = _job(description='short teaser')
    calls = []

    def handler(request):
        calls.append(str(request.url))
        if len(calls) == 1:
            return httpx.Response(429, text='slow down')
        return httpx.Response(200, text=JD_HTML, headers={'content-type': 'text/html'})

    assert ensure_full_description(job, client=_client(handler)) == 'short teaser'

    job.full_description_fetched_at = timezone.now() - RETRY_FAILED_AFTER * 2
    job.save(update_fields=['full_description_fetched_at'])

    assert 'Kubernetes' in ensure_full_description(job, client=_client(handler))
    assert len(calls) == 2
