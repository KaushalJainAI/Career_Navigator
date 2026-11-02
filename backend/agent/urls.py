from django.urls import path

from .copilot.views import (
    CopilotApproveView,
    CopilotChatView,
    CopilotLatestView,
    CopilotSessionView,
    CopilotToolCallView,
    CopilotToolsView,
)
from .views import AgentChatView, AgentSessionListCreateView

urlpatterns = [
    path('sessions/', AgentSessionListCreateView.as_view(), name='agent-sessions'),
    path('sessions/<int:session_id>/chat/', AgentChatView.as_view(), name='agent-chat'),
    path('copilot/', CopilotChatView.as_view(), name='copilot-chat'),
    path('copilot/latest/', CopilotLatestView.as_view(), name='copilot-latest'),
    path('copilot/tools/', CopilotToolsView.as_view(), name='copilot-tools'),
    path('copilot/tools/<str:name>/', CopilotToolCallView.as_view(), name='copilot-tool-call'),
    path('copilot/<int:session_id>/', CopilotSessionView.as_view(), name='copilot-session'),
    path('copilot/<int:session_id>/approve/', CopilotApproveView.as_view(), name='copilot-approve'),
]
