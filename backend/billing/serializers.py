from rest_framework import serializers

from .models import CreditLedger, StripeSubscription


class CreditLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditLedger
        fields = '__all__'
        read_only_fields = ['user', 'created_at']


class StripeSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StripeSubscription
        fields = '__all__'
        read_only_fields = ['user']
