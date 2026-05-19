import pytest

from applications.models import Application, ApplicationStatus, AutoApplySession
from jobs.models import Company, JobPosting, Source

pytestmark = pytest.mark.django_db


def test_application_flow(user):
    company = Company.objects.create(name='Acme', domain='acme.com')
    source = Source.objects.create(name='greenhouse-acme', kind='ats_public')
    job = JobPosting.objects.create(source=source, external_id='1', company=company, title='Eng')
    app = Application.objects.create(user=user, job=job)
    assert app.status == ApplicationStatus.SAVED

    session = AutoApplySession.objects.create(user=user)
    token = session.issue_approval_token()
    assert token
    assert session.state == 'waiting_approval'
    app.auto_apply_session = session
    app.save()
    assert app.auto_apply_session.approval_token == token
