from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from applications.models import Application
from jobs.ghost import band_for
from jobs.text import description_to_text
from jobs.views import visible_jobs
from profiles.models import StructuredProfile
from resumes.models import Resume

from .fit import Candidate, Corpus, candidate_from_parsed, candidate_from_profile, job_skill_weights, score_fit, tokenize
from .models import MatchScore
from .serializers import MatchScoreSerializer

FEED_SCAN_LIMIT = 1500


def candidate_for(user) -> Candidate:
    profile = StructuredProfile.objects.filter(user=user).prefetch_related(
        'skills', 'experiences', 'projects').first()
    cand = candidate_from_profile(profile)
    if cand.has_data:
        return cand
    resume = Resume.objects.filter(user=user, is_master=True).first() or \
        Resume.objects.filter(user=user, parse_status='done').order_by('-created_at').first()
    if resume and resume.parsed_json:
        return candidate_from_parsed(resume.parsed_json)
    return cand


def _job_skills(job) -> dict:
    if job.skills:
        return job.skills
    weights = job_skill_weights(job.title, job.description)
    if weights:
        type(job).objects.filter(pk=job.pk).update(skills=weights)
    return weights


class JobMatchView(APIView):
    """Fit of the current user against one job, with reasons. Cached in MatchScore."""

    permission_classes = [IsAuthenticated]

    def get(self, request, job_id: int):
        job = get_object_or_404(visible_jobs(request.user), pk=job_id)
        cand = candidate_for(request.user)
        if not cand.has_data:
            return Response({'detail': 'Upload your résumé or fill in your profile first.'}, status=400)
        # IDF over a sample of the catalogue so common words don't dominate.
        sample = list(visible_jobs(request.user).order_by('-created_at').values_list('title', 'description')[:300])
        corpus = Corpus([tokenize(f'{t} {description_to_text(d)}') for t, d in sample] or [[]])
        result = score_fit(cand, title=job.title, description=job.description, location=job.location,
                           remote=job.remote, skills=_job_skills(job), corpus=corpus)
        score, _ = MatchScore.objects.update_or_create(
            user=request.user, job=job,
            defaults={
                'score': result['score'],
                'breakdown': result['breakdown'],
                'gaps': result['missing_skills'],
                'matched_skills': result['matched_skills'],
                'explanation': result['explanation'],
                'model_version': result['model_version'],
            },
        )
        data = MatchScoreSerializer(score).data
        data.update({'fit': result['fit'], 'verdict': result['verdict'],
                     'missing_skills': result['missing_skills']})
        return Response(data)


def rank_for_user(user, *, q: str = '', remote: bool = False, hide_ghost: bool = True,
                  only_new: bool = True, min_fit: int = 0) -> tuple[list, dict, Candidate]:
    """Score every visible job for `user`; returns (rows, applications_by_job, candidate).
    Each row is (job, fit_result | None), sorted best-first."""
    from django.db.models import Q

    cand = candidate_for(user)
    qs = visible_jobs(user)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(company__name__icontains=q) | Q(location__icontains=q))
    if remote:
        qs = qs.filter(remote=True)
    if hide_ghost:
        qs = qs.filter(ghost_risk__lt=60)
    for name in cand.exclude_companies:
        qs = qs.exclude(company__name__iexact=name)
    apps = {a.job_id: a for a in Application.objects.filter(user=user)}
    if only_new:
        qs = qs.exclude(pk__in=[jid for jid, a in apps.items() if a.status != 'saved'])
    jobs = list(qs.order_by('-created_at')[:FEED_SCAN_LIMIT])
    texts = {j.pk: tokenize(f'{j.title} {description_to_text(j.description)}') for j in jobs}
    corpus = Corpus(list(texts.values()) or [[]])
    rows = []
    for j in jobs:
        r = score_fit(cand, title=j.title, description=j.description, location=j.location, remote=j.remote,
                      skills=_job_skills(j), corpus=corpus, job_tokens=texts[j.pk]) if cand.has_data else None
        rows.append((j, r))
    if cand.has_data:
        rows = [x for x in rows if x[1]['fit'] >= min_fit]
        rows.sort(key=lambda x: (-x[1]['fit'], x[0].ghost_risk))
    return rows, apps, cand


def feed_row(j, r, app) -> dict:
    return {
        'id': j.pk, 'title': j.title,
        'company': {'id': j.company_id, 'name': j.company.name, 'domain': j.company.domain},
        'location': j.location, 'remote': j.remote, 'apply_url': j.apply_url,
        'posted_at': j.posted_at, 'created_at': j.created_at,
        'salary_min': j.salary_min, 'salary_max': j.salary_max, 'salary_currency': j.salary_currency,
        'source': j.source.name,
        'ghost_risk': j.ghost_risk, 'ghost_band': band_for(j.ghost_risk),
        'fit': r['fit'] if r else None, 'verdict': r['verdict'] if r else None,
        'matched_skills': r['matched_skills'][:6] if r else [],
        'missing_skills': r['missing_skills'][:4] if r else [],
        'reasons': r['explanation'][:3] if r else [],
        'application': {'id': app.id, 'status': app.status} if app else None,
    }


class FeedView(APIView):
    """Jobs ranked by fit for the current user.

    Query params: q, remote=1, min_fit=0..100, hide_ghost=1 (default: hide
    high ghost-risk), status=new|all (new hides jobs you already applied to /
    dismissed), limit (default 30), offset."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        p = request.query_params
        try:
            min_fit = int(p.get('min_fit', 0))
        except ValueError:
            min_fit = 0
        rows, apps, cand = rank_for_user(
            request.user, q=(p.get('q') or '').strip(), remote=p.get('remote') in {'1', 'true'},
            hide_ghost=p.get('hide_ghost', '1') in {'1', 'true'}, only_new=p.get('status', 'new') == 'new',
            min_fit=min_fit)
        try:
            limit = max(1, min(100, int(p.get('limit', 30))))
            offset = max(0, int(p.get('offset', 0)))
        except ValueError:
            limit, offset = 30, 0
        page = rows[offset:offset + limit]
        return Response({
            'count': len(rows), 'total_jobs': visible_jobs(request.user).count(),
            'has_profile': cand.has_data,
            'results': [feed_row(j, r, apps.get(j.pk)) for j, r in page],
        })
