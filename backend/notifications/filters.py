"""Filter DSL — small, deterministic, easy to test.
A `filter_json` looks like:
    {
        'titles': ['engineer', 'developer'],   # any substring match
        'locations': ['remote', 'new york'],
        'remote': True,
        'salary_min': 100000,
        'exclude_companies': ['evilcorp'],
        'keywords': ['python', 'django'],
    }
All present clauses must match. Missing keys are skipped."""

from __future__ import annotations


def match_filter(job, spec: dict) -> bool:
    title = (job.title or '').lower()
    location = (job.location or '').lower()
    desc = (job.description or '').lower()
    company = (job.company.name if job.company_id else '').lower()

    titles = [t.lower() for t in spec.get('titles', []) if t]
    if titles and not any(t in title for t in titles):
        return False

    locations = [t.lower() for t in spec.get('locations', []) if t]
    if locations and not any(t in location for t in locations) and not job.remote:
        return False

    if spec.get('remote') is True and not job.remote:
        return False

    salary_min = spec.get('salary_min')
    if salary_min and (job.salary_max or 0) < salary_min:
        return False

    excludes = [t.lower() for t in spec.get('exclude_companies', []) if t]
    if any(t in company for t in excludes):
        return False

    keywords = [t.lower() for t in spec.get('keywords', []) if t]
    if keywords and not any(k in desc or k in title for k in keywords):
        return False

    return True
