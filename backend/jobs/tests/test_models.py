import pytest

from jobs.models import ATSType, Company, JobPosting, Source

pytestmark = pytest.mark.django_db


def test_create_company_and_job():
    company = Company.objects.create(name='Acme', domain='acme.com', ats_type=ATSType.GREENHOUSE)
    source = Source.objects.create(name='greenhouse-acme', kind='ats_public')
    job = JobPosting.objects.create(
        source=source, external_id='42', company=company, title='Engineer', remote=True
    )
    assert job.title == 'Engineer'
    assert str(job).startswith('Engineer')


def test_job_unique_per_source_external_id():
    company = Company.objects.create(name='Acme', domain='acme.com')
    source = Source.objects.create(name='greenhouse-acme', kind='ats_public')
    JobPosting.objects.create(source=source, external_id='1', company=company, title='A')
    with pytest.raises(Exception):
        JobPosting.objects.create(source=source, external_id='1', company=company, title='B')
