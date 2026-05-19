from rest_framework import serializers

from .models import Alert, Subscription, WebPushDevice


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = '__all__'
        read_only_fields = ['user', 'created_at']


class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = '__all__'


class WebPushDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebPushDevice
        fields = '__all__'
        read_only_fields = ['user', 'created_at']
