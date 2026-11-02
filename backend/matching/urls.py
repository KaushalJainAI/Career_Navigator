from django.urls import path

from .views import FeedView, JobMatchView

urlpatterns = [
    path('feed/', FeedView.as_view(), name='match-feed'),
    path('jobs/<int:job_id>/', JobMatchView.as_view(), name='match-job'),
]
