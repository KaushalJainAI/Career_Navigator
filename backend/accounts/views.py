import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import GuestSession
from .oauth import GoogleOAuthError, GoogleOAuthProvider
from .serializers import GoogleLoginSerializer, RegisterSerializer, UserSerializer


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
