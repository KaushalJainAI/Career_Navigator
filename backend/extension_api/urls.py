from django.urls import path

from .views import AutofillView, PageContextView, SubmitEventView

urlpatterns = [
    path('page-context/', PageContextView.as_view(), name='ext-page-context'),
    path('autofill/', AutofillView.as_view(), name='ext-autofill'),
    path('submit-event/', SubmitEventView.as_view(), name='ext-submit-event'),
]
