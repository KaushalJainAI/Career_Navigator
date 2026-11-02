import json

import pytest

from tailoring.engine import (
    draft_cover_letter,
    llm_polish,
    tailor,
    verify_cover_letter,
    verify_rewrite,
)

SNAP = {
    'full_name': 'Priya Sharma', 'headline': 'Senior Backend Engineer', 'email': 'p@x.com', 'phone': '',
    'location': 'Bengaluru', 'links': [], 'summary': 'Backend engineer.',
    'skills': [{'name': 'Python'}, {'name': 'Figma'}, {'name': 'Kafka'}],
    'experiences': [
        {'title': 'Senior Engineer', 'company': 'Razorpay', 'start': '2021-01-01', 'end': '', 'is_current': True,
         'bullets': ['Organised the team offsite.',
                     'Built a Kafka pipeline on PostgreSQL processing 3M events/day.',
                     'Mentored 4 engineers.']},
        {'title': 'Engineer', 'company': 'Flipkart', 'start': '2018-07-01', 'end': '2020-12-01', 'is_current': False,
         'bullets': ['Built Django REST APIs used by 200k sellers.']},
    ],
    'educations': [], 'projects': [],
}
JD = '<p>Senior Backend Engineer</p><ul><li>Build event pipelines with Kafka and PostgreSQL</li>' \
     '<li>Python and Django services</li><li>Kubernetes experience</li></ul>'


def test_tailor_reorders_truthfully_and_flags_gaps():
    out = tailor(SNAP, job_title='Senior Backend Engineer', company='Stripe', description=JD)
    c = out['content']
    names = [s['name'] for s in c['skills']]
    assert names[0] in ('Kafka', 'Python') and names.index('Figma') > names.index('Kafka')
    # PostgreSQL / Django are evidenced in bullets -> surfaced, not invented
    assert 'PostgreSQL' in names and 'Django' in names
    assert 'Kubernetes' not in names and 'Kubernetes' in out['missing_skills']
    assert c['experiences'][0]['bullets'][0].startswith('Built a Kafka pipeline')
    # identity untouched
    assert [(e['title'], e['company']) for e in c['experiences']] == [
        ('Senior Engineer', 'Razorpay'), ('Engineer', 'Flipkart')]
    assert 'Senior Backend Engineer with' in c['summary'] and 'Razorpay' in c['summary']
    assert out['suggestions'] and 'Kubernetes' in out['suggestions'][0]
    assert 'experience' in out['diff_from_master']['changed_sections']


def test_verify_rewrite_blocks_invented_skills_and_numbers():
    allowed = {'python', 'kafka'}
    assert verify_rewrite('Built pipeline for 3M events', 'Built Kafka pipeline for 3M events',
                          allowed_skills=allowed) == []
    probs = verify_rewrite('Built pipeline', 'Built Kubernetes pipeline for 10M events', allowed_skills=allowed)
    assert any('Kubernetes' in p for p in probs) and any('10' in p for p in probs)


def test_llm_polish_keeps_verified_edits_only():
    base = tailor(SNAP, job_title='Backend Engineer', company='Stripe', description=JD)

    def fake_llm(prompt):
        exps = [e['bullets'] for e in base['content']['experiences']]
        exps[0] = ['Designed a Kafka pipeline on PostgreSQL handling 3M events/day.'] + exps[0][1:]
        exps[1] = ['Led a Kubernetes migration saving 50%.']  # fabricated -> must be rejected
        return json.dumps({'summary': 'Backend engineer fluent in Rust.', 'experiences': exps})

    out = llm_polish(base, SNAP, job_title='Backend Engineer', company='Stripe', llm=fake_llm)
    c = out['content']
    assert c['experiences'][0]['bullets'][0].startswith('Designed a Kafka pipeline')
    assert c['experiences'][1]['bullets'][0] == 'Built Django REST APIs used by 200k sellers.'
    assert 'Rust' not in c['summary']
    assert any('Summary rewrite rejected' in n for n in out['verification'])


def test_llm_polish_garbage_falls_back():
    base = tailor(SNAP, job_title='Backend Engineer', company='Stripe', description=JD)
    out = llm_polish(base, SNAP, job_title='x', company='y', llm=lambda p: 'not json')
    assert out['content']['summary'] == base['content']['summary']


def test_cover_letter_is_factual_and_signed():
    t = tailor(SNAP, job_title='Senior Backend Engineer', company='Stripe', description=JD)
    letter = draft_cover_letter(SNAP, t, job_title='Senior Backend Engineer', company='Stripe', description=JD)
    assert letter.startswith('Dear Stripe hiring team,')
    assert 'At Razorpay, I built a Kafka pipeline' in letter
    assert letter.rstrip().endswith('p@x.com') and 'Priya Sharma' in letter
    assert 'Kubernetes' in letter  # gap acknowledged honestly
    assert verify_cover_letter('Dear team, I know Rust. Bob', SNAP)  # wrong name + fake skill flagged
