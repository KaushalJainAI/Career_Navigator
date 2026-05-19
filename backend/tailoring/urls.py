from django.urls import path

from .views import DraftCoverLetterView, TailorResumeView

urlpatterns = [
    path('resume/', TailorResumeView.as_view(), name='tailor-resume'),
    path('cover-letter/', DraftCoverLetterView.as_view(), name='tailor-cover-letter'),
]
