from rest_framework import serializers

from .models import Application, ApplicationEvent, AutoApplySession


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

    class Meta:
        model = Application
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'updated_at']
