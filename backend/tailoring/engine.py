"""Truthful, per-job résumé tailoring and cover-letter drafting.

Works with no LLM. The deterministic engine only *selects, orders and
summarises* facts that already exist in the candidate's profile:

  - skills the job asks for move to the front (nothing is added);
  - each role's bullets are re-ranked by relevance to the JD, older roles are
    trimmed to their most relevant bullets;
  - projects are ranked the same way;
  - a factual summary is composed from headline, years, matched skills and
    the single most relevant achievement;
  - JD skills the candidate lacks become *suggestions*, never insertions.

When an LLM is configured it may rewrite the summary and bullets, but every
rewrite passes `verify_rewrite` (no new skills, no new numbers, no new
employers) or the deterministic text is kept — the check fails closed.
"""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Callable

from jobs.text import description_to_text
from matching.fit import job_skill_weights, tokenize
from resumes.skills import canonical_skill, extract_skills

MAX_BULLETS_RECENT = 6
MAX_BULLETS_OLDER = 3
MAX_PROJECTS = 3


# ---------------------------------------------------------------- snapshot

def _iso(d) -> str:
    if not d:
        return ''
    return d.isoformat() if isinstance(d, date) else str(d)


def profile_snapshot(user) -> dict:
    """The candidate's facts in one dict (same shape the ATS exporter uses)."""
    profile = getattr(user, 'structured_profile', None)
    from resumes.models import Resume
    parsed = {}
    master = Resume.objects.filter(user=user, is_master=True).first()
    if master and master.parsed_json:
        parsed = master.parsed_json
    if profile is not None and (profile.experiences.exists() or profile.skills.exists() or profile.full_name):
        return {
            'full_name': profile.full_name or user.get_full_name() or '',
            'headline': profile.headline,
            'email': user.email,
            'phone': profile.phone,
            'location': profile.location,
            'links': [x for x in (profile.website, profile.linkedin, profile.github) if x],
            'summary': profile.summary,
            'skills': [{'name': s.name} for s in profile.skills.all()],
            'experiences': [{
                'title': e.title, 'company': e.company, 'location': e.location,
                'start': _iso(e.start_date), 'end': _iso(e.end_date),
                'is_current': e.is_current, 'bullets': list(e.bullets or []),
            } for e in profile.experiences.all()],
            'educations': [{
                'degree': ed.degree, 'field_of_study': ed.field_of_study, 'institution': ed.institution,
                'end': _iso(ed.end_date), 'gpa': ed.gpa,
            } for ed in profile.educations.all()],
            'projects': [{'name': p.name, 'description': p.description, 'tech_stack': p.tech_stack or []}
                         for p in profile.projects.all()],
        }
    # Résumé-only fallback.
    return {
        'full_name': parsed.get('full_name') or user.get_full_name() or '',
        'headline': parsed.get('headline', ''),
        'email': parsed.get('email') or user.email,
        'phone': parsed.get('phone', ''),
        'location': parsed.get('location', ''),
        'links': [x for x in (parsed.get('website'), parsed.get('linkedin'), parsed.get('github')) if x],
        'summary': parsed.get('summary', ''),
        'skills': [s if isinstance(s, dict) else {'name': str(s)} for s in parsed.get('skills') or []],
        'experiences': [{
            'title': e.get('title', ''), 'company': e.get('company', ''), 'location': e.get('location', ''),
            'start': e.get('start_date') or '', 'end': e.get('end_date') or '',
            'is_current': bool(e.get('is_current')), 'bullets': list(e.get('bullets') or []),
        } for e in parsed.get('experiences') or [] if isinstance(e, dict)],
        'educations': [{
            'degree': e.get('degree', ''), 'field_of_study': e.get('field_of_study', ''),
            'institution': e.get('institution', ''), 'end': e.get('end_date') or '', 'gpa': e.get('gpa', ''),
        } for e in parsed.get('educations') or [] if isinstance(e, dict)],
        'projects': [{'name': p.get('name', ''), 'description': p.get('description', ''),
                      'tech_stack': p.get('tech_stack') or []}
                     for p in parsed.get('projects') or [] if isinstance(p, dict)],
    }


