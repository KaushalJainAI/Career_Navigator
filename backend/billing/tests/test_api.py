import pytest

from billing.models import CreditLedger
from billing.pricing import PRICING, SIGNUP_BONUS
from billing.services import InsufficientCredits, balance, charge, grant_signup_bonus

pytestmark = pytest.mark.django_db


def test_new_user_gets_signup_bonus(user):
    # The post_save signal grants the welcome bonus exactly once.
    assert CreditLedger.objects.filter(user=user, reason='signup_bonus').count() == 1
    assert balance(user) == SIGNUP_BONUS


def test_signup_bonus_is_idempotent(user):
    assert grant_signup_bonus(user) is None  # already granted at creation
    assert CreditLedger.objects.filter(user=user, reason='signup_bonus').count() == 1


def test_billing_summary_reports_balance_and_breakdown(auth_client, user):
    CreditLedger.objects.create(user=user, delta=-20, reason='tailor_resume')

    response = auth_client.get('/api/v1/billing/summary/')

    assert response.status_code == 200
    assert response.data['balance'] == SIGNUP_BONUS - 20
    assert response.data['spent_total'] == 20
    assert response.data['earned_total'] == SIGNUP_BONUS
    assert response.data['spent_by_reason']['tailor_resume'] == 20
    assert response.data['stripe_enabled'] is False
    assert response.data['credits_never_expire'] is True
    assert any(item['reason'] == 'tailor_resume' for item in response.data['pricing'])


def test_pricing_endpoint_lists_costs(auth_client):
    response = auth_client.get('/api/v1/billing/pricing/')

    assert response.status_code == 200
    assert response.data['signup_bonus'] == SIGNUP_BONUS
    reasons = {item['reason'] for item in response.data['items']}
    assert reasons == set(PRICING)
    for item in response.data['items']:
        assert item['cost'] == PRICING[item['reason']]
        assert item['blurb']  # every action explains its value


def test_charge_deducts_and_records_ledger(user):
    start = balance(user)
    row = charge(user, 'tailor_resume')

    assert row.delta == -PRICING['tailor_resume']
    assert balance(user) == start - PRICING['tailor_resume']


def test_charge_raises_when_insufficient(user):
    # Drain the account below the cost of the action.
    CreditLedger.objects.create(user=user, delta=-SIGNUP_BONUS, reason='tailor_resume')
    with pytest.raises(InsufficientCredits) as exc:
        charge(user, 'autonomous_apply')
    assert exc.value.status_code == 402
    assert exc.value.cost == PRICING['autonomous_apply']


def test_free_action_charges_nothing(user):
    start = balance(user)
    assert charge(user, 'not_a_paid_action') is None
    assert balance(user) == start


def test_manual_top_up_creates_ledger_row(auth_client, user):
    response = auth_client.post('/api/v1/billing/top-up/', {'amount': 250}, format='json')

    assert response.status_code == 201
    assert response.data['delta'] == 250
    assert CreditLedger.objects.filter(user=user, delta=250, reason='top_up').exists()


def test_manual_top_up_rejects_invalid_amount(auth_client):
    response = auth_client.post('/api/v1/billing/top-up/', {'amount': 0}, format='json')

    assert response.status_code == 400
