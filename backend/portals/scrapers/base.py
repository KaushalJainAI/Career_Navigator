"""Portal scraper contract.

A scraper drives a `BrowserDriver` to fetch result pages, then parses them with a
**pure** `parse_list(html, base_url)` static method into the canonical posting
dict (`ingestion.adapters.base.make_posting`). Keeping parsing pure means it is
unit-tested against canned HTML with no browser, exactly like the API adapters'
`_normalise`. Live CSS selectors are marked `# LIVE-SELECTOR` — they need tuning
against real pages and re-checking when a site's markup changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lxml import html as lxml_html

from ..drivers import BrowserDriver


@dataclass
class PortalQuery:
    keywords: str = ''
    location: str = ''
    remote: bool | None = None
    max_results: int = 25
    extra: dict = field(default_factory=dict)


class NeedsLoginError(Exception):
    """Raised when a portal serves a login wall instead of results — surfaced to
    the user as a clean `needs_login` run, never a crash."""


def parse_dom(html_text: str):
    """Tolerant HTML → lxml element. Returns None for empty input."""
    if not html_text or not html_text.strip():
        return None
    return lxml_html.fromstring(html_text)


def el_text(element, xpath: str) -> str:
    """First text match for an xpath, whitespace-collapsed; '' if absent."""
    if element is None:
        return ''
    found = element.xpath(xpath)
    if not found:
        return ''
    value = found[0]
    text = value if isinstance(value, str) else value.text_content()
    return ' '.join(text.split()).strip()


def login_wall(element, markers: tuple[str, ...]) -> bool:
    """Heuristic: the page is a login wall if any marker phrase appears in it."""
    if element is None:
        return False
    body = element.text_content().lower()
    return any(marker.lower() in body for marker in markers)


class PortalScraper:
    portal: str = ''
    source_kind: str = 'scraper'
    login_markers: tuple[str, ...] = ('sign in', 'log in', 'join now')

    def __init__(self, driver: BrowserDriver):
        self.driver = driver

    def scrape(self, query: PortalQuery) -> list[dict]:
        raise NotImplementedError

    @staticmethod
    def parse_list(html_text: str, base_url: str) -> list[dict]:  # pragma: no cover - overridden
        raise NotImplementedError

    def _guard_login(self, dom) -> None:
        if login_wall(dom, self.login_markers):
            raise NeedsLoginError(f'{self.portal}: session is not logged in')
