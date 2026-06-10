from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    APITokenListCreateView,
    APITokenRevokeView,
    ChangePasswordView,
    GoogleLoginView,
    GuestKeyView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('login/', TokenObtainPairView.as_view(), name='auth-login'),
    path('refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('me/', MeView.as_view(), name='auth-me'),
    path('change-password/', ChangePasswordView.as_view(), name='auth-change-password'),
    path('google/', GoogleLoginView.as_view(), name='auth-google'),
    path('guest-key/', GuestKeyView.as_view(), name='auth-guest-key'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='auth-password-reset'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='auth-password-reset-confirm'),
    path('api-tokens/', APITokenListCreateView.as_view(), name='auth-api-tokens'),
    path('api-tokens/<int:pk>/revoke/', APITokenRevokeView.as_view(), name='auth-api-token-revoke'),
]
