from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .graph import AgentState, run
from .models import AgentMessage, AgentSession
from .onboarding import apply_onboarding_facts, onboarding_reply
from .serializers import AgentSessionSerializer


class AgentSessionListCreateView(generics.ListCreateAPIView):
    serializer_class = AgentSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AgentSession.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AgentChatView(APIView):
    """Single-turn chat. The real implementation streams via SSE/WebSocket;
    this endpoint is the minimum that lets the frontend integrate end-to-end."""

    permission_classes = [IsAuthenticated]

    def post(self, request, session_id: int):
        session = AgentSession.objects.get(pk=session_id, user=request.user)
        message = request.data.get('message', '')
        AgentMessage.objects.create(session=session, role='user', content=message)
        if session.kind == 'onboarding':
            result = apply_onboarding_facts(request.user, message)
            reply = onboarding_reply(result)
            AgentMessage.objects.create(session=session, role='assistant', content=reply)
            session.state = {**(session.state or {}), 'last_onboarding_result': result}
            session.save(update_fields=['state', 'updated_at'])
            return Response({
                'reply': reply,
                'observations': [{'name': 'onboarding_profile_update', 'result': result}],
                'paused_for_approval': None,
                'halt': True,
            })
        state = AgentState(user_id=request.user.id, objective=message,
                           phase_cap=request.data.get('phase_cap', 1))
        result = run(state)
        AgentMessage.objects.create(session=session, role='assistant',
                                    content=str(result.messages[-1] if result.messages else ''))
        if result.paused_for_approval:
            session.status = 'paused_hitl'
            session.pending_approval = result.paused_for_approval
            session.save(update_fields=['status', 'pending_approval', 'updated_at'])
        return Response({
            'observations': result.observations,
            'paused_for_approval': result.paused_for_approval,
            'halt': result.halt,
        })
