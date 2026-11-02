"""Resume parsing utilities — extracts text from PDF/DOCX and (optionally) calls an
LLM to produce a structured JSON. The LLM call is isolated so it can be mocked in tests."""

from __future__ import annotations

import io
from typing import IO
import re

from .resume_parser import parse_resume
from .skills import extract_skills

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
        lines = [p.text for p in document.paragraphs]
        # Many résumé templates lay sections out in tables; keep that text too.
        for table in document.tables:
            for row in table.rows:
                seen_cells = set()
                for cell in row.cells:
                    if id(cell._tc) in seen_cells:
                        continue
                    seen_cells.add(id(cell._tc))
                    lines.extend(p.text for p in cell.paragraphs)
        return '\n'.join(lines)
    # Fallback: treat as plain text
    return data.decode('utf-8', errors='ignore')


def naive_structured_parse(text: str) -> dict:
    """Rule-based structured parse used when no LLM is available.

    Kept for backwards compatibility; delegates to `parse_resume`, which pulls
    out contact info, sections, experience entries, education and skills."""
    return parse_resume(text)


def extract_skill_names(text: str) -> list[str]:
    """Canonical skill names mentioned in `text` (see resumes.skills)."""
    return extract_skills(text)
