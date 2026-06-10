from django.urls import path

from .views import AlertListView, AlertMarkReadView, PushRegisterView, SubscriptionDetailView, SubscriptionListCreateView

urlpatterns = [
    path('subscriptions/', SubscriptionListCreateView.as_view(), name='subscription-list'),
    path('subscriptions/<int:pk>/', SubscriptionDetailView.as_view(), name='subscription-detail'),
    path('alerts/', AlertListView.as_view(), name='alert-list'),
    path('alerts/<int:pk>/read/', AlertMarkReadView.as_view(), name='alert-read'),
    path('push/register/', PushRegisterView.as_view(), name='push-register'),
]
