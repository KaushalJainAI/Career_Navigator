import pytest

from notifications.models import Subscription

pytestmark = pytest.mark.django_db


def test_subscription_create_update_delete(auth_client, user):
    response = auth_client.post('/api/v1/notifications/subscriptions/', {
        'name': 'Backend remote',
        'filter_json': {'keywords': ['python'], 'remote': True},
        'channels': ['in_app'],
    }, format='json')
    assert response.status_code == 201
    sub_id = response.data['id']

    response = auth_client.patch(f'/api/v1/notifications/subscriptions/{sub_id}/', {
        'enabled': False,
    }, format='json')
    assert response.status_code == 200
    assert response.data['enabled'] is False

    response = auth_client.delete(f'/api/v1/notifications/subscriptions/{sub_id}/')
    assert response.status_code == 204
    assert not Subscription.objects.filter(id=sub_id).exists()


def test_subscription_detail_is_user_scoped(auth_client, django_user_model):
    other = django_user_model.objects.create_user(username='other', email='other@example.com', password='pw')
    sub = Subscription.objects.create(user=other, name='Other')

    response = auth_client.patch(f'/api/v1/notifications/subscriptions/{sub.id}/', {
        'enabled': False,
    }, format='json')

    assert response.status_code == 404
