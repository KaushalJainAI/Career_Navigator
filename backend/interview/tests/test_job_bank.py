import pytest

from applications.models import Application
from interview.grilling import _heuristic_evaluate, job_question_bank
from jobs.models import Company, JobPosting, Source
from profiles.models import Experience, Skill, StructuredProfile

pytestmark = pytest.mark.django_db

SNAP = {'skills': [{'name': 'Python'}, {'name': 'Kafka'}],
        'experiences': [{'title': 'Engineer', 'company': 'Acme', 'start': '2020-01-01',
                         'bullets': ['Built a Kafka pipeline handling 3M events/day']}]}
JD = '<ul><li>Build streaming pipelines with Kafka and Python</li><li>Run services on Kubernetes</li></ul>'


def test_job_bank_uses_jd_and_resume():
    bank = job_question_bank(role='Data Engineer', company='Stripe', stage='tech_phone', description=JD,
                             snapshot=SNAP)
    prompts = ' '.join(q['prompt'] for q in bank)
    assert 'Kafka' in prompts                     # skill you have -> prove it
    assert 'Kubernetes' in prompts                # gap -> ramp-up question
    assert 'Built a Kafka pipeline' in prompts    # résumé deep-dive
    assert 'Stripe' in prompts
    assert 4 <= len(bank) <= 7


def test_evaluator_gives_specific_feedback():
    weak = _heuristic_evaluate({'prompt': 'Tell me about a project', 'category': 'skill'}, 'We did some stuff.')
    strong = _heuristic_evaluate({'prompt': 'Tell me about a project', 'category': 'skill'},
                                 'At my last company our checkout API was timing out under load. I was asked to fix it. '
                                 'I profiled the service, I designed a Redis cache for the pricing lookups and I '
                                 'migrated the hot path to async workers. The result: p99 latency dropped from 900ms '
                                 'to 180ms and checkout conversion increased 4% the next month, which saved the '
                                 'team weeks of firefighting during the holiday peak.')
    assert strong['score'] > weak['score'] + 0.3
    assert 'too short' in weak['feedback']
    assert strong['feedback'].startswith('Strong') or 'numbers' in strong['feedback']


def test_session_from_application_uses_job(auth_client, user):
    p = StructuredProfile.objects.create(user=user, headline='Engineer')
    Skill.objects.create(profile=p, name='Kafka')
    Experience.objects.create(profile=p, company='Acme', title='Engineer', bullets=['Built Kafka pipelines'])
    c = Company.objects.create(name='Stripe', domain='stripe.com')
    s = Source.objects.create(name='gh', kind='ats_public')
    job = JobPosting.objects.create(source=s, external_id='1', company=c, title='Data Engineer', description=JD)
    app = Application.objects.create(user=user, job=job, status='phone')
    r = auth_client.post('/api/v1/interview/sessions/', {'application': app.id, 'stage': 'tech_phone'},
                         format='json')
    assert r.status_code == 201, r.data
    assert r.data['job'] == job.id and r.data['role'] == 'Data Engineer'
    prompts = [q['prompt'] for q in r.data['questions']]
    assert any('Python' in p and 'first month' in p for p in prompts)
    assert any('streaming pipelines' in p for p in prompts)
