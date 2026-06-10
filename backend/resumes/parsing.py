"""Resume parsing utilities — extracts text from PDF/DOCX and (optionally) calls an
LLM to produce a structured JSON. The LLM call is isolated so it can be mocked in tests."""

from __future__ import annotations

import io
from typing import IO
import re

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - optional at import time
    PdfReader = None  # type: ignore

try:
    import docx  # python-docx
except ImportError:  # pragma: no cover
    docx = None  # type: ignore


def extract_text(file: IO[bytes], filename: str) -> str:
    name = (filename or '').lower()
    data = file.read()
    if name.endswith('.pdf'):
        if PdfReader is None:
            raise RuntimeError('pypdf is not installed')
        reader = PdfReader(io.BytesIO(data))
        return '\n'.join(page.extract_text() or '' for page in reader.pages)
    if name.endswith('.docx'):
        if docx is None:
            raise RuntimeError('python-docx is not installed')
        document = docx.Document(io.BytesIO(data))
        return '\n'.join(p.text for p in document.paragraphs)
    # Fallback: treat as plain text
    return data.decode('utf-8', errors='ignore')


def naive_structured_parse(text: str) -> dict:
    """Cheap rule-based parser used as a fallback when no LLM is available.
    Tests use this path; production uses an LLM call (see resumes.tasks)."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    skills = [{'name': name} for name in extract_skill_names(text)]
    return {
        'raw_text': text,
        'summary': ' '.join(lines[:3]),
        'skills': skills,
        'experiences': [],
        'educations': [],
    }


SKILL_KEYWORDS = [
    'python', 'django', 'flask', 'fastapi', 'javascript', 'typescript', 'react',
    'node', 'node.js', 'java', 'spring', 'c++', 'c#', 'go', 'golang', 'rust',
    'sql', 'postgres', 'postgresql', 'mysql', 'mongodb', 'redis', 'kafka',
    'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'graphql',
    'rest', 'celery', 'elasticsearch', 'pandas', 'numpy', 'pytorch',
    'tensorflow', 'scikit-learn', 'machine learning', 'llm', 'langchain',
]


def extract_skill_names(text: str) -> list[str]:
    haystack = f' {text.lower()} '
    found = []
    seen = set()
    for skill in SKILL_KEYWORDS:
        pattern = r'(?<![a-z0-9+#])' + re.escape(skill) + r'(?![a-z0-9+#])'
        if re.search(pattern, haystack):
            label = _skill_label(skill)
            key = label.lower()
            if key not in seen:
                seen.add(key)
                found.append(label)
    return found


def _skill_label(skill: str) -> str:
    special = {
        'node.js': 'Node.js',
        'c++': 'C++',
        'c#': 'C#',
        'sql': 'SQL',
        'aws': 'AWS',
        'azure': 'Azure',
        'gcp': 'GCP',
        'llm': 'LLM',
        'rest': 'REST',
        'typescript': 'TypeScript',
        'javascript': 'JavaScript',
        'postgresql': 'PostgreSQL',
        'mysql': 'MySQL',
    }
    return special.get(skill, skill.title())