def profile_skill_set(snapshot: dict) -> set[str]:
    names = {canonical_skill(s.get('name', '')).lower() for s in snapshot.get('skills') or []}
    blob = ' '.join(
        [snapshot.get('summary', ''), snapshot.get('headline', '')]
        + [' '.join(e.get('bullets') or []) + ' ' + e.get('title', '') for e in snapshot.get('experiences') or []]
        + [f"{p.get('name', '')} {p.get('description', '')} {' '.join(p.get('tech_stack') or [])}"
           for p in snapshot.get('projects') or []]
    )
    names |= {s.lower() for s in extract_skills(blob)}
    return {n for n in names if n}


def _years(snapshot: dict) -> float:
    starts = []
    for e in snapshot.get('experiences') or []:
        try:
            starts.append(date.fromisoformat(str(e.get('start'))[:10]))
        except ValueError:
            continue
    if not starts:
        return 0.0
    return round((date.today() - min(starts)).days / 365.25, 1)


# ---------------------------------------------------------------- relevance

def _relevance(text: str, jd_tokens: set[str], jd_skills: dict[str, int]) -> float:
    toks = set(tokenize(text))
    overlap = len(toks & jd_tokens)
    skill_hits = sum(jd_skills.get(s, 0) for s in extract_skills(text))
    has_number = 1 if re.search(r'\d', text) else 0
    return overlap + 2.5 * skill_hits + 0.5 * has_number


def _sentence(text: str) -> str:
    text = text.strip().rstrip('.;')
    return text[0].lower() + text[1:] if text and not text[:2].isupper() else text


# ---------------------------------------------------------------- tailoring

def tailor(snapshot: dict, *, job_title: str, company: str, description: str,
           jd_skills: dict | None = None) -> dict:
    jd_text = description_to_text(description)
    jd_skills = jd_skills or job_skill_weights(job_title, description)
    jd_tokens = set(tokenize(f'{job_title} {jd_text}'))
    have = profile_skill_set(snapshot)

    # skills: matched first (by JD weight), then the rest in original order
    original_skills = [canonical_skill(s.get('name', '')) for s in snapshot.get('skills') or [] if s.get('name')]
    original_skills = list(dict.fromkeys(original_skills))
    matched = sorted([s for s in original_skills if s in jd_skills], key=lambda s: -jd_skills[s])
    # skills evidenced in experience but missing from the skills list
    evidenced = [s for s in sorted(jd_skills, key=lambda s: -jd_skills[s])
                 if s.lower() in have and s not in original_skills]
    skills = matched + evidenced + [s for s in original_skills if s not in matched]
    missing = [s for s in sorted(jd_skills, key=lambda s: -jd_skills[s]) if s.lower() not in have]

    # experiences: keep identity untouched, re-rank bullets
    experiences = []
    reordered_roles = []
    dropped = 0
    best_bullet = ('', '', -1.0)  # (bullet, company, score)
    for idx, e in enumerate(snapshot.get('experiences') or []):
        bullets = [b for b in (e.get('bullets') or []) if b and b.strip()]
        scored = sorted(enumerate(bullets), key=lambda ib: (-_relevance(ib[1], jd_tokens, jd_skills), ib[0]))
        cap = MAX_BULLETS_RECENT if idx < 2 else MAX_BULLETS_OLDER
        kept = [b for _, b in scored[:cap]]
        dropped += max(0, len(bullets) - len(kept))
        if kept != bullets[:len(kept)]:
            reordered_roles.append(e.get('company') or e.get('title'))
        for b in kept[:1]:
            sc = _relevance(b, jd_tokens, jd_skills)
            if sc > best_bullet[2]:
                best_bullet = (b, e.get('company', ''), sc)
        experiences.append({**e, 'bullets': kept})

    projects = sorted(snapshot.get('projects') or [],
                      key=lambda p: -_relevance(f"{p.get('name', '')} {p.get('description', '')} "
                                                f"{' '.join(p.get('tech_stack') or [])}", jd_tokens, jd_skills))
    projects = projects[:MAX_PROJECTS]

    summary = compose_summary(snapshot, matched_skills=(matched + evidenced)[:4], best_bullet=best_bullet[0])

    content = {
        **{k: snapshot.get(k) for k in ('full_name', 'headline', 'email', 'phone', 'location', 'links')},
        'summary': summary,
        'skills': [{'name': s} for s in skills],
        'experiences': experiences,
        'educations': snapshot.get('educations') or [],
        'projects': projects,
    }
    total_w = sum(jd_skills.values()) or 1
    coverage = round(100 * sum(jd_skills[s] for s in jd_skills if s.lower() in have) / total_w) if jd_skills else None
    diff = {
        'changed_sections': [x for x, changed in (
            ('summary', summary != (snapshot.get('summary') or '')),
            ('skills', skills != original_skills),
            ('experience', bool(reordered_roles) or dropped > 0),
            ('projects', [p.get('name') for p in projects] != [p.get('name') for p in (snapshot.get('projects') or [])])
        ) if changed],
        'summary_before': snapshot.get('summary') or '',
        'skills_moved_up': matched + evidenced,
        'skills_added_from_experience': evidenced,
        'reordered_roles': reordered_roles,
        'bullets_trimmed': dropped,
    }
    suggestions = [
        f'The job asks for {s}. If you have used it, add a bullet that shows it; otherwise be ready to talk about how you would ramp up.'
        for s in missing[:4]
    ]
    return {
        'content': content,
        'diff_from_master': diff,
        'keyword_coverage': coverage,
        'matched_skills': matched + evidenced,
        'missing_skills': missing,
        'suggestions': suggestions,
    }


