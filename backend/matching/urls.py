from django.urls import path

from .views import JobMatchView

urlpatterns = [
    path('jobs/<int:job_id>/', JobMatchView.as_view(), name='match-job'),
]
