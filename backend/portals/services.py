"""Orchestration: drive a portal in the user's session, scrape, and upsert.

`run_portal_scrape` is the single entry point. The browser is injected
(`driver=`) so tests run with `FakeBrowserDriver`; in production it defaults to a
real `PlaywrightDriver`. Scraped postings go through the canonical
`ingestion.services.upsert_postings`, so the Ghost-Job Shield, matching, and
stealth filter all apply automatically.
"""

from __future__ import annotations

import logging
from dataclasses import asdict

from django.utils import timezone

from ingestion.services import upsert_postings
from jobs.models import Source

from .models import Portal, PortalAccount, PortalAccountStatus, PortalScrapeRun
from .registry import PORTALS, PortalSpec, get_scraper
from .scrapers.base import NeedsLoginError, PortalQuery
from .sessions import load_storage_state

logger = logging.getLogger(__name__)


def _portal_row(spec: PortalSpec) -> Portal:
    portal, _ = Portal.objects.get_or_create(
        name=spec.name,
        defaults={'display_name': spec.display_name, 'login_url': spec.login_url},
    )
    return portal


def _source_for_portal(spec: PortalSpec) -> Source:
    source, _ = Source.objects.get_or_create(
        name=f'portal:{spec.name}',
        defaults={'kind': spec.source_kind},
    )
    return source


def _finish(run: PortalScrapeRun, status: str, *, stats=None, error: str = '') -> PortalScrapeRun:
    run.status = status
    if stats is not None:
        run.stats = stats
    if error:
        run.error = error
    run.finished_at = timezone.now()
    run.save()
    return run


def _persist_session(user, portal: Portal, driver) -> None:
    try:
        state = driver.storage_state()
    except Exception:  # noqa: BLE001 - never fail a successful scrape over session save
        return
    if not state:
        return
    account, _ = PortalAccount.objects.get_or_create(user=user, portal=portal)
    account.set_storage_state(state)
    account.last_used_at = timezone.now()
    account.save()


def run_portal_scrape(portal_name: str, user, query: PortalQuery, *, driver=None) -> PortalScrapeRun:
    spec = PORTALS.get(portal_name)
    if spec is None:
        raise ValueError(f'Unknown portal {portal_name!r}')
    portal = _portal_row(spec)
    run = PortalScrapeRun.objects.create(user=user, portal=portal, query=asdict(query), status='running')

    owns_driver = driver is None
    state = load_storage_state(user, portal_name)
    if state is None and owns_driver:
        return _finish(run, 'needs_login',
                       error='No session for this portal. Add a session cookie first.')

    try:
        if owns_driver:
            from .drivers import PlaywrightDriver  # lazy: keep Playwright out of import path
            from django.conf import settings
            driver = PlaywrightDriver(min_delay_seconds=settings.PORTAL_SCRAPER_MIN_DELAY_SECONDS)
        driver.start(headless=_headless(), storage_state=state)
        scraper = get_scraper(portal_name)(driver)
        postings = scraper.scrape(query)
        stats = upsert_postings(_source_for_portal(spec), postings)
        _persist_session(user, portal, driver)
        return _finish(run, 'success', stats=stats)
    except NeedsLoginError as exc:
        PortalAccount.objects.filter(user=user, portal=portal).update(
            status=PortalAccountStatus.NEEDS_LOGIN,
        )
        return _finish(run, 'needs_login', error=str(exc))
    except Exception as exc:  # noqa: BLE001 - record the failure on the run, don't crash the worker
        logger.warning('portal scrape failed (%s): %s', portal_name, exc)
        return _finish(run, 'failed', error=str(exc))
    finally:
        if owns_driver and driver is not None:
            try:
                driver.close()
            except Exception:  # noqa: BLE001
                pass


def _headless() -> bool:
    from django.conf import settings
    return getattr(settings, 'PORTAL_SCRAPER_HEADLESS', True)
