from django.urls import path

from .views import ApplicationDetailView, ApplicationListCreateView, ApproveAutoApplyView

urlpatterns = [
    path('', ApplicationListCreateView.as_view(), name='application-list'),
    path('<int:pk>/', ApplicationDetailView.as_view(), name='application-detail'),
    path('<int:pk>/approve/', ApproveAutoApplyView.as_view(), name='application-approve'),
]
