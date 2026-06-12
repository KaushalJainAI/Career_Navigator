"""Static registry of supported no-API portals.

Each entry maps a portal name to its scraper class plus the metadata the session
layer needs to turn an env-provided session cookie into a real browser cookie
(name + domain). Kept import-light: scraper classes are referenced lazily via
`get_scraper` so importing this module never pulls in Playwright.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PortalSpec:
    name: str
    display_name: str
    login_url: str
    # The single auth cookie that authenticates a session for this portal, and
    # the domain it must be set on, so an env/UI-provided value can be injected.
    cookie_name: str
    cookie_domain: str
    env_var: str
    source_kind: str = 'scraper'


PORTALS: dict[str, PortalSpec] = {
    'linkedin': PortalSpec(
        name='linkedin', display_name='LinkedIn',
        login_url='https://www.linkedin.com/login',
        cookie_name='li_at', cookie_domain='.linkedin.com',
        env_var='LINKEDIN_SESSION_COOKIE', source_kind='linkedin',
    ),
    'naukri': PortalSpec(
        name='naukri', display_name='Naukri',
        login_url='https://www.naukri.com/nlogin/login',
        cookie_name='nauk_at', cookie_domain='.naukri.com',
        env_var='NAUKRI_SESSION_COOKIE',
    ),
    'unstop': PortalSpec(
        name='unstop', display_name='Unstop',
        login_url='https://unstop.com/login',
        cookie_name='sessionid', cookie_domain='.unstop.com',
        env_var='UNSTOP_SESSION_COOKIE',
    ),
    'ycombinator': PortalSpec(
        name='ycombinator', display_name='Y Combinator (Work at a Startup)',
        login_url='https://www.workatastartup.com/sign_in',
        cookie_name='_waas_session', cookie_domain='.workatastartup.com',
        env_var='YC_SESSION_COOKIE',
    ),
}


def get_scraper(name: str):
    """Lazy scraper-class lookup — avoids importing scraper modules (and through
    them, anything heavy) until a scrape is actually run."""
    if name == 'linkedin':
        from .scrapers.linkedin import LinkedInScraper
        return LinkedInScraper
    if name == 'naukri':
        from .scrapers.naukri import NaukriScraper
        return NaukriScraper
    if name == 'unstop':
        from .scrapers.unstop import UnstopScraper
        return UnstopScraper
    if name == 'ycombinator':
        from .scrapers.ycombinator import YCombinatorScraper
        return YCombinatorScraper
    return None
