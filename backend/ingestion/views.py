from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .tasks import run_source


class RunSourceView(APIView):
    """Admin-only manual trigger. In prod, scheduled by Celery beat."""

    permission_classes = [IsAdminUser]

    def post(self, request, source_name: str):
        result = run_source(source_name, **request.data)
        return Response(result)
