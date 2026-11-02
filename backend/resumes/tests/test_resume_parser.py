from pathlib import Path

from resumes.resume_parser import parse_resume
from resumes.skills import canonical_skill, extract_skills

FIX = Path(__file__).parent / 'fixtures'


def _load(name):
    return parse_resume((FIX / name).read_text())


def test_contact_and_identity():
    d = _load('backend_engineer.txt')
    assert d['full_name'] == 'Priya Sharma'
    assert d['headline'] == 'Senior Backend Engineer'
    assert d['email'] == 'priya.sharma@gmail.com'
    assert d['phone'] == '+91 98765 43210'
    assert d['location'] == 'Bengaluru, India'
    assert d['linkedin'] == 'https://linkedin.com/in/priyasharma'
    assert d['github'] == 'https://github.com/priyas'
    assert d['website'] == ''  # the email's local part is not a website


def test_experience_entries_inline_and_stacked_headers():
    exps = _load('backend_engineer.txt')['experiences']
    assert [(e['title'], e['company']) for e in exps] == [
        ('Senior Software Engineer', 'Razorpay'), ('Software Engineer', 'Flipkart')]
    assert exps[0]['is_current'] and exps[0]['start_date'] == '2021-01-01'
    assert exps[1]['end_date'] == '2020-12-01'
    # wrapped bullet is joined back together
    assert any(b.endswith('900ms to 220ms.') for b in exps[0]['bullets'])
    assert len(exps[0]['bullets']) == 3


def test_sentence_bullets_and_parenthetical_location():
    exps = _load('product_designer.txt')['experiences']
    assert exps[0]['company'] == 'Notion' and exps[0]['location'] == 'Remote'
    assert exps[1]['company'] == 'Airbnb'
    assert len(exps[0]['bullets']) == 2


def test_education_projects_and_skills():
    d = _load('backend_engineer.txt')
    edu = d['educations'][0]
    assert edu['institution'].startswith('Indian Institute of Technology')
    assert edu['degree'] == 'B.Tech' and edu['field_of_study'] == 'Computer Science'
    assert edu['gpa'] == '8.6/10'
    assert d['projects'][0]['name'] == 'OpenLedger'
    assert d['projects'][0]['url'] == 'https://github.com/priyas/openledger'
    names = {s['name'] for s in d['skills']}
    assert {'Python', 'Go', 'Kubernetes', 'PostgreSQL', 'Kafka', 'Django'} <= names


def test_skill_aliases_and_ambiguity():
    assert canonical_skill('postgres') == 'PostgreSQL'
    assert canonical_skill('k8s') == 'Kubernetes'
    found = extract_skills('Ran ML models on k8s with postgres. I like to go hiking.')
    assert 'Machine Learning' in found and 'Kubernetes' in found and 'PostgreSQL' in found
    assert 'Go' not in found  # lower-case "go" is English, not Golang


def test_school_line_and_degree_words_are_not_skills():
    d = parse_resume('Sneha Iyer\nsneha@x.com\n\nEDUCATION\nNational Institute of Technology, Warangal\n'
                     'B.Tech in Electronics and Communication Engineering | 2022 - 2026 | CGPA: 7.9/10\n'
                     'Narayana Junior College — Class XII, 2022, 94%\n\nSKILLS\nPython, SQL')
    school = d['educations'][1]
    assert (school['institution'], school['degree'], school['gpa']) == ('Narayana Junior College', 'Class XII', '94%')
    assert d['educations'][0]['gpa'] == '7.9/10'
    names = {s['name'] for s in d['skills']}
    assert 'Communication Skills' not in names and 'Communication' not in names
