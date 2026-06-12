"""LinkedIn Jobs scraper — in-session, user-cookie based.

Drives the public jobs search results in the user's own authenticated session.
Selectors marked `# LIVE-SELECTOR` must be tuned against live LinkedIn markup and
re-checked when the site changes; the pure `parse_list` is unit-tested against a
representative fixture.
"""

from __future__ import annotations

import re
from urllib.parse import quote_plus

from ingestion.adapters.base import looks_remote, make_posting

from .base import PortalQuery, PortalScraper, el_text, parse_dom

_VIEW_ID_RE = re.compile(r'/jobs/view/(?:[^/]*-)?(\d+)')


class LinkedInScraper(PortalScraper):
    portal = 'linkedin'
    source_kind = 'linkedin'
    base_url = 'https://www.linkedin.com'
    login_markers = ('join now', 'sign in to', 'new to linkedin')

    def scrape(self, query: PortalQuery) -> list[dict]:
        url = (
            f'{self.base_url}/jobs/search/?keywords={quote_plus(query.keywords)}'
            f'&location={quote_plus(query.location)}'
        )
        if query.remote:
            url += '&f_WT=2'  # LinkedIn "remote" workplace-type filter
        html_text = self.driver.goto(
            url, wait_selector='div.job-search-card', scrolls=3,  # LIVE-SELECTOR
        )
        dom = parse_dom(html_text)
        self._guard_login(dom)
        return self.parse_list(html_text, self.base_url)[: query.max_results]

    @staticmethod
    def parse_list(html_text: str, base_url: str) -> list[dict]:
        dom = parse_dom(html_text)
        if dom is None:
            return []
        postings = []
        # LIVE-SELECTOR: each result is an anchor into /jobs/view/<id>.
        for anchor in dom.xpath("//a[contains(@href, '/jobs/view/')]"):
            href = anchor.get('href', '')
            match = _VIEW_ID_RE.search(href)
            if not match:
                continue
            card = anchor.xpath('ancestor::li[1]')
            scope = card[0] if card else anchor
            title = el_text(scope, ".//*[contains(@class,'base-search-card__title')]") \
                or ' '.join(anchor.text_content().split())
            company = el_text(scope, ".//*[contains(@class,'base-search-card__subtitle')]")
            location = el_text(scope, ".//*[contains(@class,'job-search-card__location')]")
            if not title:
                continue
            apply_url = href if href.startswith('http') else f'{base_url}{href}'
            postings.append(make_posting(
                external_id=match.group(1),
                title=title,
                location=location,
                remote=looks_remote(title, location),
                apply_url=apply_url.split('?')[0],
                company_name=company,
                ats_type='other',
                raw={'href': href, 'company': company, 'location': location},
            ))
        return _dedupe(postings)


def _dedupe(postings: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out = []
    for posting in postings:
        if posting['external_id'] in seen:
            continue
        seen.add(posting['external_id'])
        out.append(posting)
    return out
