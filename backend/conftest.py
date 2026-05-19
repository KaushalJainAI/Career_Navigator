import os

os.environ.setdefault('CREDENTIAL_ENCRYPTION_KEY', 'test-key-base64-32bytes-padding=')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.test')

import django  # noqa: E402

django.setup()

import pytest  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402


@pytest.fixture
def user(db):
    User = get_user_model()
    return User.objects.create_user(
        username='alice', email='alice@example.com', password='pw-test-1234'
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client
