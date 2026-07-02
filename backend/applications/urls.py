from django.urls import path

from .views import (
    ApplicationDetailView,
    ApplicationListCreateView,
    ApproveAutoApplyView,
    DashboardStatsView,
    GoalDetailView,
    GoalListCreateView,
    PrepareApplicationView,
    ResponseAnalyticsView,
    TodoDetailView,
    TodoListCreateView,
)

urlpatterns = [
    path('', ApplicationListCreateView.as_view(), name='application-list'),
    path('stats/', DashboardStatsView.as_view(), name='application-stats'),
    path('analytics/', ResponseAnalyticsView.as_view(), name='application-analytics'),
    path('prepare/', PrepareApplicationView.as_view(), name='application-prepare'),
    path('todos/', TodoListCreateView.as_view(), name='todo-list'),
    path('todos/<int:pk>/', TodoDetailView.as_view(), name='todo-detail'),
    path('goals/', GoalListCreateView.as_view(), name='goal-list'),
    path('goals/<int:pk>/', GoalDetailView.as_view(), name='goal-detail'),
    path('<int:pk>/', ApplicationDetailView.as_view(), name='application-detail'),
    path('<int:pk>/approve/', ApproveAutoApplyView.as_view(), name='application-approve'),
]
