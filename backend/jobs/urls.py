from django.urls import path

from .views import AddJobView, JobDetailView, JobListView, RefreshJobsView

urlpatterns = [
    path('', JobListView.as_view(), name='job-list'),
    path('refresh/', RefreshJobsView.as_view(), name='job-refresh'),
    path('add/', AddJobView.as_view(), name='job-add'),
    path('<int:pk>/', JobDetailView.as_view(), name='job-detail'),
]
