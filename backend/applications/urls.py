from django.urls import path

from .views import (
    ApplicationDetailView,
    ApplicationListCreateView,
    ApproveAutoApplyView,
    DashboardStatsView,
    PrepareApplicationView,
)

urlpatterns = [
    path('', ApplicationListCreateView.as_view(), name='application-list'),
    path('stats/', DashboardStatsView.as_view(), name='application-stats'),
    path('prepare/', PrepareApplicationView.as_view(), name='application-prepare'),
    path('<int:pk>/', ApplicationDetailView.as_view(), name='application-detail'),
    path('<int:pk>/approve/', ApproveAutoApplyView.as_view(), name='application-approve'),
]
