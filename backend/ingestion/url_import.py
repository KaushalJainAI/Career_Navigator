"""Import a single job from a careers-page URL.

Supports the public JSON endpoints of the big ATSs, so pasting a link is
enough for most tech jobs:
  - Greenhouse: boards.greenhouse.io/<board>/jobs/<id>, job-boards.greenhouse.io/..., ?gh_jid=<id>
  - Lever:      jobs.lever.co/<site>/<uuid>
  - Ashby:      jobs.ashbyhq.com/<org>/<uuid>
Anything else returns None and the UI asks the user to paste the description.
"""

from __future__ import annotations

import re

import httpx

from .adapters.base import looks_remote, make_posting, parse_epoch_ms, parse_iso_dt

GH_RE = re.compile(r'(?:job-boards|boards)(?:\.eu)?\.greenhouse\.io/(?:embed/job_app\?for=)?([\w-]+)/jobs/(\d+)')
GH_JID_RE = re.compile(r'[?&]gh_jid=(\d+)')
LEVER_RE = re.compile(r'jobs\.(?:eu\.)?lever\.co/([\w.-]+)/([0-9a-f-]{36})')
ASHBY_RE = re.compile(r'jobs\.ashbyhq\.com/([\w.%-]+)/([0-9a-f-]{36})')


def detect(url: str) -> tuple[str, str, str] | None:
    if m := GH_RE.search(url):
        return 'greenhouse', m.group(1), m.group(2)
    if m := LEVER_RE.search(url):
        return 'lever', m.group(1), m.group(2)
    if m := ASHBY_RE.search(url):
        return 'ashby', m.group(1), m.group(2)
    return None


def fetch_job_from_url(url: str, *, transport: httpx.BaseTransport | None = None) -> dict | None:
    found = detect(url or '')
    if not found:
        return None
    kind, org, job_id = found
    try:
        with httpx.Client(timeout=15.0, transport=transport, follow_redirects=True) as client:
            if kind == 'greenhouse':
                r = client.get(f'https://boards-api.greenhouse.io/v1/boards/{org}/jobs/{job_id}')
                r.raise_for_status()
                row = r.json()
                loc = (row.get('location') or {}).get('name', '')
                return make_posting(
                    external_id=row.get('id'), title=row.get('title'), description=row.get('content', ''),
                    location=loc, remote=looks_remote(loc), apply_url=row.get('absolute_url') or url,
                    posted_at=parse_iso_dt(row.get('updated_at')),
                    company_name=org.replace('-', ' ').title(), ats_type='greenhouse', raw={'id': row.get('id')},
                ) | {'_source': 'greenhouse'}
            if kind == 'lever':
                r = client.get(f'https://api.lever.co/v0/postings/{org}/{job_id}', params={'mode': 'json'})
                r.raise_for_status()
                row = r.json()
                loc = (row.get('categories') or {}).get('location', '')
                return make_posting(
                    external_id=row.get('id'), title=row.get('text'),
                    description=row.get('descriptionPlain') or row.get('description', ''),
                    location=loc, remote=(row.get('workplaceType') or '').lower() == 'remote' or looks_remote(loc),
                    apply_url=row.get('applyUrl') or row.get('hostedUrl') or url,
                    posted_at=parse_epoch_ms(row.get('createdAt')),
                    company_name=org.replace('-', ' ').title(), ats_type='lever', raw={'id': row.get('id')},
                ) | {'_source': 'lever'}
            if kind == 'ashby':
                r = client.get(f'https://api.ashbyhq.com/posting-api/job-board/{org}',
                               params={'includeCompensation': 'true'})
                r.raise_for_status()
                for row in r.json().get('jobs', []):
                    if row.get('id') == job_id or job_id in (row.get('jobUrl') or ''):
                        loc = row.get('location', '')
                        return make_posting(
                            external_id=row.get('id'), title=row.get('title'),
                            description=row.get('descriptionHtml') or row.get('descriptionPlain', ''),
                            location=loc, remote=bool(row.get('isRemote')) or looks_remote(loc),
                            apply_url=row.get('applyUrl') or row.get('jobUrl') or url,
                            posted_at=parse_iso_dt(row.get('publishedAt')),
                            company_name=org.replace('-', ' ').replace('%20', ' ').title(), ats_type='other',
                            raw={'id': row.get('id')},
                        ) | {'_source': 'ashby'}
    except (httpx.HTTPError, ValueError):
        return None
    return None
