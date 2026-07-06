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
    # --- Added portals ---------------------------------------------------------
    # cookie_name/cookie_domain are best-effort defaults for the single-operator
    # env-cookie path; verify each against the live site (DevTools → Application →
    # Cookies) before relying on it. The per-user session-import UI stores a full
    # Playwright storage_state and doesn't depend on these names.
    'instahyre': PortalSpec(
        name='instahyre', display_name='Instahyre',
        login_url='https://www.instahyre.com/login/',
        cookie_name='sessionid', cookie_domain='.instahyre.com',
        env_var='INSTAHYRE_SESSION_COOKIE',
    ),
    'wellfound': PortalSpec(
        name='wellfound', display_name='Wellfound (AngelList)',
        login_url='https://wellfound.com/login',
        cookie_name='_wellfound', cookie_domain='.wellfound.com',
        env_var='WELLFOUND_SESSION_COOKIE',
    ),
    'shine': PortalSpec(
        name='shine', display_name='Shine',
        login_url='https://www.shine.com/myshine/login',
        cookie_name='sessionid', cookie_domain='.shine.com',
        env_var='SHINE_SESSION_COOKIE',
    ),
    'indeed': PortalSpec(
        name='indeed', display_name='Indeed',
        login_url='https://secure.indeed.com/auth',
        cookie_name='CTK', cookie_domain='.indeed.com',
        env_var='INDEED_SESSION_COOKIE',
    ),
    'timesjobs': PortalSpec(
        name='timesjobs', display_name='TimesJobs',
        login_url='https://www.timesjobs.com/candidate/login-home.html',
        cookie_name='JSESSIONID', cookie_domain='.timesjobs.com',
        env_var='TIMESJOBS_SESSION_COOKIE',
    ),
    'foundit': PortalSpec(
        name='foundit', display_name='Foundit (Monster)',
        login_url='https://www.foundit.in/seeker/login',
        cookie_name='SEEKER_ID', cookie_domain='.foundit.in',
        env_var='FOUNDIT_SESSION_COOKIE',
    ),
    'cutshort': PortalSpec(
        name='cutshort', display_name='Cutshort',
        login_url='https://cutshort.io/login',
        cookie_name='connect.sid', cookie_domain='.cutshort.io',
        env_var='CUTSHORT_SESSION_COOKIE',
    ),
    'hirect': PortalSpec(
        name='hirect', display_name='Hirect',
        login_url='https://www.hirect.in/login',
        cookie_name='token', cookie_domain='.hirect.in',
        env_var='HIRECT_SESSION_COOKIE',
    ),
    'internshala': PortalSpec(
        name='internshala', display_name='Internshala',
        login_url='https://internshala.com/login/user',
        cookie_name='sessionid', cookie_domain='.internshala.com',
        env_var='INTERNSHALA_SESSION_COOKIE',
    ),
    'glassdoor': PortalSpec(
        name='glassdoor', display_name='Glassdoor',
        login_url='https://www.glassdoor.com/profile/login_input.htm',
        cookie_name='GDSession', cookie_domain='.glassdoor.com',
        env_var='GLASSDOOR_SESSION_COOKIE',
    ),
}


# name -> (scraper module under .scrapers, class name). Kept as data so adding a
# portal is one registry entry + one entry here, and imports stay lazy.
_SCRAPER_CLASSES: dict[str, tuple[str, str]] = {
    'linkedin': ('linkedin', 'LinkedInScraper'),
    'naukri': ('naukri', 'NaukriScraper'),
    'unstop': ('unstop', 'UnstopScraper'),
    'ycombinator': ('ycombinator', 'YCombinatorScraper'),
    'instahyre': ('instahyre', 'InstahyreScraper'),
    'wellfound': ('wellfound', 'WellfoundScraper'),
    'shine': ('shine', 'ShineScraper'),
    'indeed': ('indeed', 'IndeedScraper'),
    'timesjobs': ('timesjobs', 'TimesJobsScraper'),
    'foundit': ('foundit', 'FounditScraper'),
    'cutshort': ('cutshort', 'CutshortScraper'),
    'hirect': ('hirect', 'HirectScraper'),
    'internshala': ('internshala', 'InternshalaScraper'),
    'glassdoor': ('glassdoor', 'GlassdoorScraper'),
}


def get_scraper(name: str):
    """Lazy scraper-class lookup — avoids importing scraper modules (and through
    them, anything heavy) until a scrape is actually run."""
    entry = _SCRAPER_CLASSES.get(name)
    if entry is None:
        return None
    import importlib

    module = importlib.import_module(f'.scrapers.{entry[0]}', __package__)
    return getattr(module, entry[1])
