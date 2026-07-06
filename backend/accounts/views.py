import random
import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import APIToken, GuestSession, PasswordResetOTP
from .oauth import GoogleOAuthError, verify_google_id_token
from .serializers import (
    AccountUpdateSerializer,
    APITokenSerializer,
    ChangePasswordSerializer,
    GoogleLoginSerializer,
    OTPVerifySerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserSerializer,
)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                'user': UserSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = AccountUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        request.user.refresh_from_db()
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not request.user.check_password(serializer.validated_data['current_password']):
            return Response(
                {'current_password': ['Current password is incorrect.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save(update_fields=['password'])
        return Response({'detail': 'Password updated.'})


class GoogleLoginView(APIView):
    """Verify a Google ID token (from Google Identity Services on the client) and
    return a JWT pair, creating the local user on first sign-in (a post_save
    signal handles UserProfile). Mirrors NGU's local id_token-verification flow."""

    permission_classes = [AllowAny]
    # Tests override this with a fake to bypass the network + google-auth.
    verify_token = staticmethod(verify_google_id_token)

    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            idinfo = self.verify_token(serializer.validated_data['token'])
        except GoogleOAuthError as exc:
            return Response({'detail': f'Invalid Google token: {exc}'},
                            status=status.HTTP_401_UNAUTHORIZED)

        email = (idinfo or {}).get('email')
        if not email:
            return Response({'detail': 'No email returned by Google.'},
                            status=status.HTTP_400_BAD_REQUEST)

        user, created = self._get_or_create_user(email.strip().lower(), idinfo)
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                'user': UserSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @staticmethod
    def _get_or_create_user(email: str, idinfo: dict):
        User = get_user_model()
        # Match case-insensitively so a Google sign-in never forks a second
        # account from an email that differs only in case.
        user = User.objects.filter(email__iexact=email).first()
        if user is not None:
            return user, False
        base = email.split('@')[0]
        username = base
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f'{base}{counter}'
            counter += 1
        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=idinfo.get('given_name', ''),
            last_name=idinfo.get('family_name', ''),
        )
        user.set_unusable_password()
        user.save(update_fields=['password'])
        return user, True


class GuestKeyView(APIView):
    """Issue an anonymous guest session that may use the shared NVIDIA NIM pool."""

    permission_classes = [AllowAny]

    def post(self, request):
        if not settings.NVIDIA_API_KEY:
            return Response(
                {'detail': 'Guest mode unavailable (no NVIDIA key configured).'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        session_key = secrets.token_urlsafe(32)
        GuestSession.objects.create(session_key=session_key)
        return Response(
            {
                'session_key': session_key,
                'model': settings.NVIDIA_GUEST_MODEL,
                'max_tokens': settings.GUEST_CHAT_MAX_TOKENS,
            },
            status=status.HTTP_201_CREATED,
        )


class APITokenListCreateView(APIView):
    """GET: list the user's non-revoked tokens (metadata only).
    POST {name}: issue a new token. The cleartext is returned ONCE in the response;
    it is never persisted or shown again."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        tokens = APIToken.objects.filter(user=request.user, revoked_at__isnull=True)
        return Response(APITokenSerializer(tokens, many=True).data)

    def post(self, request):
        name = (request.data.get('name') or '').strip() or 'Browser extension'
        token, cleartext = APIToken.issue(user=request.user, name=name)
        data = APITokenSerializer(token).data
        data['token'] = cleartext  # shown exactly once
        return Response(data, status=status.HTTP_201_CREATED)


class APITokenRevokeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int):
        try:
            token = APIToken.objects.get(pk=pk, user=request.user)
        except APIToken.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        token.revoke()
        return Response({'ok': True, 'id': token.id})


# --- Email-OTP password reset (ported from NGU): request → verify → confirm ---
OTP_TTL_MINUTES = 10


class PasswordResetRequestView(APIView):
    """Step 1 — email a 6-digit OTP. Always returns the same generic message so
    the endpoint can't be used to enumerate which emails have accounts."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        User = get_user_model()
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            otp_code = f'{random.randint(100000, 999999)}'
            # Invalidate any earlier pending OTPs so only the newest works.
            PasswordResetOTP.objects.filter(user=user, is_used=False).update(is_used=True)
            record = PasswordResetOTP(
                user=user, expires_at=timezone.now() + timedelta(minutes=OTP_TTL_MINUTES)
            )
            record.set_otp(otp_code)
            record.save()
            send_mail(
                'Your Career Navigator password reset code',
                (
                    f'Your password reset code is: {otp_code}\n\n'
                    f'It expires in {OTP_TTL_MINUTES} minutes. '
                    'If you did not request this, you can ignore this email.'
                ),
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True,
            )
        return Response({'detail': 'If that email exists, a reset code has been sent.'})


class PasswordResetVerifyView(APIView):
    """Step 2 — verify the OTP and issue a one-time reset_token."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        otp_code = serializer.validated_data['otp_code']

        User = get_user_model()
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        record = (
            PasswordResetOTP.objects.filter(user=user, is_used=False).first()
            if user else None
        )
        if record is None:
            return Response({'detail': 'Invalid or expired code.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if record.is_expired:
            return Response({'detail': 'This code has expired. Please request a new one.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if record.is_locked:
            return Response({'detail': 'Too many failed attempts. Please request a new code.'},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)
        if not record.check_otp(otp_code):
            record.failed_attempts += 1
            record.save(update_fields=['failed_attempts'])
            remaining = PasswordResetOTP.MAX_FAILED_ATTEMPTS - record.failed_attempts
            if remaining > 0:
                return Response({'detail': f'Invalid code. {remaining} attempt(s) remaining.'},
                                status=status.HTTP_400_BAD_REQUEST)
            return Response({'detail': 'Too many failed attempts. Please request a new code.'},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)

        record.is_used = True
        record.reset_token = uuid.uuid4().hex
        record.save(update_fields=['is_used', 'reset_token'])
        return Response({'detail': 'Code verified.', 'reset_token': record.reset_token})


class PasswordResetConfirmView(APIView):
    """Step 3 — exchange the verified reset_token for a new password."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        reset_token = serializer.validated_data['reset_token']

        User = get_user_model()
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        record = (
            PasswordResetOTP.objects.filter(
                user=user, reset_token=reset_token, is_used=True
            ).first()
            if user else None
        )
        if record is None or record.is_expired:
            return Response({'detail': 'Invalid or expired reset session. Please start over.'},
                            status=status.HTTP_400_BAD_REQUEST)

        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        # Burn the token so it can't be replayed.
        record.reset_token = None
        record.save(update_fields=['reset_token'])
        return Response({'detail': 'Password updated. You can sign in now.'})
