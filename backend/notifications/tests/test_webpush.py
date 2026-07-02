import pytest

from jobs.models import Company, JobPosting, Source
from notifications import webpush as webpush_module
from notifications.models import Alert, Channel, Subscription, WebPushDevice
from notifications.services import deliver_job_alert

pytestmark = pytest.mark.django_db


@pytest.fixture
def vapid(settings):
    # Fake but non-empty keys so push_enabled() is True; delivery is mocked.
    settings.VAPID_PUBLIC_KEY = 'test-public-key'
    settings.VAPID_PRIVATE_KEY = 'test-private-key'
    settings.VAPID_CLAIM_EMAIL = 'mailto:test@career-navigator.local'
    return settings


@pytest.fixture
def a_job():
    src = Source.objects.create(name='s', kind='aggregator')
    company = Company.objects.create(name='Acme')
    return JobPosting.objects.create(
        source=src, external_id='x1', company=company, title='Backend Engineer',
        description='Python Django', location='Remote', remote=True,
    )


class FakeWebPushException(Exception):
    def __init__(self, status_code):
        self.response = type('R', (), {'status_code': status_code})()


def test_vapid_public_key_endpoint(auth_client, vapid):
    response = auth_client.get('/api/v1/notifications/vapid-public-key/')
    assert response.status_code == 200
    assert response.data['public_key'] == 'test-public-key'
    assert response.data['enabled'] is True


def test_register_upserts_and_unregisters(auth_client, user):
    sub = {'endpoint': 'https://push.example/abc', 'keys': {'p256dh': 'p', 'auth': 'a'}}

    r1 = auth_client.post('/api/v1/notifications/push/register/', sub, format='json')
    assert r1.status_code == 201

    # Re-registering the same endpoint updates in place, never duplicates.
    sub2 = {'endpoint': 'https://push.example/abc', 'p256dh': 'p2', 'auth': 'a2'}
    r2 = auth_client.post('/api/v1/notifications/push/register/', sub2, format='json')
    assert r2.status_code == 200
    assert WebPushDevice.objects.filter(user=user).count() == 1
    assert WebPushDevice.objects.get(user=user).p256dh == 'p2'

    r3 = auth_client.post('/api/v1/notifications/push/unregister/',
                          {'endpoint': 'https://push.example/abc'}, format='json')
    assert r3.status_code == 200
    assert WebPushDevice.objects.filter(user=user).count() == 0


def test_register_rejects_incomplete_subscription(auth_client):
    r = auth_client.post('/api/v1/notifications/push/register/',
                         {'endpoint': 'https://push.example/x'}, format='json')
    assert r.status_code == 400


def test_send_web_push_calls_pywebpush(vapid, user, monkeypatch):
    device = WebPushDevice.objects.create(user=user, endpoint='https://push/x', auth='a', p256dh='p')
    calls = {}

    def fake_webpush(**kwargs):
        calls.update(kwargs)

    monkeypatch.setattr('pywebpush.webpush', fake_webpush)
    monkeypatch.setattr('pywebpush.WebPushException', FakeWebPushException)

    assert webpush_module.send_web_push(device, {'title': 'hi'}) is True
    assert calls['subscription_info']['endpoint'] == 'https://push/x'
    assert calls['subscription_info']['keys'] == {'auth': 'a', 'p256dh': 'p'}
    assert calls['vapid_private_key'] == 'test-private-key'


def test_send_web_push_prunes_expired_subscription(vapid, user, monkeypatch):
    device = WebPushDevice.objects.create(user=user, endpoint='https://push/gone', auth='a', p256dh='p')

    def fake_webpush(**kwargs):
        raise FakeWebPushException(410)

    monkeypatch.setattr('pywebpush.webpush', fake_webpush)
    monkeypatch.setattr('pywebpush.WebPushException', FakeWebPushException)

    assert webpush_module.send_web_push(device, {'title': 'hi'}) is False
    assert not WebPushDevice.objects.filter(pk=device.pk).exists()  # pruned on 410


def test_send_web_push_noop_without_keys(user, monkeypatch):
    # No VAPID keys configured -> must not attempt delivery.
    device = WebPushDevice.objects.create(user=user, endpoint='https://push/x', auth='a', p256dh='p')
    monkeypatch.setattr(webpush_module.settings, 'VAPID_PRIVATE_KEY', '')
    monkeypatch.setattr(webpush_module.settings, 'VAPID_PUBLIC_KEY', '')
    assert webpush_module.send_web_push(device, {'title': 'hi'}) is False


def test_deliver_job_alert_pushes_to_webpush_devices(vapid, user, a_job, monkeypatch):
    Subscription.objects.create(user=user, name='All', filter_json={}, channels=[Channel.WEBPUSH], enabled=True)
    WebPushDevice.objects.create(user=user, endpoint='https://push/d1', auth='a', p256dh='p')
    sent = []
    monkeypatch.setattr('notifications.services.send_web_push', lambda device, payload: sent.append((device.endpoint, payload)) or True)

    delivered = deliver_job_alert(a_job)

    assert len(delivered) == 1
    assert delivered[0].channel == Channel.WEBPUSH
    assert sent and sent[0][0] == 'https://push/d1'
    assert 'Backend Engineer' in sent[0][1]['title']


def test_activity_feed_merges_alerts_and_events(auth_client, user, a_job):
    from applications.models import Application, ApplicationEvent
    from notifications.models import Alert, Channel, Subscription
    sub = Subscription.objects.create(user=user, name='s', channels=[Channel.IN_APP])
    Alert.objects.create(user=user, job=a_job, subscription=sub, channel=Channel.IN_APP, read=False)
    app = Application.objects.create(user=user, job=a_job)
    ApplicationEvent.objects.create(application=app, type='status_changed', payload={'status': 'phone'})
    ApplicationEvent.objects.create(application=app, type='tailored_resume_generated', payload={})

    resp = auth_client.get('/api/v1/notifications/activity/')
    assert resp.status_code == 200
    kinds = {i['kind'] for i in resp.data['items']}
    assert 'alert' in kinds and 'status' in kinds and 'material' in kinds
    assert resp.data['unread'] == 1
    titles = [i['title'] for i in resp.data['items']]
    assert any('Moved to' in t for t in titles)
    assert any('Tailored resume' in t for t in titles)
