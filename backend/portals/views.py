from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PortalAccount, PortalAccountStatus, PortalScrapeRun
from .registry import PORTALS
from .scrapers.base import PortalQuery
from .serializers import (
    PortalScrapeRunSerializer, ScrapeRequestSerializer, StoreSessionSerializer,
)
from .services import _portal_row, run_portal_scrape
from .sessions import env_cookie_for, _state_from_cookie
from .tasks import run_portal_scrape_task


class PortalListView(APIView):
    """Supported portals + this user's session status for each."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        accounts = {
            a.portal.name: a
            for a in PortalAccount.objects.filter(user=request.user).select_related('portal')
        }
        out = []
        for name, spec in PORTALS.items():
            account = accounts.get(name)
            has_session = bool(account and account.has_session()) or bool(env_cookie_for(name))
            out.append({
                'name': name,
                'display_name': spec.display_name,
                'login_url': spec.login_url,
                'connected': has_session,
                'status': account.status if account else PortalAccountStatus.NEEDS_LOGIN,
            })
        return Response({'portals': out, 'scraper_enabled': settings.PORTAL_SCRAPER_ENABLED})


class PortalSessionView(APIView):
    """Store or forget a portal session for the user. Write-only."""

    permission_classes = [IsAuthenticated]

    def post(self, request, name: str):
        spec = PORTALS.get(name)
        if spec is None:
            return Response({'detail': 'Unknown portal.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = StoreSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        state = serializer.validated_data.get('storage_state') \
            or _state_from_cookie(spec, serializer.validated_data['cookie'])

        portal = _portal_row(spec)
        account, _ = PortalAccount.objects.get_or_create(user=request.user, portal=portal)
        account.set_storage_state(state)
        account.save()
        return Response({'status': account.status}, status=status.HTTP_200_OK)

    def delete(self, request, name: str):
        PortalAccount.objects.filter(user=request.user, portal__name=name).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PortalScrapeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, name: str):
        if name not in PORTALS:
            return Response({'detail': 'Unknown portal.'}, status=status.HTTP_404_NOT_FOUND)
        if not settings.PORTAL_SCRAPER_ENABLED:
            return Response({'detail': 'Portal scraping is disabled on this deployment.'},
                            status=status.HTTP_403_FORBIDDEN)
        serializer = ScrapeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        query_kwargs = {
            'keywords': data['keywords'], 'location': data['location'],
            'remote': data['remote'], 'max_results': data['max_results'],
        }

        if settings.RUN_INGESTION_ASYNC:
            task = run_portal_scrape_task.delay(name, request.user.id, **query_kwargs)
            return Response({'queued': True, 'task_id': task.id}, status=status.HTTP_202_ACCEPTED)

        run = run_portal_scrape(name, request.user, PortalQuery(**query_kwargs))
        return Response(PortalScrapeRunSerializer(run).data, status=status.HTTP_200_OK)


class PortalRunListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        runs = PortalScrapeRun.objects.filter(user=request.user).select_related('portal')[:50]
        return Response(PortalScrapeRunSerializer(runs, many=True).data)
