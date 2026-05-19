"""Resume parsing utilities — extracts text from PDF/DOCX and (optionally) calls an
LLM to produce a structured JSON. The LLM call is isolated so it can be mocked in tests."""

from __future__ import annotations

import io
from typing import IO

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
    return {
        'raw_text': text,
        'summary': ' '.join(lines[:3]),
        'skills': [],
        'experiences': [],
        'educations': [],
    }
