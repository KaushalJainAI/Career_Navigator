from django.urls import path

from .views import RunSourceView

urlpatterns = [
    path('run/<str:source_name>/', RunSourceView.as_view(), name='ingestion-run-source'),
]
