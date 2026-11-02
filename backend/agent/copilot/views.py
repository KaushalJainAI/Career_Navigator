from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ai.providers import configured_model_label, get_configured_llm

from ..models import AgentMessage, AgentSession
from .loop import describe, execute, llm_turn, rule_turn
from .tools import CONFIRM, TOOLS, schema


def _history(session) -> list[dict]:
    return [{'role': m.role, 'content': m.content} for m in session.messages.filter(role__in=['user', 'assistant'])
            .order_by('-created_at')[:12]][::-1]


def _mode() -> str:
    return configured_model_label() or 'rules'


def _session_payload(session) -> dict:
    return {
        'mode': _mode(),
        'id': session.id, 'status': session.status, 'pending_action': session.pending_approval,
        'messages': [{'id': m.id, 'role': m.role, 'content': m.content, 'meta': m.tool_calls, 'created_at': m.created_at}
                     for m in session.messages.filter(role__in=['user', 'assistant'])],
    }


def _record(session, out: dict) -> dict:
    steps = [{'tool': s['tool'], 'args': s.get('args', {}), 'ok': s.get('ok'), 'error': s.get('error')}
             for s in out.get('steps', [])]
    meta = {'steps': steps, 'ui': out.get('ui', []), 'pending_action': out.get('pending_action')}
    msg = AgentMessage.objects.create(session=session, role='assistant', content=out.get('reply', ''), tool_calls=[meta])
    for s in out.get('steps', []):
        AgentMessage.objects.create(session=session, role='tool', tool_name=s['tool'],
                                    content=str(s.get('result') if s.get('ok') else s.get('error'))[:4000])
    session.pending_approval = out.get('pending_action')
    session.status = 'paused_hitl' if out.get('pending_action') else 'active'
    session.save(update_fields=['pending_approval', 'status', 'updated_at'])
    return {'session_id': session.id, 'message_id': msg.id, 'reply': msg.content, 'steps': steps,
            'ui': out.get('ui', []), 'pending_action': out.get('pending_action'),
            'mode': out.get('mode', 'rules')}


class CopilotChatView(APIView):
    """POST {message, session_id?} → one copilot turn."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        message = (request.data.get('message') or '').strip()
        if not message:
            return Response({'detail': 'message is required'}, status=400)
        sid = request.data.get('session_id')
        session = AgentSession.objects.filter(pk=sid, user=request.user, kind='copilot').first() if sid else None
        if session is None:
            session = AgentSession.objects.create(user=request.user, kind='copilot')
        history = _history(session)
        AgentMessage.objects.create(session=session, role='user', content=message)
        out: dict = {}
        llm = get_configured_llm()
        if llm is not None:
            try:
                out = llm_turn(request.user, message, history, llm)
                if out:
                    out['mode'] = configured_model_label()
            except Exception:  # noqa: BLE001 - provider hiccup: fall back to rules
                out = {}
        if not out:
            out = rule_turn(request.user, message)
            out['mode'] = 'rules'
        return Response(_record(session, out))


class CopilotSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id: int):
        session = get_object_or_404(AgentSession, pk=session_id, user=request.user, kind='copilot')
        return Response(_session_payload(session))


class CopilotLatestView(APIView):
    """The user's most recent copilot conversation (or an empty one)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        session = AgentSession.objects.filter(user=request.user, kind='copilot').order_by('-updated_at').first()
        if session is None:
            return Response({'id': None, 'status': 'active', 'pending_action': None, 'messages': [], 'mode': _mode()})
        return Response(_session_payload(session))


class CopilotApproveView(APIView):
    """POST {action_id, approve: bool} — run (or cancel) the paused confirm-level action."""

    permission_classes = [IsAuthenticated]

    def post(self, request, session_id: int):
        session = get_object_or_404(AgentSession, pk=session_id, user=request.user, kind='copilot')
        pending = session.pending_approval
        if not pending or pending.get('id') != request.data.get('action_id'):
            return Response({'detail': 'Nothing is waiting for approval (or it was already handled).'}, status=409)
        if not request.data.get('approve'):
            return Response(_record(session, {'reply': 'Okay, I did not change anything.', 'steps': []}))
        step = {'tool': pending['tool'], 'args': pending['args'],
                **execute(request.user, pending['tool'], pending['args'])}
        res = step.get('result') or {}
        return Response(_record(session, {'reply': describe(step), 'steps': [step],
                                          'ui': res.get('ui', []) if isinstance(res, dict) else []}))


class CopilotToolsView(APIView):
    """Tool catalogue — used by the Claude Code plugin / MCP server."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'tools': schema()})


class CopilotToolCallView(APIView):
    """POST {args, confirmed} — call one tool directly (MCP clients).

    confirm-level tools need `confirmed: true`; MCP hosts such as Claude Code
    show the user a permission prompt before sending it."""

    permission_classes = [IsAuthenticated]

    def post(self, request, name: str):
        tool = TOOLS.get(name)
        if tool is None:
            return Response({'detail': 'unknown tool'}, status=404)
        args = request.data.get('args') or {}
        if tool.risk == CONFIRM and not request.data.get('confirmed'):
            return Response({'detail': 'confirmation required', 'summary': tool.summary(args)}, status=409)
        out = execute(request.user, name, args)
        if not out['ok']:
            return Response({'detail': out['error']}, status=400)
        return Response({'result': out['result'], 'text': describe({'tool': name, 'args': args, **out})})
