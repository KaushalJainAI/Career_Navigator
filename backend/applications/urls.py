from django.urls import path

from .views import (
    ApplicationDetailView,
    ApplicationListCreateView,
    ApproveAutoApplyView,
    DashboardStatsView,
    FollowedUpView,
    TodayView,
    PrepareApplicationView,
    ResponseAnalyticsView,
)

urlpatterns = [
    path('', ApplicationListCreateView.as_view(), name='application-list'),
    path('stats/', DashboardStatsView.as_view(), name='application-stats'),
    path('today/', TodayView.as_view(), name='application-today'),
    path('analytics/', ResponseAnalyticsView.as_view(), name='application-analytics'),
    path('prepare/', PrepareApplicationView.as_view(), name='application-prepare'),
    path('<int:pk>/', ApplicationDetailView.as_view(), name='application-detail'),
    path('<int:pk>/approve/', ApproveAutoApplyView.as_view(), name='application-approve'),
    path('<int:pk>/followed-up/', FollowedUpView.as_view(), name='application-followed-up'),
]
