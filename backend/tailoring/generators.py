"""Resume tailoring + cover letter generation. Both functions accept an
optional `llm` callable so tests can inject a deterministic stub instead of
calling out to a real provider."""

from __future__ import annotations

from typing import Callable


def _default_llm(prompt: str, **_) -> str:  # pragma: no cover - replaced in prod
    return prompt[:512]


def tailor_resume(parsed_master: dict, job_title: str, job_description: str,
                  *, llm: Callable | None = None) -> dict:
    llm = llm or _default_llm
    prompt = (
        'Rewrite the following resume to maximally fit this job description, '
        'preserving truthfulness. Job title: ' + job_title + '\n\n'
        'JD:\n' + job_description + '\n\n'
        'Master resume JSON:\n' + str(parsed_master)
    )
    rewritten = llm(prompt)
    return {
        'content': {'raw_text': rewritten, 'summary': rewritten[:200]},
        'diff_from_master': {'changed_sections': ['summary']},
    }


def draft_cover_letter(parsed_master: dict, job_title: str, company_name: str,
                       job_description: str, *, llm: Callable | None = None) -> str:
    llm = llm or _default_llm
    prompt = (
        f'Write a concise, specific cover letter for {job_title} at {company_name}. '
        f'JD: {job_description}\nResume: {parsed_master}'
    )
    return llm(prompt)
