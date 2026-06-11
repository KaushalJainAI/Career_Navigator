"""Ghost-Job Shield — deterministic ghost-risk scoring for a JobPosting.

No ML, no network: a pure-Python rule set over signals the ingestion layer
already tracks (idempotent `(source, external_id)` upsert + liveness fields).
Signals, per docs/competitive-landscape.md §6.5:

- staleness: same copy unchanged for >45 / >60 days (`first_seen_at` resets
  whenever the JD text or salary changes, so age = age of *this* copy);
- repost cycles: identical content fingerprint seen under other
  source/external_id pairs (take-down-and-repost);
- missing salary range;
- evergreen / talent-pool language (req with no specific role to fill);
- JD red-flag language (subsumes the planned red-flag detector).

`assess_ghost_risk` returns {'score': 0-100, 'band': low|medium|high,
'reasons': [...]}. Thresholds live here only — callers derive the band
from this module, never re-hardcode it.
"""

from __future__ import annotations

import hashlib
import re

from django.utils import timezone

STALE_DAYS = 45
VERY_STALE_DAYS = 60

MEDIUM_BAND = 30
HIGH_BAND = 60

EVERGREEN_PHRASES = (
    'always hiring',
    'always looking',
    'evergreen',
    'talent pool',
    'talent community',
    'talent network',
    'future opportunities',
    'general application',
    'pipeline requisition',
    'ongoing recruitment',
    'expression of interest',
)

RED_FLAG_PHRASES = (
    'rockstar',
    'ninja',
    'work hard play hard',
    'wear many hats',
    'fast-paced environment',
    'unpaid',
    'thrives under pressure',
    'like a family',
)

_TAG_RE = re.compile(r'<[^>]+>')
_WS_RE = re.compile(r'\s+')


def _plain(text: str | None) -> str:
    """HTML-stripped, whitespace-collapsed, lower-cased text."""
    return _WS_RE.sub(' ', _TAG_RE.sub(' ', text or '')).strip().lower()


def content_fingerprint(title, description, salary_min=None, salary_max=None) -> str:
    """Stable hash of the visible posting content + salary band.

    Two postings with identical copy (modulo HTML/whitespace/case) hash the
    same, which is how repost cycles are detected across runs and sources.
    """
    body = f'{_plain(title)}\n{_plain(description)}|{salary_min or ""}|{salary_max or ""}'
    return hashlib.sha256(body.encode('utf-8')).hexdigest()


def band_for(score: int) -> str:
    if score >= HIGH_BAND:
        return 'high'
    if score >= MEDIUM_BAND:
        return 'medium'
    return 'low'


def assess_ghost_risk(*, title, description, salary_min, salary_max,
                      first_seen_at, repost_count=0, now=None) -> dict:
    """Score a posting's likelihood of being a ghost job (0 = clean, 100 = max)."""
    now = now or timezone.now()
    score = 0
    reasons: list[str] = []

    age_days = (now - first_seen_at).days if first_seen_at else 0
    if age_days >= VERY_STALE_DAYS:
        score += 40
        reasons.append(f'Same copy live for {age_days} days (over {VERY_STALE_DAYS})')
    elif age_days >= STALE_DAYS:
        score += 25
        reasons.append(f'Same copy live for {age_days} days (over {STALE_DAYS})')

    if not salary_min and not salary_max:
        score += 20
        reasons.append('No salary range disclosed')

    if repost_count >= 1:
        score += 30
        reasons.append(f'Identical posting reposted {repost_count}x across runs/sources')

    text = f'{_plain(title)} {_plain(description)}'
    evergreen = sorted({p for p in EVERGREEN_PHRASES if p in text})
    if evergreen:
        score += 25
        reasons.append('Evergreen/pipeline language: ' + ', '.join(evergreen))

    flags = sorted({p for p in RED_FLAG_PHRASES if p in text})
    if flags:
        score += min(15, 5 * len(flags))
        reasons.append('JD red-flag language: ' + ', '.join(flags))

    score = min(score, 100)
    return {'score': score, 'band': band_for(score), 'reasons': reasons}
