import pytest

from portals import views
from portals.models import Portal, PortalAccount, PortalScrapeRun

pytestmark = pytest.mark.django_db


def test_portal_list_includes_all_supported_portals(auth_client, settings):
    settings.PORTAL_SESSION_COOKIES = {}
    response = auth_client.get('/api/v1/portals/')
    assert response.status_code == 200
    names = {p['name'] for p in response.data['portals']}
    assert {'linkedin', 'naukri', 'unstop', 'ycombinator'} <= names
    linkedin = next(p for p in response.data['portals'] if p['name'] == 'linkedin')
    assert linkedin['connected'] is False


def test_portal_list_marks_env_connected(auth_client, settings):
    settings.PORTAL_SESSION_COOKIES = {'linkedin': 'env-cookie'}
    response = auth_client.get('/api/v1/portals/')
    linkedin = next(p for p in response.data['portals'] if p['name'] == 'linkedin')
    assert linkedin['connected'] is True


def test_store_session_marks_account_connected(auth_client, user):
    response = auth_client.post('/api/v1/portals/linkedin/session/', {'cookie': 'abc123'}, format='json')
    assert response.status_code == 200
    account = PortalAccount.objects.get(user=user, portal__name='linkedin')
    assert account.has_session()


def test_store_session_unknown_portal_404(auth_client):
    response = auth_client.post('/api/v1/portals/monster/session/', {'cookie': 'x'}, format='json')
    assert response.status_code == 404


def test_delete_session_forgets_account(auth_client, user):
    auth_client.post('/api/v1/portals/linkedin/session/', {'cookie': 'abc'}, format='json')
    response = auth_client.delete('/api/v1/portals/linkedin/session/')
    assert response.status_code == 204
    assert not PortalAccount.objects.filter(user=user, portal__name='linkedin').exists()


def test_scrape_disabled_returns_403(auth_client, settings):
    settings.PORTAL_SCRAPER_ENABLED = False
    response = auth_client.post('/api/v1/portals/linkedin/scrape/', {'keywords': 'python'}, format='json')
    assert response.status_code == 403


def test_scrape_enabled_runs_synchronously(auth_client, user, settings, monkeypatch):
    settings.PORTAL_SCRAPER_ENABLED = True
    settings.RUN_INGESTION_ASYNC = False

    def fake_run(name, u, query):
        portal, _ = Portal.objects.get_or_create(name=name)
        return PortalScrapeRun.objects.create(
            user=u, portal=portal, status='success', stats={'created': 3},
        )

    monkeypatch.setattr(views, 'run_portal_scrape', fake_run)
    response = auth_client.post('/api/v1/portals/linkedin/scrape/', {'keywords': 'python'}, format='json')
    assert response.status_code == 200
    assert response.data['status'] == 'success'
    assert response.data['stats'] == {'created': 3}


def test_runs_list_returns_user_runs(auth_client, user):
    portal = Portal.objects.create(name='linkedin')
    PortalScrapeRun.objects.create(user=user, portal=portal, status='success')
    response = auth_client.get('/api/v1/portals/runs/')
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]['portal'] == 'linkedin'
