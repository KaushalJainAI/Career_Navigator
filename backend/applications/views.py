from rest_framework import generics, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Application, ApplicationEvent, AutoApplySession
from .serializers import ApplicationSerializer


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
