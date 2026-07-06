"""The person-detail fields (phone, how_we_met, last_discussed, last_contacted_at)
round-trip through the contact retrieve/update endpoint."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from networking.models import Contact

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    user = get_user_model().objects.create_user(username='o', email='o@x.com', password='pw')
    c = APIClient()
    c.force_authenticate(user=user)
    return c, user


def test_detail_fields_persist_and_return(client):
    c, user = client
    contact = Contact.objects.create(user=user, name='Jane Doe')
    resp = c.patch(f'/api/v1/networking/contacts/{contact.id}/', {
        'phone': '+1 555 0100',
        'how_we_met': 'Met at PyCon 2024, introduced by a mutual friend.',
        'last_discussed': 'Her team is hiring backend engineers in Q3.',
        'last_contacted_at': '2026-06-01',
    }, format='json')
    assert resp.status_code == 200, resp.content

    got = c.get(f'/api/v1/networking/contacts/{contact.id}/').data
    assert got['phone'] == '+1 555 0100'
    assert 'PyCon' in got['how_we_met']
    assert 'backend engineers' in got['last_discussed']
    assert got['last_contacted_at'] == '2026-06-01'


def test_last_contacted_at_can_be_cleared(client):
    c, user = client
    contact = Contact.objects.create(user=user, name='Jane Doe', last_contacted_at='2026-01-01')
    resp = c.patch(f'/api/v1/networking/contacts/{contact.id}/', {'last_contacted_at': None}, format='json')
    assert resp.status_code == 200, resp.content
    assert c.get(f'/api/v1/networking/contacts/{contact.id}/').data['last_contacted_at'] is None
