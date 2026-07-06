"""Wellfound (formerly AngelList Talent) scraper — in-session, user-cookie based.

Selectors marked `# LIVE-SELECTOR` need tuning against live Wellfound markup.
"""

from __future__ import annotations

import re
from urllib.parse import quote_plus

from ingestion.adapters.base import looks_remote, make_posting

from .base import PortalQuery, PortalScraper, el_text, parse_dom

_JOB_ID_RE = re.compile(r'/jobs/(\d+)')


class WellfoundScraper(PortalScraper):
    portal = 'wellfound'
    base_url = 'https://wellfound.com'
    login_markers = ('log in', 'sign up', 'find your next hire')

    def scrape(self, query: PortalQuery) -> list[dict]:
        role = query.keywords.strip().lower().replace(' ', '-') or 'software-engineer'
        url = f'{self.base_url}/role/{quote_plus(role)}'
        if query.location:
            url += f'/{quote_plus(query.location.strip().lower().replace(" ", "-"))}'
        html_text = self.driver.goto(url, wait_selector='div[data-test="JobSearchResults"]', scrolls=3)  # LIVE-SELECTOR
        dom = parse_dom(html_text)
        self._guard_login(dom)
        return self.parse_list(html_text, self.base_url)[: query.max_results]

    @staticmethod
    def parse_list(html_text: str, base_url: str) -> list[dict]:
        dom = parse_dom(html_text)
        if dom is None:
            return []
        postings = []
        # LIVE-SELECTOR: job title anchors link to /jobs/<id>-<slug>.
        for anchor in dom.xpath("//a[contains(@href,'/jobs/')]"):
            href = anchor.get('href', '')
            match = _JOB_ID_RE.search(href)
            if not match:
                continue
            card = anchor.xpath("ancestor::div[contains(@class,'styles_component') or contains(@data-test,'JobListing')][1]")
            scope = card[0] if card else anchor
            title = ' '.join(anchor.text_content().split())
            company = el_text(scope, ".//*[contains(@class,'company') or contains(@data-test,'startup')]")
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
