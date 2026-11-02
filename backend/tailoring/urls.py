from django.urls import path

from .views import (
    CoverLetterEditView,
    DraftCoverLetterView,
    ExportResumeView,
    TailoredResumeEditView,
    TailorResumeView,
)

urlpatterns = [
    path('resume/', TailorResumeView.as_view(), name='tailor-resume'),
    path('resume/export/', ExportResumeView.as_view(), name='export-resume'),
    path('resume/<int:pk>/', TailoredResumeEditView.as_view(), name='tailor-resume-edit'),
    path('cover-letter/', DraftCoverLetterView.as_view(), name='tailor-cover-letter'),
    path('cover-letter/<int:pk>/', CoverLetterEditView.as_view(), name='tailor-cover-letter-edit'),
]
