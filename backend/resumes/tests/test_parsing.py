import io

from resumes.parsing import extract_text, naive_structured_parse


def test_extract_text_plaintext():
    text = 'Alice\nEngineer\nPython, Django'
    out = extract_text(io.BytesIO(text.encode()), 'resume.txt')
    assert 'Alice' in out


def test_naive_structured_parse():
    data = naive_structured_parse('Alice\nEngineer\nPython')
    assert data['raw_text'].startswith('Alice')
    assert 'summary' in data
    assert data['skills'] == []
