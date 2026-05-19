from django.urls import path

from .views import AnswerView, ReportView, SessionDetailView, SessionListCreateView

urlpatterns = [
    path('sessions/', SessionListCreateView.as_view(), name='interview-sessions'),
    path('sessions/<int:pk>/', SessionDetailView.as_view(), name='interview-session-detail'),
    path('sessions/<int:session_id>/answer/', AnswerView.as_view(), name='interview-answer'),
    path('sessions/<int:session_id>/report/', ReportView.as_view(), name='interview-report'),
]
