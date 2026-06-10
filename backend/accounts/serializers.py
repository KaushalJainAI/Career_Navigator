from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError, transaction
from rest_framework import serializers

from .models import APIToken, UserProfile

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


class AccountUpdateSerializer(serializers.ModelSerializer):
    """PATCH /auth/me/ — update the user's display name and stealth domains.
    Email/username are intentionally immutable here (the username is keyed to the
    sign-up email and changing it would break OAuth account linking)."""

    stealth_domains = serializers.ListField(
        child=serializers.CharField(allow_blank=False),
        required=False,
        source='cn_profile.stealth_domains',
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'stealth_domains']

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('cn_profile', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if profile_data is not None and 'stealth_domains' in profile_data:
            profile = instance.cn_profile
            profile.stealth_domains = profile_data['stealth_domains']
            profile.save(update_fields=['stealth_domains', 'updated_at'])
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_new_password(self, value):
        validate_password(value)
        return value


class GoogleLoginSerializer(serializers.Serializer):
    """Body of POST /auth/google/ — code from the OAuth callback."""
    code = serializers.CharField(required=True)
    redirect_uri = serializers.CharField(required=False, allow_blank=True)


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)

    def validate_email(self, value):
        email = value.strip().lower()
        # Username is set to the email, so guard against both columns.
        if User.objects.filter(username__iexact=email).exists() or \
                User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return email

    def validate_password(self, value):
        # Run Django's configured password validators (length, common, numeric, etc.).
        validate_password(value)
        return value

    def create(self, validated_data):
        email = validated_data['email']
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=validated_data['password'],
                    first_name=validated_data.get('first_name', ''),
                    last_name=validated_data.get('last_name', ''),
                )
        except IntegrityError:
            # Lost a race with a concurrent signup for the same email.
            raise serializers.ValidationError(
                {'email': 'An account with this email already exists.'}
            )
        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)


class APITokenSerializer(serializers.ModelSerializer):
    """Read-only view of an APIToken. The cleartext token is NEVER echoed here —
    it is only included in the response of `APITokenListCreateView.post` once."""

    class Meta:
        model = APIToken
        fields = ['id', 'name', 'last_used_at', 'created_at', 'revoked_at']
        read_only_fields = fields
