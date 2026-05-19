from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Alert, Subscription, WebPushDevice
from .serializers import AlertSerializer, SubscriptionSerializer, WebPushDeviceSerializer


class SubscriptionListCreateView(generics.ListCreateAPIView):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Subscription.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AlertListView(generics.ListAPIView):
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Alert.objects.filter(user=self.request.user).select_related('job', 'job__company')


class PushRegisterView(generics.CreateAPIView):
    serializer_class = WebPushDeviceSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
