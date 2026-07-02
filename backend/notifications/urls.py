from django.urls import path

from .views import (
    ActivityFeedView,
    AlertListView,
    AlertMarkReadView,
    PushRegisterView,
    PushUnregisterView,
    SubscriptionDetailView,
    SubscriptionListCreateView,
    VapidPublicKeyView,
)

urlpatterns = [
    path('subscriptions/', SubscriptionListCreateView.as_view(), name='subscription-list'),
    path('subscriptions/<int:pk>/', SubscriptionDetailView.as_view(), name='subscription-detail'),
    path('alerts/', AlertListView.as_view(), name='alert-list'),
    path('activity/', ActivityFeedView.as_view(), name='activity-feed'),
    path('alerts/<int:pk>/read/', AlertMarkReadView.as_view(), name='alert-read'),
    path('vapid-public-key/', VapidPublicKeyView.as_view(), name='vapid-public-key'),
    path('push/register/', PushRegisterView.as_view(), name='push-register'),
    path('push/unregister/', PushUnregisterView.as_view(), name='push-unregister'),
]
