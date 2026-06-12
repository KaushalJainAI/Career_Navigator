"""Unstop (formerly Dare2Compete) scraper — in-session, user-cookie based.

Selectors marked `# LIVE-SELECTOR` need tuning against live Unstop markup.
"""

from __future__ import annotations

import re
from urllib.parse import quote_plus

from ingestion.adapters.base import looks_remote, make_posting

from .base import PortalQuery, PortalScraper, el_text, parse_dom

_SLUG_ID_RE = re.compile(r'/(?:jobs|internships)/[^/]*-(\d+)')


class UnstopScraper(PortalScraper):
    portal = 'unstop'
    base_url = 'https://unstop.com'
    login_markers = ('login to unstop', 'create your account', 'register to apply')

    def scrape(self, query: PortalQuery) -> list[dict]:
        url = f'{self.base_url}/jobs?searchTerm={quote_plus(query.keywords)}'
        html_text = self.driver.goto(url, wait_selector='div.opportunity-cards', scrolls=2)  # LIVE-SELECTOR
        dom = parse_dom(html_text)
        self._guard_login(dom)
        return self.parse_list(html_text, self.base_url)[: query.max_results]

    @staticmethod
    def parse_list(html_text: str, base_url: str) -> list[dict]:
        dom = parse_dom(html_text)
        if dom is None:
            return []
        postings = []
        # LIVE-SELECTOR: opportunity cards link to /jobs/<slug>-<id>.
        for anchor in dom.xpath("//a[contains(@href,'/jobs/') or contains(@href,'/internships/')]"):
            href = anchor.get('href', '')
            match = _SLUG_ID_RE.search(href)
            if not match:
                continue
            card = anchor.xpath("ancestor::*[contains(@class,'single_profile') or contains(@class,'opportunity-card')][1]")
            scope = card[0] if card else anchor
            title = el_text(scope, ".//*[contains(@class,'opp_title') or self::h2]") \
                or ' '.join(anchor.text_content().split())
            company = el_text(scope, ".//*[contains(@class,'org_name') or contains(@class,'company')]")
            location = el_text(scope, ".//*[contains(@class,'location')]")
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
        return postings
