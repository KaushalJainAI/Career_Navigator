"""Map adapter output → JobPosting rows, upsert idempotently."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from jobs.ghost import assess_ghost_risk, content_fingerprint
from jobs.models import Company, JobPosting, Source

from .models import IngestionRun


@transaction.atomic
def upsert_postings(source: Source, postings: list[dict]) -> dict:
    created = 0
    updated = 0
    skipped = 0
    now = timezone.now()
    for p in postings:
        if not p.get('external_id') or not p.get('title'):
            skipped += 1
            continue
        company_data = p.get('company') or {}
        company, _ = Company.objects.get_or_create(
            name=company_data.get('name') or 'Unknown',
            domain=company_data.get('domain') or '',
            defaults={'ats_type': company_data.get('ats_type', 'other')},
        )

        # --- Ghost-Job Shield: liveness + repost fingerprinting ---
        fingerprint = content_fingerprint(
            p.get('title', ''), p.get('description', ''),
            p.get('salary_min'), p.get('salary_max'),
        )
        existing = JobPosting.objects.filter(
            source=source, external_id=p['external_id'],
        ).first()
        # first_seen tracks the age of THIS copy: keep it only while the
        # fingerprint is unchanged, otherwise the copy was refreshed.
        if existing and existing.content_fingerprint == fingerprint:
            first_seen = existing.first_seen_at
        else:
            first_seen = now
        # Repost cycle: the same copy living under a different (source,
        # external_id) for the same company is a take-down-and-repost signal.
        repost_count = JobPosting.objects.filter(
            company=company, content_fingerprint=fingerprint,
        ).exclude(source=source, external_id=p['external_id']).count()
        risk = assess_ghost_risk(
            title=p.get('title', ''), description=p.get('description', ''),
            salary_min=p.get('salary_min'), salary_max=p.get('salary_max'),
            first_seen_at=first_seen, repost_count=repost_count, now=now,
        )

        defaults = {
            'company': company,
            'title': p.get('title', ''),
            'description': p.get('description', ''),
            'location': p.get('location', ''),
            'remote': bool(p.get('remote')),
            'salary_min': p.get('salary_min'),
            'salary_max': p.get('salary_max'),
            'salary_currency': p.get('salary_currency', ''),
            'apply_url': p.get('apply_url', ''),
            'posted_at': p.get('posted_at'),
            'raw': p.get('raw', {}),
            'content_fingerprint': fingerprint,
            'first_seen_at': first_seen,
            'last_seen_at': now,
            'repost_count': repost_count,
            'ghost_risk': risk['score'],
            'ghost_reasons': risk['reasons'],
        }
        _, was_created = JobPosting.objects.update_or_create(
            source=source, external_id=p['external_id'], defaults=defaults,
        )
        if was_created:
            created += 1
        else:
            updated += 1
    return {'created': created, 'updated': updated, 'skipped': skipped}


def run_adapter(source: Source, adapter, ctx=None) -> IngestionRun:
    run = IngestionRun.objects.create(source=source)
    try:
        postings = adapter.run(ctx)
        stats = upsert_postings(source, postings)
        run.status = 'success'
        run.stats = stats
    except Exception as exc:  # noqa: BLE001
        run.status = 'failed'
        run.error = str(exc)
    finally:
        run.finished_at = timezone.now()
        run.save()
    return run
