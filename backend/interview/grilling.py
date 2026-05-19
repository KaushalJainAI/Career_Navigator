"""Core mechanics of the Interview Grill Chat Agent.

Three concerns kept separate so each is unit-testable in isolation:
  - `research()`            : gathers company/role/interview-process info
  - `generate_question_bank`: produces a tailored list of questions
  - `evaluate_answer`       : scores a single answer against a rubric
  - `summarise_session`     : builds the post-session report

Each function accepts an optional `llm` callable so tests can inject a stub.
Production wires the LLM via NVIDIA NIM / OpenRouter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class Rubric:
    signals: list[str]
    must_have: list[str]
    nice_to_have: list[str]


def _default_llm(prompt: str, **_) -> str:  # pragma: no cover - replaced in tests/prod
    return ''


def research(company_name: str, role: str, stage: str, *, llm: Callable | None = None) -> dict:
    """Phase 2 tool — returns notes the question generator will use as context."""
    llm = llm or _default_llm
    prompt = (
        f'Summarise what a candidate should know about {company_name} for a {stage} interview '
        f'targeting the role of {role}. Include culture, typical interview process, '
        f'commonly-asked questions, and red flags.'
    )
    notes = llm(prompt) or ''
    return {
        'company': company_name,
        'role': role,
        'stage': stage,
        'notes': notes,
        'sources': [],
    }


def generate_question_bank(role: str, stage: str, *, difficulty: str = 'medium',
                           research_notes: dict | None = None,
                           llm: Callable | None = None, count: int = 8) -> list[dict]:
    llm = llm or _default_llm
    if llm is _default_llm:
        return _seed_bank(role, stage, difficulty, count)
    prompt = (
        f'Generate {count} interview questions for a {stage} round for a {role} role at '
        f'difficulty {difficulty}. Output as plain lines. Context:\n'
        f'{(research_notes or {}).get("notes", "")}'
    )
    raw = llm(prompt) or ''
    lines = [ln.strip(' -•\t') for ln in raw.splitlines() if ln.strip()]
    return [
        {'prompt': line, 'category': stage, 'difficulty': difficulty,
         'expected_signals': []}
        for line in lines[:count]
    ] or _seed_bank(role, stage, difficulty, count)


def _seed_bank(role: str, stage: str, difficulty: str, count: int) -> list[dict]:
    """Deterministic seed so tests work without an LLM and Phase-1 dev has fallbacks."""
    base = {
        'recruiter': [
            'Walk me through your background.',
            'Why are you interested in this role?',
            'What are your salary expectations?',
            'When can you start?',
        ],
        'tech_phone': [
            'Describe a system you built end-to-end and the trade-offs.',
            'How do you debug a slow API endpoint?',
            'What is the difference between a process and a thread?',
            'Walk through your favourite recent code review.',
        ],
        'system_design': [
            'Design a URL shortener.',
            'Design a notification system.',
            'Design a real-time job board.',
            'How would you handle 10x traffic on this service?',
        ],
        'behavioral': [
            'Tell me about a time you disagreed with your manager.',
            'Describe a project you led that failed.',
            'How do you handle ambiguous requirements?',
            'Give an example of cross-team collaboration.',
        ],
        'role_specific': [
            f'What is the hardest thing about being a {role}?',
            f'How do you measure success as a {role}?',
            f'Describe your dream first 90 days as a {role}.',
            f'Tell me about a {role}-specific tool you’d remove from your stack.',
        ],
    }
    pool = base.get(stage, base['behavioral'])
    return [
        {'prompt': p, 'category': stage, 'difficulty': difficulty,
         'expected_signals': ['structure', 'specificity', 'outcome']}
        for p in pool[:count]
    ]


def evaluate_answer(question: dict, answer: str, *, llm: Callable | None = None) -> dict:
    """Scores 0–1 on (structure, specificity, outcome) using STAR-style rubric.
    Falls back to a tiny heuristic when no LLM is configured — keeps tests stable."""
    llm = llm or _default_llm
    if llm is _default_llm:
        return _heuristic_evaluate(question, answer)
    prompt = (
        f'Question: {question.get("prompt", "")}\nAnswer: {answer}\n'
        'Score the answer on structure, specificity, and outcome (each 0..1). '
        'Return JSON like {"structure":0.8,"specificity":0.5,"outcome":0.7,"feedback":"..."}.'
    )
    raw = llm(prompt) or ''
    return _parse_eval(raw, fallback=_heuristic_evaluate(question, answer))


def _heuristic_evaluate(question: dict, answer: str) -> dict:
    n = len((answer or '').split())
    structure = min(1.0, n / 60)
    specificity = 1.0 if any(t.isdigit() for t in (answer or '').split()) else 0.4
    outcome = 1.0 if any(w in answer.lower() for w in ('result', 'impact', 'shipped', 'increased', 'reduced')) else 0.3
    score = round((structure + specificity + outcome) / 3, 4)
    weak = []
    if structure < 0.5:
        weak.append('add a clear situation→task→action→result arc')
    if specificity < 0.5:
        weak.append('cite a specific metric or number')
    if outcome < 0.5:
        weak.append('describe the measurable outcome / impact')
    return {
        'structure': structure,
        'specificity': specificity,
        'outcome': outcome,
        'score': score,
        'feedback': '; '.join(weak) or 'Strong, specific, outcome-driven.',
        'drill_focus': weak[0] if weak else None,
    }


def _parse_eval(raw: str, *, fallback: dict) -> dict:
    import json
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except Exception:  # noqa: BLE001
        pass
    return fallback


def summarise_session(turns: list[dict]) -> dict:
    if not turns:
        return {'overall_score': 0.0, 'strengths': [], 'gaps': [], 'study_plan': []}
    overall = round(sum(t.get('score', 0) for t in turns) / len(turns), 4)
    strengths = sorted({
        s for t in turns for s in t.get('strengths', [])
    })
    gaps = sorted({
        g for t in turns for g in t.get('gaps', [])
    } | {
        t['drill_focus'] for t in turns if t.get('drill_focus')
    })
    study_plan = [{'topic': g, 'action': f'Practice 3 examples that fix: {g}'} for g in gaps][:5]
    return {
        'overall_score': overall,
        'strengths': strengths,
        'gaps': gaps,
        'study_plan': study_plan,
    }
