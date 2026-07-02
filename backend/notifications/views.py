from django.conf import settings
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Alert, Subscription, WebPushDevice
from .serializers import AlertSerializer, SubscriptionSerializer, WebPushDeviceSerializer
from .webpush import push_enabled


class SubscriptionListCreateView(generics.ListCreateAPIView):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Subscription.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SubscriptionDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Subscription.objects.filter(user=self.request.user)


class AlertListView(generics.ListAPIView):
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Alert.objects.filter(user=self.request.user).select_related('job', 'job__company')


class AlertMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        Alert.objects.filter(pk=pk, user=request.user).update(read=True)
        return Response({'detail': 'Alert marked as read.'})


def _extract_subscription(data):
    """Accept either flat {endpoint, p256dh, auth} or a raw browser
    PushSubscription {endpoint, keys: {p256dh, auth}}."""
    keys = data.get('keys') or {}
    return (
        data.get('endpoint'),
        data.get('p256dh') or keys.get('p256dh'),
        data.get('auth') or keys.get('auth'),
    )


class VapidPublicKeyView(APIView):
    """The browser needs this key to create a push subscription."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'public_key': settings.VAPID_PUBLIC_KEY,
            'enabled': push_enabled(),
        })


class ActivityFeedView(APIView):
    """Unified recent-activity feed for the notification bell (alerts + events)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .activity import build_activity
        return Response(build_activity(request.user))


class PushRegisterView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        endpoint, p256dh, auth = _extract_subscription(request.data)
        if not (endpoint and p256dh and auth):
            return Response(
                {'detail': 'endpoint, p256dh and auth are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        device, created = WebPushDevice.objects.update_or_create(
            user=request.user,
            endpoint=endpoint,
            defaults={'p256dh': p256dh, 'auth': auth},
        )
        return Response(
            WebPushDeviceSerializer(device).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class PushUnregisterView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        endpoint, _, _ = _extract_subscription(request.data)
        qs = WebPushDevice.objects.filter(user=request.user)
        if endpoint:
            qs = qs.filter(endpoint=endpoint)
        deleted, _ = qs.delete()
        return Response({'detail': 'Unsubscribed.', 'removed': deleted})
