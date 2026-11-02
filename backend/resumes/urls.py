from django.urls import path

from .views import ResumeDetailView, ResumeImportTextView, ResumeListCreateView, ResumeMakeMasterView

urlpatterns = [
    path('', ResumeListCreateView.as_view(), name='resume-list'),
    path('import-text/', ResumeImportTextView.as_view(), name='resume-import-text'),
    path('<int:pk>/', ResumeDetailView.as_view(), name='resume-detail'),
    path('<int:pk>/make-master/', ResumeMakeMasterView.as_view(), name='resume-make-master'),
]
