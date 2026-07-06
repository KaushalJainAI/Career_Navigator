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
    # Optional: name the company to research (no Company row needed). Seeds
    # research['company'], which perform_create reads to tailor the question bank.
    company_name = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = InterviewSession
        fields = '__all__'
        read_only_fields = ['user', 'started_at', 'ended_at', 'status']

    def create(self, validated_data):
        name = (validated_data.pop('company_name', '') or '').strip()
        if name:
            research = dict(validated_data.get('research') or {})
            research['company'] = name
            validated_data['research'] = research
        return super().create(validated_data)
