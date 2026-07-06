"""TimesJobs scraper — in-session, user-cookie based.

Selectors marked `# LIVE-SELECTOR` need tuning against live TimesJobs markup.
"""

from __future__ import annotations

import re
from urllib.parse import quote_plus

from ingestion.adapters.base import looks_remote, make_posting

from .base import PortalQuery, PortalScraper, el_text, parse_dom

_JOB_ID_RE = re.compile(r'jobid[-=](\d+)')


class TimesJobsScraper(PortalScraper):
    portal = 'timesjobs'
    base_url = 'https://www.timesjobs.com'
    login_markers = ('login to apply', 'register now', 'create your profile')

    def scrape(self, query: PortalQuery) -> list[dict]:
        url = (
            f'{self.base_url}/candidate/job-search.html'
            f'?searchType=personalizedSearch&txtKeywords={quote_plus(query.keywords)}'
        )
        if query.location:
            url += f'&txtLocation={quote_plus(query.location)}'
        html_text = self.driver.goto(url, wait_selector='li.clearfix.job-bx', scrolls=2)  # LIVE-SELECTOR
        dom = parse_dom(html_text)
        self._guard_login(dom)
        return self.parse_list(html_text, self.base_url)[: query.max_results]

    @staticmethod
    def parse_list(html_text: str, base_url: str) -> list[dict]:
        dom = parse_dom(html_text)
        if dom is None:
            return []
        postings = []
        # LIVE-SELECTOR: each posting is an <li class="job-bx"> with a detail anchor.
        for card in dom.xpath("//li[contains(@class,'job-bx')]"):
            anchor = card.xpath(".//h2/a | .//header//a")
            if not anchor:
                continue
            href = anchor[0].get('href', '')
            match = _JOB_ID_RE.search(href)
            if not match:
                continue
            title = ' '.join(anchor[0].text_content().split())
            company = el_text(card, ".//h3[contains(@class,'joblist-comp-name')]")
            location = el_text(card, ".//ul[contains(@class,'top-jd-dtl')]//span")
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
