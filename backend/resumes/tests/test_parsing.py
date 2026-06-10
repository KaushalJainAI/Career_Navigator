import io

from resumes.parsing import extract_skill_names, extract_text, naive_structured_parse


def test_extract_text_plaintext():
    text = 'Alice\nEngineer\nPython, Django'
    out = extract_text(io.BytesIO(text.encode()), 'resume.txt')
    assert 'Alice' in out


def test_naive_structured_parse():
    data = naive_structured_parse('Alice\nEngineer\nPython and Django')
    assert data['raw_text'].startswith('Alice')
    assert 'summary' in data
    assert data['skills'] == [{'name': 'Python'}, {'name': 'Django'}]


def test_extract_skill_names_uses_known_keyword_boundaries():
    skills = extract_skill_names('Built REST APIs with TypeScript, React, PostgreSQL, and Kafka.')
    assert skills == ['TypeScript', 'React', 'PostgreSQL', 'Kafka', 'REST']
