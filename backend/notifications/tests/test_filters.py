import pytest

from jobs.models import Company, JobPosting, Source
from notifications.filters import match_filter

pytestmark = pytest.mark.django_db


@pytest.fixture
def job_factory():
    src = Source.objects.create(name='s', kind='aggregator')

    def make(title='Backend Engineer', company_name='Acme', remote=True, location='Remote',
             salary_max=120000, description='Build microservices with Python and Django'):
        company, _ = Company.objects.get_or_create(name=company_name)
        return JobPosting.objects.create(
            source=src, external_id=title + company_name, company=company, title=title,
            description=description, location=location, remote=remote, salary_max=salary_max,
        )

    return make


def test_title_match(job_factory):
    job = job_factory(title='Senior Backend Engineer')
    assert match_filter(job, {'titles': ['engineer']}) is True
    assert match_filter(job, {'titles': ['designer']}) is False


def test_remote_required(job_factory):
    job = job_factory(remote=False, location='NYC')
    assert match_filter(job, {'remote': True}) is False
    assert match_filter(job_factory(remote=True), {'remote': True}) is True


def test_exclude_company(job_factory):
    job = job_factory(company_name='EvilCorp')
    assert match_filter(job, {'exclude_companies': ['evilcorp']}) is False


def test_salary_min(job_factory):
    job = job_factory(salary_max=80000)
    assert match_filter(job, {'salary_min': 100000}) is False


def test_keywords(job_factory):
    job = job_factory(description='Build microservices with Python and Django')
    assert match_filter(job, {'keywords': ['django']}) is True
    assert match_filter(job, {'keywords': ['rust']}) is False
