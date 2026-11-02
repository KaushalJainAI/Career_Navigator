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
        'hr': [
            'Tell me about yourself.',
            'Why should we hire you over other candidates?',
            'What are your strengths and one real weakness?',
            'Where do you see yourself in three years?',
            'Are you open to relocation and to working in shifts if needed?',
            'Do you have any questions for us?',
        ],
        'cs_fundamentals': [
            'Explain the difference between a process and a thread. When would you use each?',
            'What is database normalization? Walk through 1NF, 2NF and 3NF with an example.',
            'Explain the four pillars of OOP with a short example of each.',
            'What happens when you type a URL into the browser and press Enter?',
            'What is a deadlock? What conditions cause it and how can it be prevented?',
            'Explain the difference between TCP and UDP and give a use case for each.',
            'What is the difference between an INNER JOIN and a LEFT JOIN? Write a query using one.',
            'How does a hash map work internally, and what is the time complexity of lookups?',
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
    """STAR-style heuristic: structure, specificity, outcome, ownership.

    Not a substitute for a human, but it catches the four most common
    weaknesses in practice answers and says exactly what to fix."""
    import re as _re
    text = answer or ''
    low = text.lower()
    words = text.split()
    n = len(words)
    category = question.get('category', '')
    short_ok = category == 'recruiter' or 'salary' in question.get('prompt', '').lower()

    # structure: a context → action → result arc, and a sensible length
    has_context = bool(_re.search(r'\b(when|at my|in my|our team|the project|we had|there was|i was)\b', low))
    has_action = bool(_re.search(r'\b(i (built|led|designed|wrote|decided|created|owned|proposed|drove|fixed|'
                                 r'implemented|migrated|shipped|ran|set up|introduced|talked|worked))\b', low))
    has_result = bool(_re.search(r'\b(result|resulted|so that|which (cut|reduced|increased|improved|saved)|'
                                 r'impact|outcome|shipped|launched|reduced|increased|improved|saved|grew|cut)\b', low))
    target = 25 if short_ok else 90
    length = min(1.0, n / target)
    structure = round(min(1.0, 0.4 * length + 0.2 * has_context + 0.2 * has_action + 0.2 * has_result), 3)
    numbers = _re.findall(r'\d+(?:\.\d+)?\s*(?:%|x|ms|s|k|m|users|customers|people|engineers|hours|days|weeks)?',
                          low)
    specificity = round(min(1.0, 0.35 + 0.25 * len(numbers) + (0.2 if _re.search(r'[A-Z][a-z]+[A-Z]|[A-Z]{2,}', text) else 0)), 3)
    outcome = 1.0 if has_result and numbers else (0.6 if has_result else 0.25)
    i_count = len(_re.findall(r'\bi\b', low))
    we_count = len(_re.findall(r'\bwe\b', low))
    ownership = 1.0 if i_count >= we_count else (0.6 if i_count else 0.3)
    if short_ok:
        score = round((structure + specificity + ownership) / 3, 4)
    else:
        score = round(0.3 * structure + 0.25 * specificity + 0.3 * outcome + 0.15 * ownership, 4)

    weak: list[str] = []
    strengths: list[str] = []
    if n < (10 if short_ok else 40):
        weak.append('answer is too short — aim for 60–120 seconds when spoken')
    elif not short_ok and n > 350:
        weak.append('answer is long — lead with the headline, then the details')
    if not short_ok:
        if not has_context:
            weak.append('set the scene first: where you were and what the problem was')
        if not has_action:
            weak.append('say what YOU did, with action verbs ("I designed…", "I led…")')
        if outcome < 0.6:
            weak.append('finish with the measurable result (numbers, before/after)')
        elif outcome < 1.0:
            weak.append('quantify the result — a number makes it memorable')
        if ownership < 1.0 and we_count > 2:
            weak.append('too much "we" — make your own contribution clear')
    if numbers:
        strengths.append('uses concrete numbers')
    if has_action:
        strengths.append('clear personal ownership')
    if has_result:
        strengths.append('ends with an outcome')
    feedback = ('Strong: ' + ', '.join(strengths) + '.') if not weak else \
        ('Improve: ' + '; '.join(weak) + '.' + (f' Good: {", ".join(strengths)}.' if strengths else ''))
    return {
        'structure': structure,
        'specificity': specificity,
        'outcome': outcome,
        'ownership': ownership,
        'score': score,
        'feedback': feedback,
        'strengths': strengths,
        'gaps': weak,
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
    from collections import Counter
    counts = Counter(g for t in turns for g in t.get('gaps', []))
    ordered = [g for g, _ in counts.most_common()] + [g for g in gaps if g not in counts]
    gaps = ordered
    study_plan = [{'topic': g[0].upper() + g[1:],
                   'action': 'Rewrite your weakest answer with this fixed, then say it out loud and time yourself.'}
                  for g in ordered][:5]
    return {
        'overall_score': overall,
        'strengths': strengths,
        'gaps': gaps,
        'study_plan': study_plan,
    }


# ---------------------------------------------------------------- job-aware bank

def job_question_bank(*, role: str, company: str, stage: str, description: str = '',
                      snapshot: dict | None = None, difficulty: str = 'medium', count: int = 7) -> list[dict]:
    """Questions built from THIS job description and THIS candidate's résumé.

    Deterministic: the skills the JD stresses that you have (prove it), the
    ones you lack (how would you ramp up), the JD's own responsibilities,
    a deep-dive on your strongest résumé bullet, plus stage staples."""
    from jobs.text import description_to_text
    from matching.fit import job_skill_weights
    from tailoring.engine import _jd_responsibility, profile_skill_set, tailor

    snapshot = snapshot or {}
    jd_text = description_to_text(description)
    weights = job_skill_weights(role, description)
    have = profile_skill_set(snapshot) if snapshot else set()
    ranked = sorted(weights, key=lambda s: -weights[s])
    matched = [s for s in ranked if s.lower() in have]
    missing = [s for s in ranked if s.lower() not in have]
    company_label = company or 'this company'

    def q(prompt, category, signals):
        return {'prompt': prompt, 'category': category, 'difficulty': difficulty, 'expected_signals': signals}

    star = ['situation', 'your actions', 'measurable result']
    bank: list[dict] = []
    best_bullet = ''
    if snapshot.get('experiences'):
        t = tailor(snapshot, job_title=role, company=company, description=description, jd_skills=weights)
        for e in t['content']['experiences']:
            if e.get('bullets'):
                best_bullet = e['bullets'][0]
                break
    resp = _jd_responsibility(jd_text, set()) if jd_text else ''

    projects = [p for p in (snapshot.get('projects') or []) if p.get('name')]
    if stage == 'hr':
        bank += [
            q(f'Tell me about yourself — in the context of this {role} role.', 'hr', ['concise arc', 'relevance']),
            q(f'Why do you want to join {company_label}?', 'hr', ['company specifics', 'motivation']),
        ]
        if projects:
            bank.append(q(f'Which project are you proudest of — {projects[0]["name"]} or another — and why?', 'hr',
                          ['ownership', 'impact']))
    elif stage == 'cs_fundamentals':
        for s in matched[:2]:
            bank.append(q(f'You list {s}. Explain how it works under the hood, as you would to a junior.', 'cs',
                          ['correct concepts', 'clarity', 'example']))
    elif stage == 'recruiter':
        bank += [
            q(f'Walk me through your background and why it fits a {role} role.', 'recruiter', ['concise arc', 'relevance']),
            q(f'Why {company_label}, and why now?', 'recruiter', ['company specifics', 'motivation']),
            q('What are you looking for in your next role?', 'recruiter', ['clarity', 'alignment']),
        ]
        if matched:
            bank.append(q(f'Give me a quick example of your work with {matched[0]}.', 'recruiter', star))
        bank.append(q('What are your salary expectations and notice period?', 'recruiter', ['range', 'flexibility']))
    else:
        for s in matched[:2]:
            bank.append(q(f'Tell me about the most complex thing you built with {s}. What trade-offs did you make?',
                          'skill', ['context', 'trade-offs', 'outcome']))
        if best_bullet:
            bank.append(q(f'On your résumé: “{best_bullet.rstrip(".")}.” Walk me through it — what was your '
                          'specific contribution and how did you measure success?', 'resume', star))
        for p in projects[:2 if not best_bullet else 1]:
            bank.append(q(f'Walk me through your project {p["name"]}: the problem, your design choices, '
                          'what broke and what you would do differently.', 'project',
                          ['problem', 'design choices', 'trade-offs', 'learning']))
        if resp:
            bank.append(q(f'This role involves “{resp}”. Tell me about a time you did something similar.',
                          'role', star))
        for s in missing[:1]:
            bank.append(q(f'The team uses {s}, which isn\'t on your résumé. How would you get productive with it '
                          'in your first month?', 'gap', ['honesty', 'learning plan', 'transferable skills']))
        if stage == 'system_design':
            bank.insert(0, q(f'Design a core system {company_label} might run for this role\'s product area. '
                             'Start with requirements, then scale it.', 'system_design',
                             ['requirements', 'data model', 'scaling', 'trade-offs']))
        bank.append(q(f'Why do you want to work at {company_label}?', 'motivation', ['company specifics', 'fit']))
    seed = _seed_bank(role, 'behavioral' if stage in ('role_specific', 'tech_phone') else stage, difficulty, 12)
    seen = {b['prompt'] for b in bank}
    for item in seed:
        if len(bank) >= count:
            break
        if item['prompt'] not in seen:
            bank.append(item)
    return bank[:count]
