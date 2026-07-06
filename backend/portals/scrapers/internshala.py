"""Internshala scraper — in-session, user-cookie based.

Covers both internships and Internshala's fresher jobs. Selectors marked
`# LIVE-SELECTOR` need tuning against live Internshala markup.
"""

from __future__ import annotations

import re
from urllib.parse import quote_plus

from ingestion.adapters.base import looks_remote, make_posting

from .base import PortalQuery, PortalScraper, el_text, parse_dom

_JOB_ID_RE = re.compile(r'-(\d+)(?:\?|$|/)')


class InternshalaScraper(PortalScraper):
    portal = 'internshala'
    base_url = 'https://internshala.com'
    login_markers = ('login', 'register (it\'s free)', 'student login')

    def scrape(self, query: PortalQuery) -> list[dict]:
        slug = query.keywords.strip().lower().replace(' ', '-') or 'jobs'
        url = f'{self.base_url}/jobs/{quote_plus(slug)}-jobs'
        if query.location:
            url += f'-in-{quote_plus(query.location.strip().lower().replace(" ", "-"))}'
        html_text = self.driver.goto(url, wait_selector='div.individual_internship', scrolls=2)  # LIVE-SELECTOR
        dom = parse_dom(html_text)
        self._guard_login(dom)
        return self.parse_list(html_text, self.base_url)[: query.max_results]

    @staticmethod
    def parse_list(html_text: str, base_url: str) -> list[dict]:
        dom = parse_dom(html_text)
        if dom is None:
            return []
        postings = []
        # LIVE-SELECTOR: each card carries a job/detail anchor ending in a numeric id.
        for card in dom.xpath("//div[contains(@class,'individual_internship')]"):
            anchor = card.xpath(".//a[contains(@class,'job-title-href') or contains(@href,'/job/detail') or contains(@href,'/internship/detail')]")
            if not anchor:
                continue
            href = anchor[0].get('href', '')
            match = _JOB_ID_RE.search(href) or _JOB_ID_RE.search(card.get('data-href', ''))
            if not match:
                continue
            title = ' '.join(anchor[0].text_content().split())
            company = el_text(card, ".//*[contains(@class,'company-name') or contains(@class,'company_name')]")
            location = el_text(card, ".//*[contains(@class,'locations')]")
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
