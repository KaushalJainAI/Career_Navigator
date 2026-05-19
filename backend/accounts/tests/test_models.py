import pytest
from django.contrib.auth import get_user_model

from accounts.models import Tier, UserProfile

pytestmark = pytest.mark.django_db


def test_userprofile_autocreated_on_user_create():
    User = get_user_model()
    user = User.objects.create_user(username='bob', email='bob@example.com', password='pw12345678')
    assert UserProfile.objects.filter(user=user).exists()
    profile = user.cn_profile
    assert profile.tier == Tier.FREE
    assert profile.is_paid is False


def test_userprofile_is_paid_flag():
    User = get_user_model()
    user = User.objects.create_user(username='carol', email='carol@example.com', password='pw12345678')
    user.cn_profile.tier = Tier.PRO
    user.cn_profile.save()
    assert user.cn_profile.is_paid is True


def test_stealth_domains_default_empty():
    User = get_user_model()
    user = User.objects.create_user(username='dave', email='dave@example.com', password='pw12345678')
    assert user.cn_profile.stealth_domains == []
