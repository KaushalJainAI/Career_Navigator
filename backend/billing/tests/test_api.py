import pytest

from billing.models import CreditLedger

pytestmark = pytest.mark.django_db


def test_billing_summary_reports_credit_balance(auth_client, user):
    CreditLedger.objects.create(user=user, delta=100, reason='signup_bonus')
    CreditLedger.objects.create(user=user, delta=-20, reason='tailor_resume')

    response = auth_client.get('/api/v1/billing/summary/')

    assert response.status_code == 200
    assert response.data['balance'] == 80
    assert response.data['stripe_enabled'] is False


def test_manual_top_up_creates_ledger_row(auth_client, user):
    response = auth_client.post('/api/v1/billing/top-up/', {'amount': 250}, format='json')

    assert response.status_code == 201
    assert response.data['delta'] == 250
    assert CreditLedger.objects.filter(user=user, delta=250, reason='top_up').exists()


def test_manual_top_up_rejects_invalid_amount(auth_client):
    response = auth_client.post('/api/v1/billing/top-up/', {'amount': 0}, format='json')

    assert response.status_code == 400
