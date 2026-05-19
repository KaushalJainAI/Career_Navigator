"""Endpoints consumed by the MV3 browser extension during assist/autofill tiers.
Phase 2 fleshes these out; Phase 1 ships the skeletons so the extension can compile."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from applications.models import Application
from jobs.models import Company, JobPosting, Source
from profiles.models import StructuredProfile


class PageContextView(APIView):
    """The extension's content script POSTs the URL + parsed JD it sees.
    We upsert a JobPosting so the user can act on it from the app."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        url = request.data.get('url', '')
        title = request.data.get('title', '')
        description = request.data.get('description', '')
        company_name = request.data.get('company', '')
        ats_type = request.data.get('ats_type', 'other')
        if not (url and title):
            return Response({'detail': 'url and title required'}, status=400)

        source, _ = Source.objects.get_or_create(name='extension', kind='scraper')
        company, _ = Company.objects.get_or_create(
            name=company_name or 'Unknown', domain='', defaults={'ats_type': ats_type}
        )
        job, _ = JobPosting.objects.update_or_create(
            source=source, external_id=url,
            defaults={'title': title, 'description': description,
                      'apply_url': url, 'company': company},
        )
        return Response({'job_id': job.id})


class AutofillView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        job_id = request.query_params.get('job_id')
        try:
            app = Application.objects.get(job_id=job_id, user=request.user)
        except Application.DoesNotExist:
            app = None
        profile = StructuredProfile.objects.filter(user=request.user).first()
        return Response({
            'application_id': app.id if app else None,
            'fields': {
                'full_name': getattr(profile, 'full_name', '') if profile else '',
                'email': request.user.email,
                'phone': getattr(profile, 'phone', '') if profile else '',
                'linkedin': getattr(profile, 'linkedin', '') if profile else '',
                'github': getattr(profile, 'github', '') if profile else '',
            },
        })


class SubmitEventView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # The extension lets the user know we logged the submit. Full audit goes
        # via applications.ApplicationEvent (Phase 2).
        return Response({'ok': True})
