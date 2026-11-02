"""Turn ATS job-description HTML (often entity-encoded) into readable text."""

from __future__ import annotations

import html
import re

_BLOCK = re.compile(r'</?(?:p|div|br|li|ul|ol|h[1-6]|section|tr|table)\b[^>]*>', re.IGNORECASE)
_LI = re.compile(r'<li\b[^>]*>', re.IGNORECASE)
_TAG = re.compile(r'<[^>]+>')


def description_to_text(raw: str) -> str:
    if not raw:
        return ''
    text = html.unescape(raw)
    if '&lt;' in text or '&amp;' in text:  # double-encoded (Greenhouse)
        text = html.unescape(text)
    text = _LI.sub('\n• ', text)
    text = _BLOCK.sub('\n', text)
    text = _TAG.sub('', text)
    text = text.replace(' ', ' ')
    lines = [re.sub(r'[ \t]+', ' ', ln).strip() for ln in text.splitlines()]
    out: list[str] = []
    for ln in lines:
        if ln in ('', '•'):
            if out and out[-1] != '':
                out.append('')
            continue
        out.append(ln)
    # No blank lines between consecutive bullets.
    tidy: list[str] = []
    for i, ln in enumerate(out):
        if ln == '' and tidy and tidy[-1].startswith('• ') and i + 1 < len(out) and out[i + 1].startswith('• '):
            continue
        tidy.append(ln)
    return '\n'.join(tidy).strip()
