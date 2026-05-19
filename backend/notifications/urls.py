from django.urls import path

from .views import AlertListView, PushRegisterView, SubscriptionListCreateView

urlpatterns = [
    path('subscriptions/', SubscriptionListCreateView.as_view(), name='subscription-list'),
    path('alerts/', AlertListView.as_view(), name='alert-list'),
    path('push/register/', PushRegisterView.as_view(), name='push-register'),
]
