from matching.embeddings import cosine, embed, hash_embed
from matching.scorer import score_resume_against_job


def test_hash_embed_deterministic_and_normalised():
    v1 = hash_embed('python django')
    v2 = hash_embed('python django')
    assert v1 == v2
    # L2 norm
    norm = sum(x * x for x in v1) ** 0.5
    assert abs(norm - 1.0) < 1e-6


def test_cosine_identical_is_one():
    v = embed('alice engineer python')
    assert abs(cosine(v, v) - 1.0) < 1e-6


def test_score_returns_breakdown_and_gaps():
    parsed = {
        'summary': 'Backend engineer with Python and Django experience',
        'skills': [{'name': 'Python'}, {'name': 'Django'}],
    }
    out = score_resume_against_job(
        parsed,
        job_title='Senior Backend Engineer',
        job_description='Build microservices with Python, Django, Kafka',
        jd_skills=['Python', 'Django', 'Kafka'],
    )
    assert 'score' in out
    assert out['breakdown']['skill_overlap'] > 0
    assert 'kafka' in out['gaps']


def test_score_infers_jd_skills_when_not_provided():
    parsed = {
        'summary': 'Backend engineer',
        'skills': [{'name': 'Python'}, {'name': 'Django'}],
    }
    out = score_resume_against_job(
        parsed,
        job_title='Backend Engineer',
        job_description='We use Python, Django, Docker, and Kafka.',
    )

    assert out['breakdown']['skill_overlap'] == 0.5
    assert out['gaps'] == ['docker', 'kafka']
