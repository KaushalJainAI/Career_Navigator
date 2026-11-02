import hashlib

from django.db.models import Q
from rest_framework import filters, generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import JobPosting, Source
from .serializers import JobPostingSerializer


def visible_jobs(user):
    """Jobs a user may see: everything ingested, plus the manual jobs *they* added,
    minus stealth-mode employer domains."""
    qs = JobPosting.objects.select_related('company', 'source').filter(
        ~Q(raw__has_key='added_by') | Q(raw__added_by=user.id))
    domains = getattr(getattr(user, 'cn_profile', None), 'stealth_domains', []) or []
    if domains:
        qs = qs.exclude(company__domain__in=domains)
    return qs


class JobListView(generics.ListAPIView):
    serializer_class = JobPostingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'company__name', 'location']
    ordering_fields = ['posted_at', 'created_at', 'ghost_risk']

    def get_queryset(self):
        qs = visible_jobs(self.request.user)
        remote = self.request.query_params.get('remote')
        if remote in {'true', '1'}:
            qs = qs.filter(remote=True)
        location = self.request.query_params.get('location')
        if location:
            qs = qs.filter(location__icontains=location)
        # Ghost-Job Shield: let callers cap the ghost-risk of returned jobs.
        max_ghost_risk = self.request.query_params.get('max_ghost_risk')
        if max_ghost_risk is not None:
            try:
                qs = qs.filter(ghost_risk__lte=int(max_ghost_risk))
            except ValueError:
                pass
        return qs


class JobDetailView(generics.RetrieveAPIView):
    serializer_class = JobPostingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return visible_jobs(self.request.user)


class RefreshJobsView(APIView):
    """"Find jobs for me" — pull fresh postings for the user's target roles."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from ingestion.discovery import discover_for_candidate
        from matching.fit import candidate_from_profile
        from profiles.models import StructuredProfile

        profile = StructuredProfile.objects.filter(user=request.user).first()
        candidate = candidate_from_profile(profile)
        if not candidate.titles:
            return Response({'detail': 'Add at least one target role to your profile first.'}, status=400)
        try:
            watch = list(profile.preference.watch_companies or [])
        except Exception:  # noqa: BLE001
            watch = []
        return Response(discover_for_candidate(candidate, watch=watch))


class AddJobView(APIView):
    """Add a job you found anywhere: paste a Greenhouse/Lever/Ashby link and we
    fetch it; for any other site paste the title, company and description."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from applications.models import Application
        from ingestion.services import upsert_postings
        from ingestion.url_import import fetch_job_from_url

        data = request.data
        url = (data.get('url') or '').strip()
        posting = fetch_job_from_url(url) if url else None
        if posting is None:
            title = (data.get('title') or '').strip()
            company = (data.get('company') or '').strip()
            description = (data.get('description') or '').strip()
            if not (title and company and len(description) >= 50):
                return Response({
                    'detail': "We couldn't read that link automatically. Paste the job title, company and description.",
                    'needs_details': True,
                }, status=400)
            location = (data.get('location') or '').strip()
            ext = hashlib.sha1(f'{request.user.id}|{url}|{title}|{company}'.encode()).hexdigest()[:32]
            posting = {
                'external_id': ext, 'title': title[:255], 'description': description,
                'location': location, 'remote': bool(data.get('remote')) or 'remote' in location.lower(),
                'apply_url': url, 'company': {'name': company[:255], 'domain': '', 'ats_type': 'other'},
                'raw': {},
            }
        posting.pop('_source', None)
        posting['raw'] = {**(posting.get('raw') or {}), 'added_by': request.user.id}
        posting['external_id'] = f"u{request.user.id}-{posting['external_id']}"
        source, _ = Source.objects.get_or_create(name='manual', defaults={'kind': 'manual'})
        upsert_postings(source, [posting])
        job = JobPosting.objects.get(source=source, external_id=posting['external_id'])
        app, _ = Application.objects.get_or_create(user=request.user, job=job)
        changed = []
        deadline = (data.get('deadline') or '').strip() if isinstance(data.get('deadline'), str) else ''
        if deadline:
            from datetime import date
            try:
                app.deadline = date.fromisoformat(deadline[:10])
                changed.append('deadline')
            except ValueError:
                pass
        if (data.get('notes') or '').strip():
            app.notes = data['notes'].strip()
            changed.append('notes')
        if changed:
            app.save(update_fields=changed + ['updated_at'])
        out = JobPostingSerializer(job).data
        out['application_id'] = app.id
        return Response(out, status=status.HTTP_201_CREATED)
