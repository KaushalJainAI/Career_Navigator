from datetime import timedelta

import pytest
from django.utils import timezone

from applications.analytics import build_response_analytics
from applications.models import Application, ApplicationEvent, ApplicationStatus, AutoApplyTier
from jobs.models import Company, JobPosting, Source

pytestmark = pytest.mark.django_db


def _job(ext):
    company, _ = Company.objects.get_or_create(name='Acme', domain='acme.com')
    source, _ = Source.objects.get_or_create(name='gh', kind='ats_public')
    return JobPosting.objects.create(source=source, external_id=ext, company=company, title='Eng')


def _app(user, ext, status, tier=AutoApplyTier.ASSIST, past_statuses=()):
    app = Application.objects.create(user=user, job=_job(ext), status=status, tier_used=tier)
    for s in past_statuses:
        ApplicationEvent.objects.create(application=app, type='status_changed', payload={'status': s})
    return app


def test_analytics_counts_funnel_responses_and_rates(user):
    # 4 submitted (one only saved → not submitted), 2 responses, 1 offer
    _app(user, 'a', ApplicationStatus.SAVED)  # never applied
    _app(user, 'b', ApplicationStatus.APPLIED)  # applied, no response
    _app(user, 'c', ApplicationStatus.PHONE)  # response
    _app(user, 'd', ApplicationStatus.OFFER)  # response + offer
    # rejected, but event history shows it reached a phone screen → still a response
    _app(user, 'e', ApplicationStatus.REJECTED, past_statuses=[ApplicationStatus.APPLIED, ApplicationStatus.PHONE])

    data = build_response_analytics(
        Application.objects.filter(user=user).prefetch_related('events'),
    )

    assert data['total'] == 5
    assert data['submitted'] == 4  # b, c, d, e
    assert data['responses'] == 3  # c, d, e
    assert data['offers'] == 1     # d
    assert data['rejections'] == 1
    assert data['response_rate'] == round(3 / 4, 4)
    assert data['offer_rate'] == round(1 / 4, 4)
    assert data['funnel'] == {'applied': 4, 'phone': 3, 'onsite': 1, 'offer': 1}


def test_analytics_breaks_down_by_tier(user):
    _app(user, 'a', ApplicationStatus.PHONE, tier=AutoApplyTier.AUTOFILL)
    _app(user, 'b', ApplicationStatus.APPLIED, tier=AutoApplyTier.AUTOFILL)
    _app(user, 'c', ApplicationStatus.APPLIED, tier=AutoApplyTier.ASSIST)

    data = build_response_analytics(Application.objects.filter(user=user).prefetch_related('events'))

    assert data['by_tier']['autofill'] == {
        'submitted': 2, 'responses': 1, 'offers': 0, 'response_rate': 0.5,
    }
    assert data['by_tier']['assist']['response_rate'] == 0.0


def test_analytics_empty_is_safe(user):
    data = build_response_analytics(Application.objects.filter(user=user))
    assert data['total'] == 0
    assert data['response_rate'] == 0.0
    assert data['avg_days_to_first_response'] is None


def test_avg_days_to_first_response_from_event_time(user):
    app = _app(user, 'a', ApplicationStatus.PHONE, past_statuses=[ApplicationStatus.PHONE])
    Application.objects.filter(pk=app.pk).update(created_at=timezone.now() - timedelta(days=10))
    ApplicationEvent.objects.filter(application=app).update(
        created_at=timezone.now() - timedelta(days=4),
    )

    data = build_response_analytics(Application.objects.filter(user=user).prefetch_related('events'))
    assert data['avg_days_to_first_response'] == 6.0


def test_analytics_endpoint_returns_payload(auth_client, user):
    _app(user, 'a', ApplicationStatus.PHONE)
    response = auth_client.get('/api/v1/applications/analytics/')
    assert response.status_code == 200
    assert response.data['responses'] == 1
    assert 'by_tier' in response.data and 'funnel' in response.data
