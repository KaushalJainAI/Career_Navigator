"""Fetch the full job description from a posting's apply_url.

Aggregator APIs return teasers, not job descriptions: every Adzuna row is
hard-truncated to exactly 500 characters and Jooble's run ~300. Match scoring,
skill overlap, ghost-risk keyword detection and resume tailoring were all
reasoning over a marketing blurb, which is why ghost-risk scores clustered on
a couple of values instead of spreading.

So we fetch the real page once, on demand (first time someone opens the job),
and cache it on the row. Deliberately conservative: a plain GET with a short
timeout, no JS execution, a hard size cap, and '' on any failure — a posting
whose page we cannot read keeps working off the teaser.
"""

from __future__ import annotations

import logging

import httpx
from datetime import timedelta

from django.utils import timezone
from lxml import html as lxml_html

logger = logging.getLogger(__name__)

TIMEOUT = 10.0
MAX_BYTES = 2_000_000
MAX_CHARS = 20_000
# Chrome UA: several boards return a stub or a consent wall to unknown agents.
USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/124.0 Safari/537.36'
)
# Chrome/nav/footer noise that would otherwise dominate the extracted text.
STRIP_TAGS = ('script', 'style', 'noscript', 'nav', 'header', 'footer', 'svg', 'form')
# A block/consent/JS-stub page still returns 200-ish HTML and can extract to
# more characters than a 500-char teaser, so length alone is not enough to
# decide a scrape is an improvement. These markers only appear on such pages.
BLOCK_MARKERS = (
    'request blocked', 'the request could not be satisfied', 'access denied',
    'are you a robot', 'verify you are human', 'enable javascript',
    'please enable cookies', 'unusual traffic', 'rate limited', 'cloudfront',
)
# Even a genuine page can render as a stub; a real JD is comfortably longer.
MIN_USEFUL_CHARS = 400
# A failed fetch is usually permanent (dead link, login wall) but sometimes
# transient (a board rate-limits a burst of requests). Don't retry on every
# view, but don't give up forever either.
RETRY_FAILED_AFTER = timedelta(days=7)


def html_to_text(html_text: str) -> str:
    """Flatten an HTML document to readable text, largest content block first."""
    if not html_text or not html_text.strip():
        return ''
    try:
        tree = lxml_html.fromstring(html_text)
    except (ValueError, SyntaxError, lxml_html.etree.ParserError):
        return ''
    for tag in STRIP_TAGS:
        for node in tree.findall(f'.//{tag}'):
            parent = node.getparent()
            if parent is not None:
                parent.remove(node)

    # Prefer a semantic container when the page offers one; a JD is nearly
    # always inside <main>/<article>, and taking it avoids sidebar junk.
    best = ''
    for xpath in ('//main', '//article', "//*[@role='main']"):
        for node in tree.xpath(xpath):
            candidate = _clean(node.text_content())
            if len(candidate) > len(best):
                best = candidate
    if len(best) >= 400:
        return best[:MAX_CHARS]
    return _clean(tree.text_content())[:MAX_CHARS]


def looks_unusable(text: str) -> bool:
    """True for block pages, consent walls and JS stubs masquerading as a JD."""
    if len(text) < MIN_USEFUL_CHARS:
        return True
    head = text[:1500].lower()
    return any(marker in head for marker in BLOCK_MARKERS)


def _clean(text: str) -> str:
    lines = [line.strip() for line in (text or '').splitlines()]
    return '\n'.join(line for line in lines if line)


def candidate_urls(job) -> list[str]:
    """URLs to try for the JD text, best first.

    `apply_url` is chosen for applying, which is not always the best page to
    read: Adzuna's `redirect_url` is a click-tracking interstitial that only
    forwards via JS, so it extracts to nothing, while `/details/<id>` renders
    the actual description server-side. Prefer the readable one, keep
    apply_url as the fallback.
    """
    urls = []
    raw = job.raw if isinstance(job.raw, dict) else {}
    source_name = job.source.name if job.source_id else ''
    if source_name == 'adzuna' and raw.get('id'):
        urls.append(f'https://www.adzuna.com/details/{raw["id"]}')
    apply_url = (job.apply_url or '').strip()
    if apply_url:
        urls.append(apply_url)
    return [u for u in urls if u.startswith(('http://', 'https://'))]


def fetch_full_description(job, client: httpx.Client | None = None) -> str:
    """Return the full JD text for `job`, or '' if it cannot be retrieved.

    Tries each candidate URL in turn and keeps the longest readable result;
    a board that answers 403 or serves a JS stub falls through to the next.

    `client` is injectable so tests use httpx.MockTransport and never touch
    the network.
    """
    urls = candidate_urls(job)
    if not urls:
        return ''

    owns_client = client is None
    if owns_client:
        client = httpx.Client(
            timeout=TIMEOUT, follow_redirects=True, headers={'User-Agent': USER_AGENT},
        )
    try:
        best = ''
        for url in urls:
            try:
                response = client.get(url)
                response.raise_for_status()
            except (httpx.HTTPError, ValueError) as exc:
                # Never log the URL: some apply_urls carry per-source tokens.
                logger.info('full-description fetch failed for job %s: %s',
                            job.pk, type(exc).__name__)
                continue
            content_type = response.headers.get('content-type', '')
            if content_type and 'html' not in content_type:
                continue
            if len(response.content) > MAX_BYTES:
                continue
            text = html_to_text(response.text)
            if looks_unusable(text):
                continue
            if len(text) > len(best):
                best = text
        return best
    finally:
        if owns_client:
            client.close()


def ensure_full_description(job, client: httpx.Client | None = None) -> str:
    """Fetch-and-cache. Returns the description the app should now use.

    A page we cannot read costs one request, not one per view: `fetched_at` is
    stamped whether or not we got anything. Empty results are retried after
    RETRY_FAILED_AFTER, because failures are not always permanent — a board
    that rate-limits a burst will serve the same URL happily a week later.
    """
    stamped = job.full_description_fetched_at
    if job.full_description:
        return job.full_description
    if stamped is not None and timezone.now() - stamped < RETRY_FAILED_AFTER:
        return job.best_description

    text = fetch_full_description(job, client=client)
    job.full_description_fetched_at = timezone.now()
    # Only accept a result that beats the teaser we already have.
    if len(text) > len(job.description or ''):
        job.full_description = text
    job.save(update_fields=['full_description', 'full_description_fetched_at'])
    return job.best_description
