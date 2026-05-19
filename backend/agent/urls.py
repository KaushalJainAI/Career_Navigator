from django.urls import path

from .views import AgentChatView, AgentSessionListCreateView

urlpatterns = [
    path('sessions/', AgentSessionListCreateView.as_view(), name='agent-sessions'),
    path('sessions/<int:session_id>/chat/', AgentChatView.as_view(), name='agent-chat'),
]
