"""Turn a raw job posting into a structured breakdown using an LLM.

The posting model only stores a title, company and a free-text description. This
module expands that into responsibilities / requirements / benefits / a short
company blurb so the detail page has real, role-specific content instead of
placeholders. There is deliberately NO fabricating fallback: with no LLM
configured the caller gets ``None`` and the UI keeps its honest empty state.
"""
from __future__ import annotations

import json
import re
from typing import Callable


def _extract_json(raw: str) -> dict | None:
    """Best-effort parse of a JSON object from an LLM response, tolerating
    markdown code fences and surrounding prose."""
    if not raw:
        return None
    text = raw.strip()
    text = re.sub(r'^```(?:json)?', '', text).strip()
    text = re.sub(r'```$', '', text).strip()
    start, end = text.find('{'), text.rfind('}')
    if start == -1 or end == -1 or end < start:
        return None
    try:
        parsed = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _clean_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    seen, out = set(), []
    for item in value:
        s = str(item).strip()
        if s and s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
    return out[:6]


def generate_breakdown(title: str, company_name: str, description: str,
                       *, llm: Callable[[str], str] | None) -> dict | None:
    """Return a structured breakdown dict, or ``None`` if generation isn't
    possible (no LLM) or the model returned nothing usable."""
    if llm is None:
        return None
    prompt = (
        'You expand a job posting into a structured breakdown for a candidate. '
        'Ground everything in the posting; if it is short, infer only what is standard '
        'and clearly implied for this exact role. Never invent specifics such as salary '
        'figures, headcount or team names.\n\n'
        f'Role title: {title}\n'
        f'Company: {company_name}\n'
        f'Posting description: {description.strip() or "(no description provided)"}\n\n'
        'Output ONLY a JSON object — no preamble, no markdown fences, no commentary — '
        'of exactly this shape:\n'
        '{"responsibilities": ["..."], "requirements": ["..."], '
        '"benefits": ["..."], "about_company": "..."}\n'
        'Rules: 3-5 items per list; each item a short phrase under 14 words; '
        'about_company at most two sentences. Use an empty list rather than guessing.'
    )
    data = _extract_json(llm(prompt) or '')
    if not data:
        return None
    breakdown = {
        'responsibilities': _clean_list(data.get('responsibilities')),
        'requirements': _clean_list(data.get('requirements')),
        'benefits': _clean_list(data.get('benefits')),
        'about_company': str(data.get('about_company', '')).strip(),
    }
    # Require at least some real content, otherwise treat as a failed generation.
    if not (breakdown['responsibilities'] or breakdown['requirements']):
        return None
    return breakdown
