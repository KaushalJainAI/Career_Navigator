"""Resume↔Job match scorer. Combines a cosine-similarity signal on the
embedding of the resume vs the JD, a skill-overlap signal, and an optional
LLM critique. The LLM step is pluggable; the deterministic core is unit-tested."""

from __future__ import annotations

from typing import Iterable

from .embeddings import cosine, embed
from resumes.parsing import extract_skill_names


def _resume_text(parsed: dict) -> str:
    parts = [parsed.get('summary', '')]
    parts.extend([s.get('name') if isinstance(s, dict) else str(s) for s in parsed.get('skills', [])])
    for exp in parsed.get('experiences', []):
        parts.append(exp.get('title', '') if isinstance(exp, dict) else str(exp))
        parts.append(exp.get('company', '') if isinstance(exp, dict) else '')
        for b in exp.get('bullets', []) if isinstance(exp, dict) else []:
            parts.append(str(b))
    return ' '.join(p for p in parts if p)


def _normalise_skills(values: Iterable) -> set[str]:
    out = set()
    for v in values or []:
        if isinstance(v, dict):
            name = v.get('name', '')
        else:
            name = str(v)
        name = name.strip().lower()
        if name:
            out.add(name)
    return out


def score_resume_against_job(parsed_resume: dict, job_title: str, job_description: str,
                             resume_skills: Iterable | None = None,
                             jd_skills: Iterable | None = None) -> dict:
    resume_text = _resume_text(parsed_resume) or parsed_resume.get('raw_text', '')
    jd_text = f'{job_title}\n{job_description}'
    semantic = cosine(embed(resume_text), embed(jd_text))

    resume_skill_set = _normalise_skills(
        resume_skills if resume_skills is not None else parsed_resume.get('skills', []))
    jd_skill_set = _normalise_skills(jd_skills if jd_skills is not None else extract_skill_names(jd_text))
    if jd_skill_set:
        overlap = len(resume_skill_set & jd_skill_set) / len(jd_skill_set)
    else:
        overlap = 0.0

    score = round(0.6 * semantic + 0.4 * overlap, 4)
    return {
        'score': score,
        'breakdown': {'semantic': round(semantic, 4), 'skill_overlap': round(overlap, 4)},
        'gaps': sorted(jd_skill_set - resume_skill_set),
    }