def compose_summary(snapshot: dict, *, matched_skills: list[str], best_bullet: str) -> str:
    headline = (snapshot.get('headline') or '').strip()
    exps = snapshot.get('experiences') or []
    years = _years(snapshot)
    parts = []
    role = headline or (exps[0].get('title') if exps else '')
    if role:
        lead = f'{role}'
        if years >= 1:
            lead += f' with {int(years)}+ years of experience'
        if exps and exps[0].get('company'):
            verb = 'currently at' if exps[0].get('is_current') else 'most recently at'
            lead += f', {verb} {exps[0]["company"]}'
        parts.append(lead + '.')
    if matched_skills:
        if len(matched_skills) > 1:
            listed = ', '.join(matched_skills[:-1]) + f' and {matched_skills[-1]}'
        else:
            listed = matched_skills[0]
        parts.append(f'Hands-on with {listed}.')
    if best_bullet:
        b = best_bullet.strip().rstrip('.')
        if len(b) > 180:
            b = b[:177].rsplit(' ', 1)[0] + '…'
        parts.append(f'Recent highlight: {_sentence(b)}.')
    out = ' '.join(parts)
    return out or (snapshot.get('summary') or '')


# ---------------------------------------------------------------- verification

_NUM_RE = re.compile(r'\d+(?:[.,]\d+)?')


def verify_rewrite(original: str, rewritten: str, *, allowed_skills: set[str],
                   allowed_numbers: set[str] | None = None, forbidden_names: set[str] | None = None) -> list[str]:
    """Return a list of problems; empty list == safe to use."""
    problems = []
    for s in extract_skills(rewritten):
        if s.lower() not in allowed_skills:
            problems.append(f'mentions {s}, which is not in your profile')
    nums = set(_NUM_RE.findall(rewritten))
    allowed = allowed_numbers if allowed_numbers is not None else set(_NUM_RE.findall(original))
    invented = sorted(n for n in nums if n not in allowed)
    if invented:
        problems.append('introduces numbers not in your profile: ' + ', '.join(invented))
    if not rewritten.strip():
        problems.append('empty')
    return problems


def llm_polish(result: dict, snapshot: dict, *, job_title: str, company: str,
               llm: Callable[[str], str] | None) -> dict:
    """Optionally let an LLM rewrite the summary + bullets; keep only verified edits."""
    if llm is None:
        return {**result, 'model_used': '', 'verification': []}
    content = result['content']
    allowed = profile_skill_set(snapshot)
    all_text = json.dumps(snapshot)
    allowed_numbers = set(_NUM_RE.findall(all_text))
    prompt = (
        'You are editing a résumé for one job. Rewrite ONLY wording. Never add skills, tools, employers, '
        'titles, numbers or achievements that are not already present. Return strict JSON: '
        '{"summary": "...", "experiences": [["bullet", ...], ...]} with the same number of experiences '
        'and bullets in the same order.\n'
        f'Job: {job_title} at {company}\n'
        f'Résumé JSON: {json.dumps({"summary": content["summary"], "experiences": [e["bullets"] for e in content["experiences"]]})}'
    )
    try:
        raw = llm(prompt) or ''
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        data = json.loads(m.group(0)) if m else None
    except Exception:  # noqa: BLE001
        data = None
    notes: list[str] = []
    if not isinstance(data, dict):
        return {**result, 'model_used': '', 'verification': ['AI rewrite unavailable; kept the factual version.']}
    used = False
    new_summary = data.get('summary')
    if isinstance(new_summary, str):
        problems = verify_rewrite(content['summary'], new_summary, allowed_skills=allowed,
                                  allowed_numbers=allowed_numbers)
        if problems:
            notes.append('Summary rewrite rejected: ' + '; '.join(problems))
        else:
            content['summary'] = new_summary.strip()
            used = True
    exps = data.get('experiences')
    if isinstance(exps, list) and len(exps) == len(content['experiences']):
        for e, new_bullets in zip(content['experiences'], exps):
            if not isinstance(new_bullets, list) or len(new_bullets) != len(e['bullets']):
                continue
            for i, (old, new) in enumerate(zip(e['bullets'], new_bullets)):
                if not isinstance(new, str):
                    continue
                problems = verify_rewrite(old, new, allowed_skills=allowed)
                if problems:
                    notes.append(f'Kept original bullet at {e.get("company")}: ' + '; '.join(problems))
                else:
                    e['bullets'][i] = new.strip()
                    used = True
    return {**result, 'content': content, 'model_used': 'llm' if used else '', 'verification': notes}


