from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from billing.services import charge
from jobs.ghost import band_for
from jobs.models import JobPosting
from matching.models import MatchScore

from .analytics import build_response_analytics
from .models import Application, ApplicationEvent, ApplicationStatus, AutoApplySession, AutoApplyTier, Goal, Todo
from .serializers import ApplicationSerializer, GoalSerializer, TodoSerializer


class ApplicationListCreateView(generics.ListCreateAPIView):
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Application.objects.filter(user=self.request.user).select_related('job', 'auto_apply_session')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ApplicationDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Application.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.save()
        ApplicationEvent.objects.create(
            application=instance,
            type='status_changed',
            payload={'status': instance.status},
        )


class ApproveAutoApplyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int):
        app = Application.objects.get(pk=pk, user=request.user)
        session = app.auto_apply_session or AutoApplySession.objects.create(user=request.user)
        app.auto_apply_session = session
        app.save(update_fields=['auto_apply_session', 'updated_at'])
        token = session.issue_approval_token()
        ApplicationEvent.objects.create(application=app, type='approval_issued', payload={})
        return Response({'approval_token': token}, status=status.HTTP_200_OK)


class PrepareApplicationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        job_id = request.data.get('job_id') or request.data.get('job')
        tier = request.data.get('tier') or request.data.get('tier_used') or AutoApplyTier.ASSIST
        if tier not in AutoApplyTier.values:
            return Response({'detail': 'Unknown apply tier.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            job = JobPosting.objects.select_related('company').get(pk=job_id)
        except JobPosting.DoesNotExist:
            return Response({'detail': 'Job not found.'}, status=status.HTTP_404_NOT_FOUND)

        app, created = Application.objects.get_or_create(
            user=request.user,
            job=job,
            defaults={'tier_used': tier},
        )
        app.tier_used = tier
        app.status = self._status_for_tier(tier)
        update_fields = ['tier_used', 'status', 'updated_at']

        approval_token = ''
        if tier == AutoApplyTier.AUTONOMOUS:
            # Charge once per application, when the autonomous session is first set up.
            if app.auto_apply_session is None:
                charge(request.user, 'autonomous_apply', meta={'application_id': app.id})
            session = app.auto_apply_session or AutoApplySession.objects.create(
                user=request.user,
                paused_reason='Review generated application before submit.',
            )
            approval_token = session.issue_approval_token()
            app.auto_apply_session = session
            update_fields.append('auto_apply_session')

        app.save(update_fields=update_fields)
        ghost_band = band_for(job.ghost_risk)
        ApplicationEvent.objects.create(
            application=app,
            type=f'{tier}_prepared',
            payload={
                'created': created,
                'apply_url': job.apply_url,
                'requires_extension': tier == AutoApplyTier.AUTOFILL,
                'requires_approval': tier == AutoApplyTier.AUTONOMOUS,
                'ghost_risk': job.ghost_risk,
                'ghost_band': ghost_band,
            },
        )

        return Response({
            'application': ApplicationSerializer(app).data,
            'tier': tier,
            'status': app.status,
            'apply_url': job.apply_url,
            'approval_token': approval_token,
            'ghost_risk': job.ghost_risk,
            'ghost_band': ghost_band,
            'ghost_reasons': job.ghost_reasons,
            'next_actions': self._next_actions(tier, job, ghost_band),
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @staticmethod
    def _status_for_tier(tier: str) -> str:
        if tier == AutoApplyTier.ASSIST:
            return ApplicationStatus.SAVED
        return ApplicationStatus.READY

    @staticmethod
    def _next_actions(tier: str, job: JobPosting, ghost_band: str = 'low') -> list[str]:
        if tier == AutoApplyTier.ASSIST:
            actions = [
                'Review the job description and match gaps.',
                'Generate a tailored resume or cover letter.',
                'Open the apply link when ready.',
            ]
        elif tier == AutoApplyTier.AUTOFILL:
            actions = [
                'Open the apply link in a browser with the Career Navigator extension installed.',
                'Use extension autofill, review every field, then submit yourself.',
            ]
        else:
            actions = [
                'Review the prepared application package.',
                'Approve only after confirming every field is accurate.',
                f'Application is paused before submit for {job.company.name}.',
            ]
        # Ghost-Job Shield: caution the user before they spend effort on a
        # likely ghost job, and put it first so it isn't missed.
        if ghost_band == 'high':
            actions.insert(0, 'Caution: high ghost-job risk — verify this role is genuinely open before applying.')
        return actions


class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        applications = Application.objects.filter(user=request.user)
        active_statuses = [
            ApplicationStatus.SAVED,
            ApplicationStatus.TAILORED,
            ApplicationStatus.READY,
            ApplicationStatus.APPLIED,
            ApplicationStatus.PHONE,
            ApplicationStatus.ONSITE,
        ]
        return Response({
            'active_applications': applications.filter(status__in=active_statuses).count(),
            'new_matches': MatchScore.objects.filter(user=request.user).count(),
            'interviews_ready': applications.filter(
                status__in=[ApplicationStatus.PHONE, ApplicationStatus.ONSITE],
            ).count(),
            'offers_received': applications.filter(status=ApplicationStatus.OFFER).count(),
            'saved_jobs': applications.filter(status=ApplicationStatus.SAVED).count(),
            'total_jobs': JobPosting.objects.count(),
        })


class ResponseAnalyticsView(APIView):
    """Funnel + response-rate analytics over the user's applications, including a
    per-tier breakdown (assist / autofill / autonomous) and average days to a
    first interview response."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        applications = Application.objects.filter(user=request.user).prefetch_related('events')
        return Response(build_response_analytics(applications))


class TodoListCreateView(generics.ListCreateAPIView):
    serializer_class = TodoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Todo.objects.filter(user=self.request.user).select_related('application', 'application__job')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TodoDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TodoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Todo.objects.filter(user=self.request.user)


class GoalListCreateView(generics.ListCreateAPIView):
    serializer_class = GoalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class GoalDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = GoalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user)
