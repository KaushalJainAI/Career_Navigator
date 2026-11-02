"""Profile ↔ job fit scoring (v2).

Deterministic, explainable, no embeddings (see docs/drop-faiss-and-add-google-auth.md).
Signals:
  - skills     : weighted coverage of the skills the JD asks for
  - title      : how close the job title is to the roles you target / have held,
                 plus a seniority-mismatch check
  - text       : TF-IDF cosine between your profile text and the JD
  - location   : remote / location preference fit
Every signal contributes a human-readable reason so the UI can show *why*.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date

from jobs.text import description_to_text
from resumes.skills import canonical_skill, extract_skills, skill_counts

MODEL_VERSION = 'fit-v2'

STOPWORDS = set('''a an the and or of to in for on with at by from as is are be been being this that these those
we you your our their they it its will would can could should may might must about into over under across
within without per via etc including include includes such other than more most very also not no any all each
who what when where why how which while if then so do does did done have has had having role team teams work
working job jobs company us ability strong experience experienced years year plus new using use used help join
looking candidate candidates position opportunity responsibilities requirements required preferred qualifications
skills skill knowledge understanding familiarity excellent great good based well across like within
'''.split())

TITLE_SYNONYMS = {
    'sr': 'senior', 'snr': 'senior', 'jr': 'junior', 'eng': 'engineer', 'engineering': 'engineer',
    'engr': 'engineer', 'dev': 'developer', 'developers': 'developer', 'engineers': 'engineer',
    'mgr': 'manager', 'mgmt': 'management', 'swe': 'software engineer', 'sde': 'software engineer',
    'pm': 'product manager', 'ml': 'machine learning', 'ai': 'ai', 'ui': 'ui', 'ux': 'ux',
    'fullstack': 'full stack', 'full-stack': 'full stack', 'front-end': 'frontend', 'front': 'frontend',
    'back-end': 'backend', 'back': 'backend', 'programmer': 'developer', 'devops': 'devops',
    'sre': 'site reliability engineer', 'qa': 'quality assurance', 'vp': 'vice president',
}
# Words that are interchangeable for "what job is this".
TITLE_FAMILY = {'developer': 'engineer', 'programmer': 'engineer', 'swe': 'engineer'}
SENIORITY = {
    'intern': 0, 'internship': 0, 'trainee': 0, 'graduate': 1, 'junior': 1, 'associate': 1, 'entry': 1,
    'mid': 2, 'ii': 2, 'senior': 3, 'iii': 3, 'staff': 4, 'lead': 4, 'principal': 5, 'distinguished': 6,
    'head': 6, 'director': 6, 'vice': 7, 'president': 7, 'chief': 8,
}
TITLE_NOISE = set(SENIORITY) | {'i', 'iv', 'remote', 'hybrid', 'contract', 'temporary', 'part', 'time', 'full',
                                 'f', 'm', 'w', 'd', 'x', 'h', 'all', 'genders', 'new', 'grad'}


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r'[a-z][a-z0-9+#.]*[a-z0-9+#]|[a-z]', (text or '').lower())
            if len(t) > 1 and t not in STOPWORDS]


def _title_tokens(title: str) -> list[str]:
    raw = re.findall(r'[a-z0-9+#]+(?:-[a-z]+)?', (title or '').lower())
    out: list[str] = []
    for t in raw:
        mapped = TITLE_SYNONYMS.get(t, t)
        out.extend(mapped.split())
    return out


def _core(tokens: list[str]) -> set[str]:
    return {TITLE_FAMILY.get(t, t) for t in tokens if t not in TITLE_NOISE and t not in STOPWORDS}


def seniority_level(title: str) -> int | None:
    levels = [SENIORITY[t] for t in _title_tokens(title) if t in SENIORITY]
    if not levels:
        return None
    # "Head of", "Director", "VP" dominate; otherwise the highest marker.
    return max(levels)


def level_for_years(years: float) -> int:
    if years < 1:
        return 1
    if years < 3:
        return 2
    if years < 6:
        return 3
    if years < 10:
        return 4
    return 5


def job_skill_weights(title: str, description: str) -> dict[str, int]:
    text = description_to_text(description)
    weights = skill_counts(text)
    for s in extract_skills(title or ''):
        weights[s] = weights.get(s, 0) + 3
    return weights


# ---------------------------------------------------------------- candidate

@dataclass
class Candidate:
    skills: dict[str, str] = field(default_factory=dict)  # lower -> display
    evidence: dict[str, int] = field(default_factory=dict)  # lower -> mentions in experience
    titles: list[str] = field(default_factory=list)
    text: str = ''
    years: float = 0.0
    locations: list[str] = field(default_factory=list)
    remote_ok: bool = True
    exclude_companies: list[str] = field(default_factory=list)
    has_data: bool = False


def _years_from_ranges(ranges: list[tuple[date | None, date | None, bool]]) -> float:
    spans = []
    today = date.today()
    for start, end, current in ranges:
        if not start:
            continue
        stop = today if (current or not end) else end
        if stop > start:
            spans.append((start, stop))
    spans.sort()
    total = 0
    cur_s = cur_e = None
    for s, e in spans:
        if cur_e is None or s > cur_e:
            if cur_e is not None:
                total += (cur_e - cur_s).days
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    if cur_e is not None:
        total += (cur_e - cur_s).days
    return round(total / 365.25, 1)


def candidate_from_profile(profile) -> Candidate:
    c = Candidate()
    if profile is None:
        return c
    pref = getattr(profile, 'preference', None) if hasattr(profile, 'preference') else None
    try:
        pref = profile.preference
    except Exception:  # noqa: BLE001 - RelatedObjectDoesNotExist
        pref = None
    for s in profile.skills.all():
        name = canonical_skill(s.name)
        c.skills[name.lower()] = name
    parts = [profile.headline, profile.summary]
    ranges = []
    for e in profile.experiences.all():
        c.titles.append(e.title)
        parts.extend([e.title, e.company, ' '.join(e.bullets or [])])
        for s in extract_skills(f"{e.title} {' '.join(e.bullets or [])}"):
            c.evidence[s.lower()] = c.evidence.get(s.lower(), 0) + 1
            c.skills.setdefault(s.lower(), s)
        ranges.append((e.start_date, e.end_date, e.is_current))
    for p in profile.projects.all():
        parts.extend([p.name, p.description, ' '.join(p.tech_stack or [])])
        for s in (p.tech_stack or []) + extract_skills(p.description or ''):
            name = canonical_skill(s)
            c.skills.setdefault(name.lower(), name)
    for s in extract_skills(f'{profile.headline} {profile.summary}'):
        c.skills.setdefault(s.lower(), s)
    parts.extend(c.skills.values())
    c.years = _years_from_ranges(ranges)
    targets = list(pref.target_titles or []) if pref else []
    c.titles = [t for t in targets + [profile.headline] + c.titles if t]
    c.text = ' '.join(p for p in parts if p)
    if pref:
        c.locations = [loc for loc in (pref.locations or []) if loc]
        c.remote_ok = bool(pref.remote)
        c.exclude_companies = [x.lower() for x in (pref.exclude_companies or []) if x]
    if not c.locations and profile.location and profile.location.lower() != 'remote':
        c.locations = [profile.location]
    c.has_data = bool(c.skills or c.titles or c.text.strip())
    return c


def candidate_from_parsed(parsed: dict) -> Candidate:
    """Fallback when the user has a parsed résumé but no structured profile."""
    c = Candidate()
    for s in parsed.get('skills') or []:
        name = canonical_skill(s.get('name') if isinstance(s, dict) else str(s))
        if name:
            c.skills[name.lower()] = name
    for e in parsed.get('experiences') or []:
        if isinstance(e, dict) and e.get('title'):
            c.titles.append(e['title'])
    if parsed.get('headline'):
        c.titles.insert(0, parsed['headline'])
    c.text = parsed.get('raw_text') or ' '.join([parsed.get('summary', '')] + list(c.skills.values()))
    if parsed.get('location'):
        c.locations = [parsed['location']]
    c.has_data = bool(c.skills or c.text.strip())
    return c


# ---------------------------------------------------------------- corpus

class Corpus:
    """Document frequencies for TF-IDF over the jobs being ranked."""

    def __init__(self, docs: list[list[str]]):
        self.n = max(1, len(docs))
        self.df: Counter = Counter()
        for toks in docs:
            self.df.update(set(toks))

    def idf(self, token: str) -> float:
        return math.log((self.n + 1) / (self.df.get(token, 0) + 1)) + 1.0

    def vector(self, tokens: list[str]) -> dict[str, float]:
        tf = Counter(tokens)
        vec = {t: (1 + math.log(n)) * self.idf(t) for t, n in tf.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {t: v / norm for t, v in vec.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(t, 0.0) for t, v in a.items())


YEARS_RE = re.compile(r'(\d{1,2})\s*\+?\s*(?:-|–|to)?\s*(?:\d{1,2}\s*)?\+?\s*years?', re.IGNORECASE)


def required_years(text: str) -> int | None:
    best = None
    for m in YEARS_RE.finditer(text or ''):
        window = text[m.end():m.end() + 60].lower()
        if 'experience' in window or 'exp' in window[:15] or 'professional' in window or 'industry' in window:
            n = int(m.group(1))
            if 0 < n <= 20:
                best = n if best is None else min(best, n)
    return best


# ---------------------------------------------------------------- scoring

def _verdict(fit: int) -> str:
    if fit >= 70:
        return 'strong'
    if fit >= 50:
        return 'good'
    if fit >= 35:
        return 'stretch'
    return 'weak'


def _location_fit(c: Candidate, job_location: str, job_remote: bool) -> tuple[float, dict | None]:
    loc = (job_location or '').lower()
    if job_remote and c.remote_ok:
        return 1.0, {'kind': 'positive', 'title': 'Remote role', 'detail': 'You are open to remote work.'}
    for pref in c.locations:
        city = pref.split(',')[0].strip().lower()
        if city and city in loc:
            return 1.0, {'kind': 'positive', 'title': f'In {pref.split(",")[0]}',
                         'detail': 'Matches your preferred location.'}
    if not c.locations and c.remote_ok:
        return 0.6, None
    if job_remote and not c.remote_ok:
        return 0.5, {'kind': 'neutral', 'title': 'Remote role', 'detail': 'You said you prefer on-site work.'}
    if not loc:
        return 0.6, None
    return 0.2, {'kind': 'negative', 'title': f'Location: {job_location}',
                 'detail': 'Not one of your preferred locations' + (' and not remote.' if not job_remote else '.')}


def score_fit(c: Candidate, *, title: str, description: str, location: str = '', remote: bool = False,
              skills: dict | None = None, corpus: Corpus | None = None,
              job_tokens: list[str] | None = None) -> dict:
    text = description_to_text(description)
    weights = skills if skills else job_skill_weights(title, description)
    reasons: list[dict] = []

    # --- skills
    total_w = sum(weights.values())
    matched = [s for s in weights if s.lower() in c.skills]
    missing = sorted((s for s in weights if s.lower() not in c.skills), key=lambda s: -weights[s])
    skill_score = (sum(weights[s] for s in matched) / total_w) if total_w else None
    if skill_score is not None:
        matched_sorted = sorted(matched, key=lambda s: -weights[s])
        reasons.append({
            'kind': 'positive' if skill_score >= 0.6 else ('neutral' if skill_score >= 0.35 else 'negative'),
            'title': f'You have {len(matched)} of {len(weights)} skills it asks for',
            'detail': ', '.join(matched_sorted[:8]) if matched_sorted else 'None of the listed skills appear in your profile.',
        })
        if missing:
            key_missing = missing[:5]
            reasons.append({
                'kind': 'negative' if (weights[missing[0]] >= 2 or skill_score < 0.75) else 'neutral',
                'title': 'Gaps: ' + ', '.join(key_missing),
                'detail': 'Not in your profile. If you have them, add them; otherwise address them honestly.',
            })

    # --- title + seniority
    job_core = _core(_title_tokens(title))
    title_score = 0.0
    best_title = ''
    for t in c.titles[:8]:
        cand_core = _core(_title_tokens(t))
        if not job_core or not cand_core:
            continue
        overlap = len(job_core & cand_core) / len(job_core | cand_core)
        # Matching the head noun ("engineer", "designer") counts for a lot.
        head = _title_tokens(title)[-1:] if _title_tokens(title) else []
        if head and TITLE_FAMILY.get(head[0], head[0]) in cand_core:
            overlap = max(overlap, 0.4) + 0.15
        overlap = min(1.0, overlap)
        if overlap > title_score:
            title_score, best_title = overlap, t
    if c.titles:
        if title_score >= 0.6:
            reasons.append({'kind': 'positive', 'title': 'Title fits your target',
                            'detail': f'Close to "{best_title}".'})
        elif title_score < 0.3:
            reasons.append({'kind': 'negative', 'title': 'Different kind of role',
                            'detail': 'The title is far from the roles you target or have held.'})
    job_level = seniority_level(title)
    seniority_penalty = 0.0
    if job_level is not None and c.years:
        cand_level = level_for_years(c.years)
        diff = job_level - cand_level
        if diff >= 2:
            seniority_penalty = 0.12
            reasons.append({'kind': 'negative', 'title': 'Likely above your level',
                            'detail': f'Title suggests more seniority than your ~{c.years:g} years.'})
        elif diff <= -2 and job_level <= 1:
            seniority_penalty = 0.08
            reasons.append({'kind': 'neutral', 'title': 'Likely below your level',
                            'detail': f'Looks junior for ~{c.years:g} years of experience.'})
    req = required_years(text)
    if req is not None and c.years:
        if c.years + 1 < req:
            seniority_penalty += 0.08
            reasons.append({'kind': 'negative', 'title': f'Asks for {req}+ years',
                            'detail': f'Your profile shows ~{c.years:g} years.'})
        else:
            reasons.append({'kind': 'positive', 'title': f'Asks for {req}+ years',
                            'detail': f'You have ~{c.years:g} years.'})

    # --- text similarity
    jt = job_tokens if job_tokens is not None else tokenize(f'{title} {text}')
    corpus = corpus or Corpus([jt])
    cos = _cosine(corpus.vector(tokenize(c.text)), corpus.vector(jt)) if c.text else 0.0
    text_score = min(1.0, cos / 0.3)

    # --- location
    loc_score, loc_reason = _location_fit(c, location, remote)
    if loc_reason:
        reasons.append(loc_reason)

    if skill_score is None:
        w = {'title': 0.4, 'text': 0.4, 'location': 0.2}
        raw = w['title'] * title_score + w['text'] * text_score + w['location'] * loc_score
        reasons.insert(0, {'kind': 'neutral', 'title': 'No specific skills listed',
                           'detail': 'Scored on title, wording and location only.'})
    else:
        w = {'skills': 0.45, 'title': 0.25, 'text': 0.15, 'location': 0.15}
        raw = (w['skills'] * skill_score + w['title'] * title_score
               + w['text'] * text_score + w['location'] * loc_score)
    fit = max(0, min(100, round((raw - seniority_penalty) * 100)))
    return {
        'fit': fit,
        'score': round(fit / 100, 4),
        'verdict': _verdict(fit),
        'matched_skills': sorted(matched, key=lambda s: -weights[s]),
        'missing_skills': missing,
        'gaps': missing,
        'breakdown': {
            'skills': None if skill_score is None else round(skill_score, 3),
            'title': round(title_score, 3),
            'text': round(text_score, 3),
            'location': round(loc_score, 3),
            'seniority_penalty': round(seniority_penalty, 3),
        },
        'explanation': reasons,
        'model_version': MODEL_VERSION,
    }
