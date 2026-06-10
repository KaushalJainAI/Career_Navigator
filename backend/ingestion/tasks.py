from celery import shared_task

from jobs.models import Source

from .adapters.adzuna import AdzunaAdapter
from .adapters.base import AdapterContext
from .adapters.greenhouse import GreenhouseAdapter
from .adapters.jooble import JoobleAdapter
from .adapters.jsearch import JSearchAdapter
from .adapters.lever import LeverAdapter
from .services import run_adapter


ADAPTER_REGISTRY = {
    'adzuna': AdzunaAdapter,
    'greenhouse': GreenhouseAdapter,
    'jooble': JoobleAdapter,
    'jsearch': JSearchAdapter,
    'lever': LeverAdapter,
}


@shared_task(name='ingestion.run_source')
def run_source(source_name: str, **kwargs):
    source = Source.objects.filter(name=source_name, enabled=True).first()
    if source is None:
        return {'error': f'source {source_name!r} not found or disabled'}
    cls = ADAPTER_REGISTRY.get(source.kind) or ADAPTER_REGISTRY.get(source_name)
    if cls is None:
        return {'error': f'no adapter registered for {source.kind!r}'}
    adapter = cls()
    ctx = AdapterContext(**kwargs) if kwargs else AdapterContext()
    run = run_adapter(source, adapter, ctx)
    return {'run_id': run.id, 'status': run.status, 'stats': run.stats}
