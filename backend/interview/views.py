from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .grilling import (
    evaluate_answer,
    generate_question_bank,
    research,
    summarise_session,
)
from .models import (
    InterviewQuestion,
    InterviewReport,
    InterviewSession,
    InterviewTurn,
)
from .serializers import (
    InterviewReportSerializer,
    InterviewSessionSerializer,
    InterviewTurnSerializer,
)


class SessionListCreateView(generics.ListCreateAPIView):
    serializer_class = InterviewSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return InterviewSession.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        session = serializer.save(user=self.request.user)
        company_name = session.company.name if session.company else session.research.get('company', '')
        session.research = research(company_name or session.research.get('company', ''),
                                    session.role, session.stage)
        bank = generate_question_bank(session.role, session.stage,
                                      difficulty=session.difficulty,
                                      research_notes=session.research)
        for idx, q in enumerate(bank):
            InterviewQuestion.objects.create(session=session, order=idx, **q)
        session.status = 'ready'
        session.save(update_fields=['research', 'status'])


class SessionDetailView(generics.RetrieveAPIView):
    serializer_class = InterviewSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return InterviewSession.objects.filter(user=self.request.user)


class AnswerView(APIView):
    """Submit an answer to the next pending question; receive evaluation back."""

    permission_classes = [IsAuthenticated]

    def post(self, request, session_id: int):
        session = InterviewSession.objects.get(pk=session_id, user=request.user)
        question = (
            InterviewQuestion.objects.filter(session=session)
            .exclude(turns__isnull=False)
            .order_by('order')
            .first()
        )
        if question is None:
            return Response({'detail': 'No more questions; ask for the report.'},
                            status=status.HTTP_400_BAD_REQUEST)
        answer = request.data.get('answer', '')
        evaluation = evaluate_answer(
            {'prompt': question.prompt, 'expected_signals': question.expected_signals}, answer
        )
        turn = InterviewTurn.objects.create(
            question=question, user_answer=answer, evaluation=evaluation,
            score=evaluation.get('score'), feedback=evaluation.get('feedback', ''),
        )
        if session.status != 'in_progress':
            session.status = 'in_progress'
            session.save(update_fields=['status'])
        return Response(InterviewTurnSerializer(turn).data)


class ReportView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id: int):
        session = InterviewSession.objects.get(pk=session_id, user=request.user)
        turns = InterviewTurn.objects.filter(question__session=session)
        data = summarise_session([t.evaluation for t in turns])
        report, _ = InterviewReport.objects.update_or_create(
            session=session,
            defaults={
                'strengths': data['strengths'], 'gaps': data['gaps'],
                'study_plan': data['study_plan'], 'overall_score': data['overall_score'],
            },
        )
        session.status = 'done'
        session.ended_at = timezone.now()
        session.save(update_fields=['status', 'ended_at'])
        return Response(InterviewReportSerializer(report).data)
