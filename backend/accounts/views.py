import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import APIToken, GuestSession
from .oauth import GoogleOAuthError, GoogleOAuthProvider
from .serializers import (
    APITokenSerializer,
    GoogleLoginSerializer,
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


class GoogleLoginView(APIView):
    """Exchange a Google OAuth2 authorisation code for a JWT pair.
    Creates the local user on first sign-in (post_save signal handles UserProfile)."""

    permission_classes = [AllowAny]
    # Tests inject a provider factory to bypass the network. Production uses
    # the real `GoogleOAuthProvider`.
    provider_factory = GoogleOAuthProvider

    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data['code']
        redirect_uri = serializer.validated_data.get('redirect_uri') or settings.GOOGLE_OAUTH_REDIRECT_URI

        provider = self.provider_factory(redirect_uri=redirect_uri)
        try:
            token_data = provider.exchange_code(code)
        except GoogleOAuthError as exc:
            return Response({'detail': f'Token exchange failed: {exc}'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(token_data, dict) or 'error' in token_data:
            err = token_data.get('error_description') if isinstance(token_data, dict) else 'Unknown OAuth error'
            return Response({'detail': err or 'Unknown OAuth error'},
                            status=status.HTTP_400_BAD_REQUEST)
        access_token = token_data.get('access_token')
        if not access_token:
            return Response({'detail': 'No access_token in OAuth response.'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            user_info = provider.get_user_info(access_token)
        except Exception:  # noqa: BLE001
            return Response({'detail': 'Failed to fetch user info from Google.'},
                            status=status.HTTP_400_BAD_REQUEST)
        email = (user_info or {}).get('email')
        if not email:
            return Response({'detail': 'No email returned by Google.'},
                            status=status.HTTP_400_BAD_REQUEST)

        user = self._get_or_create_user(email, user_info)
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                'user': UserSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            },
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _get_or_create_user(email: str, user_info: dict):
        User = get_user_model()
        user = User.objects.filter(email=email).first()
        if user is not None:
            return user
        base = email.split('@')[0]
        username = base
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f'{base}{counter}'
            counter += 1
        return User.objects.create_user(
            username=username,
            email=email,
            first_name=user_info.get('given_name', ''),
            last_name=user_info.get('family_name', ''),
        )


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


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        User = get_user_model()
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173').rstrip('/')
            reset_url = f'{frontend_url}/reset-password?uid={uid}&token={token}'
            send_mail(
                'Reset your Career Navigator password',
                (
                    'You asked to reset your Career Navigator password.\n\n'
                    f'Open this link to choose a new password: {reset_url}\n\n'
                    'If you did not request this, you can ignore this email.'
                ),
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True,
            )
        return Response({'detail': 'If that email exists, a reset link has been sent.'})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            uid = force_str(urlsafe_base64_decode(serializer.validated_data['uid']))
            user = get_user_model().objects.get(pk=uid, is_active=True)
        except Exception:  # noqa: BLE001
            return Response({'detail': 'Invalid reset link.'}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, serializer.validated_data['token']):
            return Response({'detail': 'Invalid or expired reset link.'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(serializer.validated_data['password'])
        user.save(update_fields=['password'])
        return Response({'detail': 'Password updated. You can sign in now.'})
