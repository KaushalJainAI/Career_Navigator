from celery import shared_task
from django.contrib.auth import get_user_model

from .scrapers.base import PortalQuery
from .services import run_portal_scrape


@shared_task(name='portals.run_portal_scrape')
def run_portal_scrape_task(portal_name: str, user_id: int, **query_kwargs):
    user = get_user_model().objects.get(pk=user_id)
    query = PortalQuery(**query_kwargs)
    run = run_portal_scrape(portal_name, user, query)
    return {'run_id': run.id, 'status': run.status, 'stats': run.stats}
