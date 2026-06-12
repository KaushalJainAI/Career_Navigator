import pytest

from jobs.models import JobPosting
from portals.drivers import FakeBrowserDriver
from portals.models import PortalAccount
from portals.scrapers.base import PortalQuery
from portals.services import run_portal_scrape
from portals.tests.test_scrapers import LINKEDIN_HTML

pytestmark = pytest.mark.django_db


def test_run_portal_scrape_success_upserts_and_logs(user):
    driver = FakeBrowserDriver(
        pages={'/jobs/search': LINKEDIN_HTML},
        state={'cookies': [{'name': 'li_at', 'value': 'V'}], 'origins': []},
    )
    run = run_portal_scrape('linkedin', user, PortalQuery(keywords='python'), driver=driver)

    assert run.status == 'success'
    assert run.stats == {'created': 2, 'updated': 0, 'skipped': 0}
    assert JobPosting.objects.filter(source__name='portal:linkedin').count() == 2
    # the post-run session is captured and encrypted on the user's account
    account = PortalAccount.objects.get(user=user, portal__name='linkedin')
    assert account.has_session()
    assert account.reveal_storage_state()['cookies'][0]['value'] == 'V'


def test_run_portal_scrape_is_idempotent(user):
    driver = FakeBrowserDriver(pages={'/jobs/search': LINKEDIN_HTML})
    run_portal_scrape('linkedin', user, PortalQuery(keywords='python'), driver=driver)
    run2 = run_portal_scrape('linkedin', user, PortalQuery(keywords='python'), driver=driver)
    assert run2.stats == {'created': 0, 'updated': 2, 'skipped': 0}
    assert JobPosting.objects.filter(source__name='portal:linkedin').count() == 2


def test_run_portal_scrape_needs_login_without_session(user):
    # no driver injected + no stored/env session → clean needs_login, no browser
    run = run_portal_scrape('linkedin', user, PortalQuery(keywords='python'))
    assert run.status == 'needs_login'
    assert 'session' in run.error.lower()


def test_run_portal_scrape_detects_login_wall(user):
    driver = FakeBrowserDriver(default_html='<body>Join now. Sign in to continue.</body>')
    run = run_portal_scrape('linkedin', user, PortalQuery(keywords='python'), driver=driver)
    assert run.status == 'needs_login'


def test_run_portal_scrape_unknown_portal_raises(user):
    with pytest.raises(ValueError):
        run_portal_scrape('monster', user, PortalQuery())
