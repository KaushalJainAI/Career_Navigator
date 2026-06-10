import pytest
from django.urls import reverse

from profiles.models import StructuredProfile

pytestmark = pytest.mark.django_db


def test_profile_get_creates_on_first_access(auth_client, user):
    assert not StructuredProfile.objects.filter(user=user).exists()
    resp = auth_client.get(reverse('profile-detail'))
    assert resp.status_code == 200
    assert StructuredProfile.objects.filter(user=user).exists()


def test_profile_requires_auth(api_client):
    assert api_client.get(reverse('profile-detail')).status_code == 401


def test_profile_patch_scalar_fields(auth_client):
    resp = auth_client.patch(
        reverse('profile-detail'),
        {'full_name': 'Ada Lovelace', 'headline': 'Engineer', 'onboarding_complete': True},
        format='json',
    )
    assert resp.status_code == 200
    assert resp.data['full_name'] == 'Ada Lovelace'
    assert resp.data['onboarding_complete'] is True


def test_profile_patch_replaces_nested_collections(auth_client, user):
    payload = {
        'experiences': [
            {'company': 'Acme', 'title': 'Engineer', 'is_current': True, 'bullets': ['Built X']},
        ],
        'skills': [
            {'name': 'Python', 'proficiency': 'expert'},
            {'name': 'Django'},
        ],
        'preference': {'target_titles': ['Senior Engineer'], 'remote': True, 'salary_min': 120000},
    }
    resp = auth_client.patch(reverse('profile-detail'), payload, format='json')
    assert resp.status_code == 200
    assert len(resp.data['experiences']) == 1
    assert {s['name'] for s in resp.data['skills']} == {'Python', 'Django'}
    assert resp.data['preference']['target_titles'] == ['Senior Engineer']
    assert resp.data['preference']['salary_min'] == 120000

    # A second PATCH with a shorter list fully replaces the previous rows.
    resp = auth_client.patch(
        reverse('profile-detail'),
        {'skills': [{'name': 'Rust'}]},
        format='json',
    )
    assert resp.status_code == 200
    assert {s['name'] for s in resp.data['skills']} == {'Rust'}
    # Experiences were omitted, so they are left untouched.
    assert len(resp.data['experiences']) == 1


def test_profile_patch_empty_list_clears_collection(auth_client):
    auth_client.patch(
        reverse('profile-detail'),
        {'skills': [{'name': 'Python'}]},
        format='json',
    )
    resp = auth_client.patch(reverse('profile-detail'), {'skills': []}, format='json')
    assert resp.status_code == 200
    assert resp.data['skills'] == []


def test_profile_readiness_reports_missing_and_ready(auth_client):
    resp = auth_client.get(reverse('profile-detail'))
    assert resp.status_code == 200
    assert resp.data['readiness']['ready'] is False
    assert 'skills' in resp.data['readiness']['missing']

    resp = auth_client.patch(
        reverse('profile-detail'),
        {
            'full_name': 'Ada Lovelace',
            'headline': 'Engineer',
            'location': 'London',
            'skills': [{'name': 'Python'}],
            'experiences': [{'company': 'Acme', 'title': 'Engineer'}],
        },
        format='json',
    )
    assert resp.status_code == 200
    assert resp.data['readiness']['ready'] is True
