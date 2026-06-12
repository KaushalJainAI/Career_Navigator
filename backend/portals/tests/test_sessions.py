import pytest

from portals.models import Portal, PortalAccount
from portals.sessions import load_storage_state

pytestmark = pytest.mark.django_db


def test_load_storage_state_prefers_stored_account(user, settings):
    settings.PORTAL_SESSION_COOKIES = {'linkedin': 'ENVVALUE'}
    portal = Portal.objects.create(name='linkedin', display_name='LinkedIn')
    account = PortalAccount(user=user, portal=portal)
    account.set_storage_state({'cookies': [{'name': 'li_at', 'value': 'DBVALUE'}], 'origins': []})
    account.save()

    state = load_storage_state(user, 'linkedin')
    assert state['cookies'][0]['value'] == 'DBVALUE'  # DB wins over env


def test_load_storage_state_falls_back_to_env_cookie(user, settings):
    settings.PORTAL_SESSION_COOKIES = {'linkedin': 'ENVVALUE'}
    state = load_storage_state(user, 'linkedin')
    assert state['cookies'][0]['name'] == 'li_at'
    assert state['cookies'][0]['domain'] == '.linkedin.com'
    assert state['cookies'][0]['value'] == 'ENVVALUE'


def test_load_storage_state_none_when_unconfigured(user, settings):
    settings.PORTAL_SESSION_COOKIES = {}
    assert load_storage_state(user, 'linkedin') is None


def test_load_storage_state_unknown_portal(user):
    assert load_storage_state(user, 'monster') is None
