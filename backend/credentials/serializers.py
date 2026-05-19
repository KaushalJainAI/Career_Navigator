from rest_framework import serializers

from .models import Credential


class CredentialSerializer(serializers.ModelSerializer):
    secret = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = Credential
        fields = ['id', 'provider', 'label', 'secret', 'meta', 'created_at', 'updated_at', 'last_used_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_used_at']

    def create(self, validated_data):
        secret = validated_data.pop('secret')
        cred = Credential(**validated_data)
        cred.set_secret(secret)
        cred.save()
        return cred

    def update(self, instance, validated_data):
        secret = validated_data.pop('secret', None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        if secret is not None:
            instance.set_secret(secret)
        instance.save()
        return instance
