"""Indeed scraper — in-session, user-cookie based.

Indeed fronts results with aggressive anti-bot (Cloudflare + a challenge on
data-heavy queries), so this path is best-effort; the API aggregators (JSearch /
Adzuna) are the more reliable route for Indeed inventory. Selectors marked
`# LIVE-SELECTOR` need tuning against live Indeed markup.
"""

from __future__ import annotations

from urllib.parse import quote_plus

from ingestion.adapters.base import looks_remote, make_posting

from .base import PortalQuery, PortalScraper, el_text, parse_dom


class IndeedScraper(PortalScraper):
    portal = 'indeed'
    base_url = 'https://www.indeed.com'
    login_markers = ('sign in', 'create an account', 'verifying you are human')

    def scrape(self, query: PortalQuery) -> list[dict]:
        url = f'{self.base_url}/jobs?q={quote_plus(query.keywords)}'
        if query.location:
            url += f'&l={quote_plus(query.location)}'
        if query.remote:
            url += '&sc=0kf%3Aattr%28DSQF7%29%3B'  # LIVE-SELECTOR: remote filter token
        html_text = self.driver.goto(url, wait_selector='div.job_seen_beacon', scrolls=2)  # LIVE-SELECTOR
        dom = parse_dom(html_text)
        self._guard_login(dom)
        return self.parse_list(html_text, self.base_url)[: query.max_results]

    @staticmethod
    def parse_list(html_text: str, base_url: str) -> list[dict]:
        dom = parse_dom(html_text)
        if dom is None:
            return []
        postings = []
        # LIVE-SELECTOR: each result card carries a stable data-jk job key.
        for card in dom.xpath("//*[@data-jk]"):
            jk = card.get('data-jk', '')
            if not jk:
                continue
            title = el_text(card, ".//h2[contains(@class,'jobTitle')]//span") \
                or el_text(card, ".//h2[contains(@class,'jobTitle')]")
            company = el_text(card, ".//*[@data-testid='company-name']")
            location = el_text(card, ".//*[@data-testid='text-location']")
            if not title:
                continue
            postings.append(make_posting(
                external_id=jk,
                title=title,
                location=location,
                remote=looks_remote(title, location),
                apply_url=f'{base_url}/viewjob?jk={jk}',
                company_name=company,
                ats_type='other',
                raw={'jk': jk, 'company': company, 'location': location},
            ))
        return postings
