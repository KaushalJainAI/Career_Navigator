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


class FeedView(APIView):
    """Jobs ranked by fit for the current user.

    Query params: q, remote=1, min_fit=0..100, hide_ghost=1 (default: hide
    high ghost-risk), status=new|all (new hides jobs you already applied to /
    dismissed), limit (default 30), offset."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        p = request.query_params
        cand = candidate_for(request.user)
        qs = visible_jobs(request.user)
        q = (p.get('q') or '').strip()
        if q:
            from django.db.models import Q
            qs = qs.filter(Q(title__icontains=q) | Q(company__name__icontains=q) | Q(location__icontains=q))
        if p.get('remote') in {'1', 'true'}:
            qs = qs.filter(remote=True)
        if p.get('hide_ghost', '1') in {'1', 'true'}:
            qs = qs.filter(ghost_risk__lt=60)
        if cand.exclude_companies:
            for name in cand.exclude_companies:
                qs = qs.exclude(company__name__iexact=name)
        apps = {a.job_id: a for a in Application.objects.filter(user=request.user)}
        if p.get('status', 'new') == 'new':
            hidden = [jid for jid, a in apps.items() if a.status not in ('saved',)]
            qs = qs.exclude(pk__in=hidden)
        jobs = list(qs.order_by('-created_at')[:FEED_SCAN_LIMIT])
        total_jobs = visible_jobs(request.user).count()

        texts = {j.pk: tokenize(f'{j.title} {description_to_text(j.description)}') for j in jobs}
        corpus = Corpus(list(texts.values()) or [[]])
        rows = []
        for j in jobs:
            if cand.has_data:
                r = score_fit(cand, title=j.title, description=j.description, location=j.location,
                              remote=j.remote, skills=_job_skills(j), corpus=corpus, job_tokens=texts[j.pk])
            else:
                r = None
            rows.append((j, r))
        try:
            min_fit = int(p.get('min_fit', 0))
        except ValueError:
            min_fit = 0
        if cand.has_data:
            rows = [x for x in rows if x[1]['fit'] >= min_fit]
            rows.sort(key=lambda x: (-x[1]['fit'], x[0].ghost_risk))
        try:
            limit = max(1, min(100, int(p.get('limit', 30))))
            offset = max(0, int(p.get('offset', 0)))
        except ValueError:
            limit, offset = 30, 0
        page = rows[offset:offset + limit]
        results = []
        for j, r in page:
            app = apps.get(j.pk)
            results.append({
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
            })
        return Response({
            'count': len(rows), 'total_jobs': total_jobs, 'has_profile': cand.has_data,
            'results': results,
        })
