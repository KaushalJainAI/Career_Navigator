from django.urls import path

from .views import DraftCoverLetterView, ExportResumeView, TailorResumeView

urlpatterns = [
    path('resume/', TailorResumeView.as_view(), name='tailor-resume'),
    path('resume/export/', ExportResumeView.as_view(), name='export-resume'),
    path('cover-letter/', DraftCoverLetterView.as_view(), name='tailor-cover-letter'),
]
