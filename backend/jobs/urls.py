from django.urls import path

from .views import JobBreakdownView, JobDetailView, JobListView, JobRefreshView

urlpatterns = [
    path('', JobListView.as_view(), name='job-list'),
    path('refresh/', JobRefreshView.as_view(), name='job-refresh'),
    path('<int:pk>/', JobDetailView.as_view(), name='job-detail'),
    path('<int:pk>/breakdown/', JobBreakdownView.as_view(), name='job-breakdown'),
]
