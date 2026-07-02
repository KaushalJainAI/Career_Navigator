from django.urls import path

from .views import AutofillView, PageContextView, ProfileContextView, SubmitEventView

urlpatterns = [
    path('page-context/', PageContextView.as_view(), name='ext-page-context'),
    path('autofill/', AutofillView.as_view(), name='ext-autofill'),
    path('submit-event/', SubmitEventView.as_view(), name='ext-submit-event'),
    path('profile-context/', ProfileContextView.as_view(), name='ext-profile-context'),
]
