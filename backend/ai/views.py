from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .providers import ai_status


class AIStatusView(APIView):
    """Which AI engine powers the app right now (or deterministic mode)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(ai_status())
