"""Glassdoor scraper — in-session, user-cookie based.

Glassdoor sits behind DataDome bot protection and rotates its markup often, so
this path is best-effort; the API aggregators (JSearch / Adzuna) are the more
reliable route for Glassdoor inventory. Selectors marked `# LIVE-SELECTOR` need
tuning against live Glassdoor markup.
"""

from __future__ import annotations

from urllib.parse import quote_plus

from ingestion.adapters.base import looks_remote, make_posting

from .base import PortalQuery, PortalScraper, el_text, parse_dom


class GlassdoorScraper(PortalScraper):
    portal = 'glassdoor'
    base_url = 'https://www.glassdoor.com'
    login_markers = ('sign in', 'create your free account', 'help us protect glassdoor')

    def scrape(self, query: PortalQuery) -> list[dict]:
        url = (
            f'{self.base_url}/Job/jobs.htm'
            f'?sc.keyword={quote_plus(query.keywords)}'
        )
        if query.location:
            url += f'&locKeyword={quote_plus(query.location)}'
        html_text = self.driver.goto(url, wait_selector='li.JobsList_jobListItem__wjTHv', scrolls=3)  # LIVE-SELECTOR
        dom = parse_dom(html_text)
        self._guard_login(dom)
        return self.parse_list(html_text, self.base_url)[: query.max_results]

    @staticmethod
    def parse_list(html_text: str, base_url: str) -> list[dict]:
        dom = parse_dom(html_text)
        if dom is None:
            return []
        postings = []
        # LIVE-SELECTOR: each list item carries a data-jobid and a title anchor.
        for card in dom.xpath("//*[@data-jobid or @data-id]"):
            job_id = card.get('data-jobid') or card.get('data-id') or ''
            if not job_id.isdigit():
                continue
            anchor = card.xpath(".//a[contains(@class,'JobCard_jobTitle') or contains(@class,'jobLink')]")
            title = ' '.join(anchor[0].text_content().split()) if anchor else \
                el_text(card, ".//*[contains(@class,'jobTitle')]")
            company = el_text(card, ".//*[contains(@class,'EmployerProfile') or contains(@class,'employerName')]")
            location = el_text(card, ".//*[contains(@class,'JobCard_location') or contains(@class,'location')]")
            href = anchor[0].get('href', '') if anchor else ''
            if not title:
                continue
            apply_url = href if href.startswith('http') else f'{base_url}{href}' if href else f'{base_url}/job-listing/index.htm?jl={job_id}'
            postings.append(make_posting(
                external_id=job_id,
                title=title,
                location=location,
                remote=looks_remote(title, location),
                apply_url=apply_url.split('?')[0] if href else apply_url,
                company_name=company,
                ats_type='other',
                raw={'job_id': job_id, 'company': company, 'location': location},
            ))
        return postings
