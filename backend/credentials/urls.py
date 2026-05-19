from django.urls import path

from .views import CredentialDetailView, CredentialListCreateView

urlpatterns = [
    path('', CredentialListCreateView.as_view(), name='credential-list'),
    path('<int:pk>/', CredentialDetailView.as_view(), name='credential-detail'),
]
