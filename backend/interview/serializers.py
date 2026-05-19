from rest_framework import serializers

from .models import (
    InterviewQuestion,
    InterviewReport,
    InterviewSession,
    InterviewTurn,
)


class InterviewQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewQuestion
        fields = '__all__'


class InterviewTurnSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewTurn
        fields = '__all__'


class InterviewReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewReport
        fields = '__all__'


class InterviewSessionSerializer(serializers.ModelSerializer):
    questions = InterviewQuestionSerializer(many=True, read_only=True)
    report = InterviewReportSerializer(read_only=True)

    class Meta:
        model = InterviewSession
        fields = '__all__'
        read_only_fields = ['user', 'started_at', 'ended_at', 'status']
