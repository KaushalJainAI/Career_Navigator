from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import UserProfile

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['tier', 'credits_remaining', 'stealth_domains', 'nvidia_guest_key_issued']
        read_only_fields = ['tier', 'credits_remaining', 'nvidia_guest_key_issued']


class UserSerializer(serializers.ModelSerializer):
    cn_profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'cn_profile']
        read_only_fields = ['id']


class GoogleLoginSerializer(serializers.Serializer):
    """Body of POST /auth/google/ — code from the OAuth callback."""
    code = serializers.CharField(required=True)
    redirect_uri = serializers.CharField(required=False, allow_blank=True)


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)

    def create(self, validated_data):
        email = validated_data['email']
        user = User.objects.create_user(
            username=email,
            email=email,
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
        )
        return user
