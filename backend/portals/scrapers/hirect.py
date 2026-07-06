"""Hirect scraper — in-session, user-cookie based.

Hirect is chat-first and mobile-led; its web listing surface is thinner than the
app, so coverage is best-effort. Selectors marked `# LIVE-SELECTOR` need tuning
against live Hirect markup.
"""

from __future__ import annotations

import re
from urllib.parse import quote_plus

from ingestion.adapters.base import looks_remote, make_posting

from .base import PortalQuery, PortalScraper, el_text, parse_dom

_JOB_ID_RE = re.compile(r'/(?:job|position)/([A-Za-z0-9]+)')


class HirectScraper(PortalScraper):
    portal = 'hirect'
    base_url = 'https://www.hirect.in'
    login_markers = ('log in', 'download the app', 'sign up')

    def scrape(self, query: PortalQuery) -> list[dict]:
        url = f'{self.base_url}/jobs?keyword={quote_plus(query.keywords)}'
        if query.location:
            url += f'&city={quote_plus(query.location)}'
        html_text = self.driver.goto(url, wait_selector='div.job-item', scrolls=3)  # LIVE-SELECTOR
        dom = parse_dom(html_text)
        self._guard_login(dom)
        return self.parse_list(html_text, self.base_url)[: query.max_results]

    @staticmethod
    def parse_list(html_text: str, base_url: str) -> list[dict]:
        dom = parse_dom(html_text)
        if dom is None:
            return []
        postings = []
        # LIVE-SELECTOR: cards link to /job/<id>.
        for anchor in dom.xpath("//a[contains(@href,'/job/') or contains(@href,'/position/')]"):
            href = anchor.get('href', '')
            match = _JOB_ID_RE.search(href)
            if not match:
                continue
            card = anchor.xpath("ancestor::div[contains(@class,'job-item')][1]")
            scope = card[0] if card else anchor
            title = el_text(scope, ".//*[contains(@class,'job-title')]") or ' '.join(anchor.text_content().split())
            company = el_text(scope, ".//*[contains(@class,'company')]")
            location = el_text(scope, ".//*[contains(@class,'city') or contains(@class,'location')]")
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
