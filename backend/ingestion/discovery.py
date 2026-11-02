"""User-triggered job discovery.

"Find jobs for me": runs every source that works without configuration
(public Greenhouse/Lever boards, Remotive, Arbeitnow) plus any keyed
aggregator the operator configured (Adzuna, Jooble, JSearch), using the
user's target titles/locations as the query. Postings are filtered for
relevance to the user's target roles before they are stored, then go
through `upsert_postings` (Ghost-Job Shield + skill extraction included).
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable

from django.conf import settings
from django.utils import timezone

from jobs.models import Source
from matching.fit import Candidate, _core, _title_tokens

from .adapters.adzuna import AdzunaAdapter
from .adapters.arbeitnow import ArbeitnowAdapter
from .adapters.base import AdapterContext, BaseAdapter
from .adapters.greenhouse import GreenhouseAdapter
from .adapters.jooble import JoobleAdapter
from .adapters.jsearch import JSearchAdapter
from .adapters.lever import LeverAdapter
from .adapters.remotive import RemotiveAdapter
from .models import IngestionRun
from .services import upsert_postings

logger = logging.getLogger(__name__)

# Public ATS boards of companies that hire broadly; used when the operator
# hasn't configured GREENHOUSE_TOKENS / LEVER_TOKENS. Users can add their own.
DEFAULT_GREENHOUSE_BOARDS = [
    'stripe', 'airbnb', 'figma', 'discord', 'databricks', 'gitlab', 'coinbase', 'cloudflare',
    'datadog', 'dropbox', 'reddit', 'robinhood', 'instacart', 'anthropic', 'asana', 'duolingo',
]
DEFAULT_LEVER_SITES = ['mistral', 'palantir', 'plaid', 'spotify', 'kraken']

MAX_PER_SOURCE = 200
GENERIC_TITLE_TOKENS = {'and', 'of', 'the', 'for', 'specialist', 'associate', 'team', 'member'}


@dataclass
class Plan:
    name: str
    kind: str
    adapter: BaseAdapter
    ctx: AdapterContext


def watched_boards(watch: list[str]) -> tuple[list[str], list[str]]:
    gh, lv = [], []
    for item in watch or []:
        kind, _, token = str(item).partition(':')
        token = token.strip().lower()
        if not token:
            continue
        if kind == 'greenhouse':
            gh.append(token)
        elif kind == 'lever':
            lv.append(token)
    return gh, lv


def build_plans(candidate: Candidate, watch: list[str] | None = None) -> list[Plan]:
    query = candidate.titles[0] if candidate.titles else ''
    location = candidate.locations[0] if candidate.locations else ''
    ctx = AdapterContext(query=query, location=location, page_size=50, max_pages=2)
    gh_watch, lv_watch = watched_boards(watch or [])
    gh = list(dict.fromkeys(gh_watch + (settings.GREENHOUSE_TOKENS or DEFAULT_GREENHOUSE_BOARDS)))
    lv = list(dict.fromkeys(lv_watch + (settings.LEVER_TOKENS or DEFAULT_LEVER_SITES)))
    plans = [
        Plan('greenhouse', 'ats_public', GreenhouseAdapter(tokens=gh), ctx),
        Plan('lever', 'ats_public', LeverAdapter(tokens=lv), ctx),
        Plan('remotive', 'aggregator', RemotiveAdapter(), ctx),
        Plan('arbeitnow', 'aggregator', ArbeitnowAdapter(), ctx),
    ]
    if getattr(settings, 'ADZUNA_APP_ID', '') and getattr(settings, 'ADZUNA_APP_KEY', ''):
        plans.append(Plan('adzuna', 'aggregator', AdzunaAdapter(), ctx))
    if getattr(settings, 'JOOBLE_API_KEY', ''):
        plans.append(Plan('jooble', 'aggregator', JoobleAdapter(), ctx))
    if getattr(settings, 'JSEARCH_RAPIDAPI_KEY', ''):
        plans.append(Plan('jsearch', 'aggregator', JSearchAdapter(), ctx))
    return plans


def relevance_filter(candidate: Candidate) -> Callable[[dict], bool]:
    target_core: set[str] = set()
    for t in candidate.titles[:5]:
        target_core |= _core(_title_tokens(t))
    target_core -= GENERIC_TITLE_TOKENS
    excluded = set(candidate.exclude_companies)

    def keep(p: dict) -> bool:
        company = ((p.get('company') or {}).get('name') or '').lower()
        if company and company in excluded:
            return False
        if not target_core:
            return True
        return bool(_core(_title_tokens(p.get('title', ''))) & target_core)

    return keep


def _fetch(plan: Plan) -> tuple[Plan, list[dict], str]:
    try:
        rows = plan.adapter.run(plan.ctx)
        fails, reqs = getattr(plan.adapter, 'failures', 0), getattr(plan.adapter, 'requests', 0)
        if not rows and fails and fails >= reqs:
            return plan, rows, 'unreachable'
        return plan, rows, ''
    except Exception as exc:  # noqa: BLE001 - one bad source must not kill the refresh
        logger.warning('discovery: %s failed: %s', plan.name, type(exc).__name__)
        return plan, [], type(exc).__name__


def discover_for_candidate(candidate: Candidate, *, watch: list[str] | None = None,
                           plans: list[Plan] | None = None) -> dict:
    plans = plans if plans is not None else build_plans(candidate, watch)
    keep = relevance_filter(candidate)
    # Network in parallel, DB writes serially on this thread.
    with ThreadPoolExecutor(max_workers=max(1, len(plans))) as pool:
        results = list(pool.map(_fetch, plans))
    report = []
    total_created = 0
    for plan, postings, error in results:
        source, _ = Source.objects.get_or_create(name=plan.name, defaults={'kind': plan.kind})
        kept = [p for p in postings if keep(p)][:MAX_PER_SOURCE]
        run = IngestionRun.objects.create(source=source)
        stats = upsert_postings(source, kept) if kept else {'created': 0, 'updated': 0, 'skipped': 0}
        run.status = 'failed' if error and not postings else 'success'
        run.error = error
        run.stats = {**stats, 'fetched': len(postings), 'kept': len(kept)}
        run.finished_at = timezone.now()
        run.save()
        total_created += stats['created']
        report.append({'source': plan.name, 'fetched': len(postings), 'kept': len(kept),
                       'created': stats['created'], 'updated': stats['updated'],
                       'ok': not (error and not postings), 'error': error})
    return {'sources': report, 'new_jobs': total_created}