# ---------------------------------------------------------------- cover letter

_VERBISH = re.compile(r'^(?:build|design|develop|lead|own|drive|work|partner|create|ship|scale|improve|'
                      r'maintain|deliver|define|manage|collaborate|help|write|implement|architect|support|'
                      r'shape|grow|launch|run|operate|analy[sz]e|research|mentor)\b', re.IGNORECASE)


def _jd_responsibility(jd_text: str, candidate_tokens: set[str]) -> str:
    best, best_score = '', 0
    for line in jd_text.splitlines():
        line = line.strip('•-* ').strip()
        if not (20 <= len(line) <= 160) or not _VERBISH.match(line):
            continue
        score = len(set(tokenize(line)) & candidate_tokens)
        if score > best_score:
            best, best_score = line, score
    return best.rstrip('.')


def draft_cover_letter(snapshot: dict, tailored: dict, *, job_title: str, company: str,
                       description: str) -> str:
    name = snapshot.get('full_name') or ''
    exps = tailored['content']['experiences']
    matched = tailored.get('matched_skills') or []
    years = _years(snapshot)
    headline = snapshot.get('headline') or (exps[0]['title'] if exps else '')
    jd_text = description_to_text(description)

    paras = [f'Dear {company} hiring team,']
    intro = f'I am applying for the {job_title} role.'
    if headline:
        who = f' I am a {headline}'
        if years >= 1:
            who += f' with {int(years)}+ years of experience'
        if exps and exps[0].get('company'):
            who += f', {"currently" if exps[0].get("is_current") else "most recently"} at {exps[0]["company"]}'
        intro += who + '.'
    paras.append(intro)

    evidence = []
    if matched:
        listed = ', '.join(matched[:3])
        evidence.append(f'The role calls for {listed}, all of which I have used hands-on.')
    used = 0
    for e in exps[:3]:
        if e.get('bullets') and used < 2:
            b = e['bullets'][0].strip().rstrip('.')
            evidence.append(f'At {e.get("company") or "a previous role"}, I {_sentence(b)}.')
            used += 1
    if evidence:
        paras.append(' '.join(evidence))

    cand_tokens = set(tokenize(' '.join(' '.join(e.get('bullets') or []) for e in exps) + ' ' + ' '.join(matched)))
    resp = _jd_responsibility(jd_text, cand_tokens)
    missing = tailored.get('missing_skills') or []
    closing = []
    if resp:
        closing.append(f'I would be glad to bring that experience to work like “{resp}”.')
    if missing:
        closing.append(f'I have not worked with {missing[0]} in depth yet, and I am happy to talk through how I would get up to speed.')
    closing.append(f'Thank you for considering my application — I would welcome a conversation about the role at {company}.')
    paras.append(' '.join(closing))

    contact = ' · '.join(x for x in [snapshot.get('email'), snapshot.get('phone')] if x)
    paras.append('Best regards,\n' + (name or '') + (f'\n{contact}' if contact else ''))
    return '\n\n'.join(p for p in paras if p).strip()


def verify_cover_letter(text: str, snapshot: dict) -> list[str]:
    problems = []
    name = (snapshot.get('full_name') or '').strip()
    if name and name.split()[0].lower() not in text.lower():
        problems.append('does not contain your name')
    allowed = profile_skill_set(snapshot)
    for s in extract_skills(text):
        if s.lower() not in allowed:
            problems.append(f'claims {s}, which is not in your profile')
    return problems
