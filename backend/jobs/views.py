from rest_framework import filters, generics, status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from django.conf import settings

from ai.providers import configured_model_label, get_configured_llm
from billing.pricing import cost_of
from billing.services import charge, grant

from .enrichment import generate_breakdown
from .models import JobPosting
from .serializers import JobPostingSerializer, JobPostingWriteSerializer


class JobListView(generics.ListCreateAPIView):
    serializer_class = JobPostingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'company__name', 'location']
    ordering_fields = ['posted_at', 'created_at', 'ghost_risk']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return JobPostingWriteSerializer
        return JobPostingSerializer

    def get_queryset(self):
        qs = JobPosting.objects.select_related('company', 'source')
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
        # Honour stealth_domains from the user's UserProfile
        domains = getattr(getattr(self.request.user, 'cn_profile', None), 'stealth_domains', []) or []
        if domains:
            qs = qs.exclude(company__domain__in=domains)
        return qs


class JobDetailView(generics.RetrieveAPIView):
    queryset = JobPosting.objects.select_related('company', 'source')
    serializer_class = JobPostingSerializer
    permission_classes = [IsAuthenticated]


class JobRefreshView(APIView):
    """User-triggered "find new jobs": re-run the configured ingestion sources.

    Hits external job-board APIs, so it's rate-limited per user (see the
    `job_refresh` throttle scope) to protect those quotas — no credit charge,
    discovery stays free. In async deployments it dispatches to Celery and
    returns immediately; otherwise it runs inline and returns the counts."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'job_refresh'

    def post(self, request):
        if getattr(settings, 'RUN_INGESTION_ASYNC', False):
            from ingestion.tasks import run_all_sources
            run_all_sources.delay()
            return Response(
                {'status': 'started',
                 'detail': 'Searching job sources — new roles will appear shortly.'},
                status=status.HTTP_202_ACCEPTED,
            )
        from ingestion.services import run_registered_sources
        totals = run_registered_sources()
        new_jobs = totals.get('new_jobs', 0)
        return Response({
            'status': 'done',
            'new_jobs': new_jobs,
            'updated': totals.get('updated', 0),
            'sources': totals.get('sources', {}),
            'detail': (
                f'Found {new_jobs} new job{"" if new_jobs == 1 else "s"}.'
                if new_jobs else 'No new jobs right now — check back later.'
            ),
        })


class JobBreakdownView(APIView):
    """Generate (or return the cached) AI breakdown for a posting.

    The breakdown is a property of the job, so it's generated once and shared:
    a cache hit is free, only a real LLM generation is charged. We charge before
    the work per the billing convention, and refund if the model gives us nothing
    usable so a user is never billed for a failed generation.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int):
        job = get_object_or_404(JobPosting, pk=pk)
        if job.ai_breakdown:
            return Response(job.ai_breakdown)

        llm = get_configured_llm()
        if llm is None:
            return Response(
                {'detail': 'AI generation is not available right now.'}, status=503)

        charge(request.user, 'job_breakdown', meta={'job': job.id})  # 402 if broke
        breakdown = generate_breakdown(
            job.title, job.company.name, job.description, llm=llm)
        if not breakdown:
            grant(request.user, 'refund', cost_of('job_breakdown'),
                  meta={'job': job.id, 'note': 'job_breakdown generation failed'})
            return Response(
                {'detail': 'Could not generate a breakdown for this posting.'},
                status=502)

        job.ai_breakdown = {**breakdown, 'model': configured_model_label()}
        job.save(update_fields=['ai_breakdown'])
        return Response(job.ai_breakdown)
