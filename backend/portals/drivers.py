"""Browser-driver abstraction.

Everything that touches a real browser goes through `BrowserDriver`, so the
scrapers and services can be unit-tested with `FakeBrowserDriver` and canned HTML
— no Chromium, no network. `PlaywrightDriver` lazily imports `sync_playwright`
inside `start()` (never at module import), mirroring the project rule that heavy
/ optional dependencies are injected at the call site, not imported at the top.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Protocol

logger = logging.getLogger(__name__)


class BrowserDriver(Protocol):
    def start(self, *, headless: bool = True, storage_state: dict | None = None) -> None: ...

    def goto(self, url: str, *, wait_selector: str | None = None, scrolls: int = 0) -> str:
        """Navigate to url and return the rendered page HTML."""
        ...

    def storage_state(self) -> dict:
        """Current cookies/localStorage, so a refreshed session can be re-saved."""
        ...

    def close(self) -> None: ...


class FakeBrowserDriver:
    """Test double: serves canned HTML per URL and records navigation.

    `pages` maps an exact URL (or a substring, checked after exact) to HTML.
    `default_html` is returned for any unmatched URL.
    """

    def __init__(self, pages: dict[str, str] | None = None, *, default_html: str = '',
                 state: dict | None = None):
        self.pages = pages or {}
        self.default_html = default_html
        self._state = state or {'cookies': [], 'origins': []}
        self.visited: list[str] = []
        self.started = False

    def start(self, *, headless: bool = True, storage_state: dict | None = None) -> None:
        self.started = True
        if storage_state:
            self._state = storage_state

    def goto(self, url: str, *, wait_selector: str | None = None, scrolls: int = 0) -> str:
        self.visited.append(url)
        if url in self.pages:
            return self.pages[url]
        for fragment, html in self.pages.items():
            if fragment in url:
                return html
        return self.default_html

    def storage_state(self) -> dict:
        return self._state

    def close(self) -> None:
        self.started = False


class PlaywrightDriver:
    """Real Chromium driver. Requires `playwright install chromium` at deploy.

    Honours a per-navigation politeness delay and human-like scrolling for the
    lazy-loaded result lists these portals use.
    """

    def __init__(self, *, min_delay_seconds: float = 1.5, user_agent: str | None = None):
        self.min_delay_seconds = min_delay_seconds
        self.user_agent = user_agent
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None

    def start(self, *, headless: bool = True, storage_state: dict | None = None) -> None:
        from playwright.sync_api import sync_playwright  # lazy — keeps imports/tests browser-free

        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=headless)
        self._context = self._browser.new_context(
            storage_state=storage_state or None,
            user_agent=self.user_agent,
        )
        self._page = self._context.new_page()

    def goto(self, url: str, *, wait_selector: str | None = None, scrolls: int = 0) -> str:
        time.sleep(self.min_delay_seconds + random.uniform(0, 0.75))  # polite, human-ish
        self._page.goto(url, wait_until='domcontentloaded')
        if wait_selector:
            try:
                self._page.wait_for_selector(wait_selector, timeout=10_000)
            except Exception:  # noqa: BLE001 - missing selector is not fatal to scraping
                logger.info('wait_selector %r not found on %s', wait_selector, url)
        for _ in range(scrolls):
            self._page.mouse.wheel(0, 2_400)
            time.sleep(0.6 + random.uniform(0, 0.6))
        return self._page.content()

    def storage_state(self) -> dict:
        return self._context.storage_state()

    def close(self) -> None:
        for closer in (self._context, self._browser):
            try:
                if closer:
                    closer.close()
            except Exception:  # noqa: BLE001
                pass
        if self._pw:
            try:
                self._pw.stop()
            except Exception:  # noqa: BLE001
                pass
