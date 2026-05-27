"""Integration tests for the new networking endpoints (employments, relationships,
company-relationships, graph, warm-intros)."""

import datetime as dt

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from jobs.models import Company
from networking.models import (
    Contact,
    ContactEmployment,
    ContactRelationship,
    ContactRelationshipKind,
    CompanyRelationship,
    CompanyRelationshipKind,
)


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(
        username='owner', email='owner@x.com', password='pw',
    )


@pytest.fixture
def other_user(db):
    return get_user_model().objects.create_user(
        username='other', email='other@x.com', password='pw',
    )


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def acme(db):
    return Company.objects.create(name='Acme', domain='acme.com')


@pytest.mark.django_db
def test_post_and_list_employments(client, user, acme):
    contact = Contact.objects.create(user=user, name='Alice')

    resp = client.post(
        f'/api/v1/networking/contacts/{contact.id}/employments/',
        {'company': acme.id, 'title': 'EM', 'started_at': '2023-01-01', 'is_current': True},
        format='json',
    )
    assert resp.status_code == 201, resp.data
    assert ContactEmployment.objects.filter(contact=contact, company=acme).exists()

    resp = client.get(f'/api/v1/networking/contacts/{contact.id}/employments/')
    assert resp.status_code == 200
    data = resp.data if isinstance(resp.data, list) else resp.data.get('results', resp.data)
    assert any(row['title'] == 'EM' for row in data)


@pytest.mark.django_db
def test_user_cannot_create_employment_on_other_users_contact(client, other_user, acme):
    foreign_contact = Contact.objects.create(user=other_user, name='Stranger')
    resp = client.post(
        f'/api/v1/networking/contacts/{foreign_contact.id}/employments/',
        {'company': acme.id, 'title': 'X'},
        format='json',
    )
    assert resp.status_code == 404


@pytest.mark.django_db
def test_post_relationship_user_scoped(client, user, other_user):
    a = Contact.objects.create(user=user, name='A')
    b = Contact.objects.create(user=user, name='B')
    foreign = Contact.objects.create(user=other_user, name='F')

    resp = client.post(
        f'/api/v1/networking/contacts/{a.id}/relationships/',
        {'to_contact': b.id, 'kind': 'mutual', 'strength': 4},
        format='json',
    )
    assert resp.status_code == 201, resp.data
    assert ContactRelationship.objects.filter(from_contact=a, to_contact=b).exists()

    # Cannot reference a contact owned by another user.
    resp = client.post(
        f'/api/v1/networking/contacts/{a.id}/relationships/',
        {'to_contact': foreign.id, 'kind': 'mutual'},
        format='json',
    )
    assert resp.status_code in (400, 403)


@pytest.mark.django_db
def test_duplicate_relationship_rejected(client, user):
    a = Contact.objects.create(user=user, name='A')
    b = Contact.objects.create(user=user, name='B')
    ContactRelationship.objects.create(
        user=user, from_contact=a, to_contact=b,
        kind=ContactRelationshipKind.MUTUAL,
    )
    resp = client.post(
        f'/api/v1/networking/contacts/{a.id}/relationships/',
        {'to_contact': b.id, 'kind': 'mutual'},
        format='json',
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_company_relationship_create_and_list(client, acme):
    other = Company.objects.create(name='BigCo', domain='bigco.com')

    resp = client.post(
        f'/api/v1/networking/companies/{acme.id}/relationships/',
        {'to_company': other.id, 'kind': 'acquired'},
        format='json',
    )
    assert resp.status_code == 201, resp.data
    assert CompanyRelationship.objects.filter(
        from_company=acme, to_company=other,
        kind=CompanyRelationshipKind.ACQUIRED,
    ).exists()

    resp = client.get(f'/api/v1/networking/companies/{acme.id}/relationships/')
    assert resp.status_code == 200


@pytest.mark.django_db
def test_graph_endpoint_returns_nodes_and_edges(client, user, acme):
    c = Contact.objects.create(user=user, name='Alice', company=acme)
    ContactEmployment.objects.create(contact=c, company=acme, is_current=True)

    resp = client.get(f'/api/v1/networking/graph/?root=user:{user.id}&depth=1')
    assert resp.status_code == 200
    assert 'nodes' in resp.data and 'edges' in resp.data
    assert any(n['id'] == f'contact:{c.id}' for n in resp.data['nodes'])


@pytest.mark.django_db
def test_graph_user_root_must_be_self(client, user, other_user):
    resp = client.get(f'/api/v1/networking/graph/?root=user:{other_user.id}')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_warm_intros_endpoint(client, user, acme):
    c = Contact.objects.create(user=user, name='Alice', company=acme)
    ContactEmployment.objects.create(
        contact=c, company=acme, is_current=True,
        started_at=dt.date(2023, 1, 1),
    )

    resp = client.get(f'/api/v1/networking/warm-intros/{acme.id}/')
    assert resp.status_code == 200
    assert resp.data['company']['id'] == acme.id
    assert len(resp.data['results']) == 1
    assert resp.data['results'][0]['contact_id'] == c.id
