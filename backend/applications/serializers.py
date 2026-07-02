from rest_framework import serializers

from jobs.serializers import JobPostingSerializer

from .goals import goal_progress
from .models import Application, ApplicationEvent, AutoApplySession, Goal, Todo


class ApplicationEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationEvent
        fields = '__all__'


class AutoApplySessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutoApplySession
        fields = '__all__'
        read_only_fields = ['approval_token']


class ApplicationSerializer(serializers.ModelSerializer):
    events = ApplicationEventSerializer(many=True, read_only=True)
    auto_apply_session = AutoApplySessionSerializer(read_only=True)
    job_detail = JobPostingSerializer(source='job', read_only=True)

    class Meta:
        model = Application
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'updated_at']


class TodoSerializer(serializers.ModelSerializer):
    application_title = serializers.CharField(source='application.job.title', read_only=True, default=None)

    class Meta:
        model = Todo
        fields = ['id', 'title', 'done', 'due_on', 'application', 'application_title', 'created_at']
        read_only_fields = ['created_at']


class GoalSerializer(serializers.ModelSerializer):
    current = serializers.SerializerMethodField()
    metric_label = serializers.CharField(source='get_metric_display', read_only=True)
    period_label = serializers.CharField(source='get_period_display', read_only=True)

    class Meta:
        model = Goal
        fields = ['id', 'title', 'metric', 'metric_label', 'target', 'period', 'period_label',
                  'manual_progress', 'current', 'created_at']
        read_only_fields = ['created_at']

    def get_current(self, obj) -> int:
        return goal_progress(obj)
