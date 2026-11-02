from datetime import date

import pytest

from jobs.models import Company, JobPosting, Source
from matching.fit import Candidate, required_years, score_fit, seniority_level
from profiles.models import Experience, Preference, Skill, StructuredProfile

pytestmark = pytest.mark.django_db

BACKEND = Candidate(
    skills={s.lower(): s for s in ['Python', 'Django', 'Kafka', 'PostgreSQL', 'AWS', 'Docker']},
    titles=['Senior Backend Engineer', 'Software Engineer'],
    text='Backend engineer building Python Django APIs, Kafka pipelines on AWS with PostgreSQL.',
    years=6, locations=['Berlin, Germany'], remote_ok=True,
)


def test_relevant_role_beats_unrelated_roles():
    good = score_fit(BACKEND, title='Senior Backend Engineer',
                     description='We use Python, Django and Kafka on AWS. PostgreSQL. Kubernetes a plus.',
                     location='Remote', remote=True)
    sales = score_fit(BACKEND, title='Account Executive',
                      description='Own a quota, prospect via Salesforce and HubSpot.', location='New York, NY')
    ios = score_fit(BACKEND, title='Staff iOS Engineer',
                    description='Swift, Objective-C, 10+ years of experience building iOS apps.',
                    location='San Francisco, CA')
    assert good['fit'] > ios['fit'] > 0
    assert good['fit'] > sales['fit']
    assert good['verdict'] in ('strong', 'good')
    assert 'Kubernetes' in good['missing_skills']
    assert 'Python' in good['matched_skills']
    kinds = {r['title']: r['kind'] for r in ios['explanation']}
    assert kinds.get('Asks for 10+ years') == 'negative'


def test_location_reasoning():
    on_site_elsewhere = score_fit(BACKEND, title='Backend Engineer', description='Python Django',
                                  location='Austin, TX', remote=False)
    in_city = score_fit(BACKEND, title='Backend Engineer', description='Python Django',
                        location='Berlin', remote=False)
    assert in_city['fit'] > on_site_elsewhere['fit']
    assert any(r['kind'] == 'negative' and 'Austin' in r['title'] for r in on_site_elsewhere['explanation'])


def test_helpers():
    assert seniority_level('Sr. Software Engineer') == 3
    assert seniority_level('Software Engineer') is None
    assert required_years('You have 5+ years of professional experience with Go.') == 5


def _profile(user):
    p = StructuredProfile.objects.create(user=user, headline='Backend Engineer')
    for s in ['Python', 'Django', 'Kafka']:
        Skill.objects.create(profile=p, name=s)
    Experience.objects.create(profile=p, company='Acme', title='Backend Engineer',
                              start_date=date(2019, 1, 1), is_current=True,
                              bullets=['Built Django services on PostgreSQL'])
    Preference.objects.create(profile=p, target_titles=['Backend Engineer'], remote=True)
    return p


def _job(ext, title, desc, **kw):
    company, _ = Company.objects.get_or_create(name=kw.pop('company', 'Acme'), domain='')
    source, _ = Source.objects.get_or_create(name='greenhouse', kind='ats_public')
    return JobPosting.objects.create(source=source, external_id=ext, company=company, title=title,
                                     description=desc, **kw)


def test_feed_ranks_and_explains(auth_client, user):
    _profile(user)
    a = _job('1', 'Backend Engineer', 'Python, Django, Kafka and PostgreSQL. Remote.', remote=True)
    _job('2', 'Marketing Manager', 'SEO, content marketing, HubSpot.', location='Paris')
    _job('3', 'Ghosty Backend Engineer', 'Python Django', ghost_risk=80)
    r = auth_client.get('/api/v1/matching/feed/')
    assert r.status_code == 200
    rows = r.data['results']
    assert rows[0]['id'] == a.id
    assert rows[0]['fit'] >= rows[-1]['fit']
    assert rows[0]['reasons']
    assert all(row['title'] != 'Ghosty Backend Engineer' for row in rows)  # hidden by default
    assert r.data['has_profile'] is True


def test_feed_hides_applied_jobs(auth_client, user):
    from applications.models import Application
    _profile(user)
    a = _job('1', 'Backend Engineer', 'Python')
    Application.objects.create(user=user, job=a, status='applied')
    ids = [row['id'] for row in auth_client.get('/api/v1/matching/feed/').data['results']]
    assert a.id not in ids
    ids = [row['id'] for row in auth_client.get('/api/v1/matching/feed/?status=all').data['results']]
    assert a.id in ids
