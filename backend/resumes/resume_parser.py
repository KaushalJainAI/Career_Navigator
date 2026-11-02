"""Deterministic résumé → structured-profile parser.

No LLM required. Handles the common layouts people actually use:

    Jane Doe
    Senior Backend Engineer
    jane@x.com | +1 555 0100 | Berlin, Germany | linkedin.com/in/jane

    EXPERIENCE
    Senior Engineer — Acme Corp            Jan 2021 – Present
    • Built ...

    Acme Corp
    Software Engineer
    2018 - 2020
    - Shipped ...

The output shape matches what `profiles.services.apply_parsed_resume` and the
matching/tailoring layers consume.
"""

from __future__ import annotations

import re
from datetime import date

from .skills import canonical_skill, extract_skills

SECTION_ALIASES = {
    'summary': ['summary', 'professional summary', 'profile', 'about', 'about me', 'objective',
                'career objective', 'professional profile', 'overview'],
    'experience': ['experience', 'work experience', 'professional experience', 'employment',
                   'employment history', 'work history', 'career history', 'relevant experience',
                   'internships', 'internship experience'],
    'education': ['education', 'academic background', 'academics', 'education and training',
                  'qualifications', 'academic qualifications'],
    'skills': ['skills', 'technical skills', 'core skills', 'key skills', 'skills & tools',
               'skills and tools', 'tech stack', 'technologies', 'core competencies',
               'competencies', 'tools', 'skills summary', 'technical proficiencies'],
    'projects': ['projects', 'personal projects', 'selected projects', 'key projects',
                 'academic projects', 'side projects'],
    'other': ['certifications', 'certificates', 'awards', 'achievements', 'publications',
              'languages', 'interests', 'hobbies', 'volunteering', 'volunteer experience',
              'references', 'activities', 'leadership', 'honors', 'positions of responsibility',
              'extracurricular activities', 'extra-curricular activities', 'relevant coursework', 'coursework',
              'coding profiles', 'achievements & certifications', 'awards and achievements', 'hackathons'],
}
_HEADER_LOOKUP = {alias: key for key, aliases in SECTION_ALIASES.items() for alias in aliases}

MONTHS = {m: i for i, m in enumerate(
    ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'], start=1)}
_MONTH_RE = r'(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?'
_DATE_TOKEN = rf'(?:{_MONTH_RE}\s*,?\s*\d{{4}}|\d{{1,2}}[/.-]\d{{4}}|\d{{4}})'
_PRESENT = r'(?:present|current|now|today|ongoing|till date|to date)'
DATE_RANGE_RE = re.compile(
    rf'(?P<start>{_DATE_TOKEN})\s*(?:-|–|—|to|until|~)\s*(?P<end>{_DATE_TOKEN}|{_PRESENT})',
    re.IGNORECASE,
)
SINGLE_DATE_RE = re.compile(rf'(?P<start>{_MONTH_RE}\s*,?\s*\d{{4}})', re.IGNORECASE)

EMAIL_RE = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
PHONE_RE = re.compile(r'(?:\+?\d[\d\s().-]{7,}\d)')
URL_RE = re.compile(r'(?:https?://)?(?:www\.)?[\w-]+(?:\.[\w-]+)+(?:/[\w./%#?=&-]*)?', re.IGNORECASE)
BULLET_RE = re.compile(r'^\s*(?:[•●▪◦‣∙·*\-–—>»✓✔■□]|\d+[.)])\s+')

ROLE_WORDS = re.compile(
    r'\b(engineer|developer|programmer|manager|intern|analyst|designer|scientist|lead|consultant|'
    r'director|architect|specialist|associate|head|officer|founder|co-founder|researcher|'
    r'administrator|coordinator|executive|vp|president|strategist|marketer|writer|editor|'
    r'technician|sre|devops|owner|principal|staff|fellow|assistant|representative|recruiter|'
    r'accountant|advisor|teacher|instructor|tutor|freelance|freelancer|contractor|cto|ceo|coo|cfo)\b',
    re.IGNORECASE,
)
INSTITUTION_WORDS = re.compile(
    r'\b(university|college|institute|school|academy|polytechnic|iit|nit|iiit|bits|mit|'
    r'universit[äa]t|ecole|école|campus|bootcamp)\b', re.IGNORECASE)
DEGREE_RE = re.compile(
    r'\b(b\.?\s?s\.?c?|b\.?\s?a\.?|b\.?\s?tech|b\.?\s?e\.?|bachelor(?:\'s)?|m\.?\s?s\.?c?|m\.?\s?a\.?|'
    r'm\.?\s?tech|m\.?\s?e\.?|master(?:\'s)?|mba|ph\.?\s?d|doctorate|diploma|associate(?:\'s)? degree|'
    r'high school|hsc|ssc|b\.?com|m\.?com|bca|mca|bba|bfa|mfa|b\.?eng|m\.?eng|a\.?b\.?|llb|llm|md)\b', re.IGNORECASE)
SCHOOL_RE = re.compile(r'\b(class\s*(?:x|xii|10|12)(?:th)?|xii|xth|12th|10th|hsc|ssc|cbse|icse|isc|'
                       r'higher secondary|secondary school|intermediate|puc)\b', re.IGNORECASE)
GPA_RE = re.compile(r'\b(?:gpa|cgpa|cpi)\s*[:\-]?\s*(\d+(?:\.\d+)?(?:\s*/\s*\d+(?:\.\d+)?)?)', re.IGNORECASE)
LOCATION_RE = re.compile(
    r'\b([A-Z][a-zA-Z.\- ]{1,30},\s*(?:[A-Z]{2}\b|[A-Z][a-zA-Z ]{2,30}))')
SEPARATORS = re.compile(r'\s+(?:—|–|-|\||@|at|·|•)\s+|\s*\|\s*|\s{3,}|\t+|,\s+(?=[A-Z])')


def _clean(line: str) -> str:
    return re.sub(r'\s+', ' ', line.replace(' ', ' ')).strip()


def _header_key(line: str) -> str | None:
    text = re.sub(r'[:\-–—_=#*|]+$', '', line.strip()).strip().lower()
    text = re.sub(r'^[#*\s]+', '', text)
    if not text or len(text) > 40:
        return None
    return _HEADER_LOOKUP.get(text)


def _parse_date(token: str) -> tuple[str | None, bool]:
    """Returns (iso date or None, is_present)."""
    t = token.strip().lower().rstrip('.')
    if re.fullmatch(_PRESENT, t):
        return None, True
    m = re.match(r'([a-z]+)\.?\s*,?\s*(\d{4})', t)
    if m and m.group(1)[:3] in MONTHS:
        return date(int(m.group(2)), MONTHS[m.group(1)[:3]], 1).isoformat(), False
    m = re.match(r'(\d{1,2})[/.-](\d{4})', t)
    if m and 1 <= int(m.group(1)) <= 12:
        return date(int(m.group(2)), int(m.group(1)), 1).isoformat(), False
    m = re.match(r'(\d{4})', t)
    if m and 1950 <= int(m.group(1)) <= 2100:
        return date(int(m.group(1)), 1, 1).isoformat(), False
    return None, False


def split_sections(lines: list[str]) -> tuple[list[str], dict[str, list[str]]]:
    """Split résumé lines into (header block, {section: lines})."""
    head: list[str] = []
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines:
        key = _header_key(line)
        if key:
            current = key
            sections.setdefault(key, [])
            continue
        if current is None:
            head.append(line)
        else:
            sections[current].append(line)
    return head, sections


def _extract_contact(text: str, head: list[str]) -> dict:
    out: dict = {'email': '', 'phone': '', 'linkedin': '', 'github': '', 'website': '', 'location': ''}
    m = EMAIL_RE.search(text)
    if m:
        out['email'] = m.group(0)
    for line in head[:8] or text.splitlines()[:8]:
        if out['phone']:
            break
        for cand in PHONE_RE.findall(line):
            digits = re.sub(r'\D', '', cand)
            if 8 <= len(digits) <= 15 and not DATE_RANGE_RE.search(cand):
                out['phone'] = cand.strip()
                break
    for m in URL_RE.finditer(text):
        url = m.group(0).rstrip('.,;)')
        low = url.lower()
        if '@' in text[max(0, m.start() - 1):m.end() + 1] or EMAIL_RE.fullmatch(url):
            continue
        full = url if low.startswith('http') else f'https://{url}'
        if 'linkedin.com' in low and not out['linkedin']:
            out['linkedin'] = full
        elif 'github.com' in low and not out['github']:
            out['github'] = full
        elif not out['website'] and m.start() < 600 and len(low) > 5 \
                and len(low.split('/')[0].split('.')[-2] if '.' in low.split('/')[0] else '') > 2 \
                and not DEGREE_RE.fullmatch(url) \
                and re.search(r'\.[a-z]{2,10}(?:/|$)', low) \
                and not any(x in low for x in ('linkedin', 'github', 'gmail', 'outlook', 'yahoo', 'hotmail')) \
                and not re.fullmatch(r'[\d.]+', low):
            out['website'] = full
    for line in head[:8]:
        if EMAIL_RE.search(line) or 'http' in line.lower():
            parts = re.split(r'\s*[|•·]\s*', line)
        else:
            parts = [line]
        for part in parts:
            part = part.strip()
            if re.search(r'\bremote\b', part, re.IGNORECASE) and len(part) < 30:
                out['location'] = out['location'] or 'Remote'
            lm = LOCATION_RE.search(part)
            if lm and not EMAIL_RE.search(part) and not ROLE_WORDS.search(part) and len(part) < 60:
                out['location'] = lm.group(1).strip()
                break
        if out['location'] and out['location'] != 'Remote':
            break
    return out


def _looks_like_name(line: str) -> bool:
    if EMAIL_RE.search(line) or re.search(r'\d', line) or 'http' in line.lower():
        return False
    words = line.replace('.', ' ').split()
    if not 2 <= len(words) <= 5:
        return False
    if ROLE_WORDS.search(line) or _header_key(line):
        return False
    return all(w[0].isupper() for w in words if w[0].isalpha())


def _identity(head: list[str], all_lines: list[str]) -> tuple[str, str]:
    pool = head[:6] if head else all_lines[:6]
    name = ''
    headline = ''
    for i, line in enumerate(pool):
        if _looks_like_name(line):
            name = line.title() if line.isupper() else line
            for nxt in pool[i + 1:i + 3]:
                if not EMAIL_RE.search(nxt) and not PHONE_RE.search(nxt) and 'http' not in nxt \
                        and len(nxt.split()) <= 14 and not LOCATION_RE.fullmatch(nxt):
                    if '|' in nxt and not ROLE_WORDS.search(nxt):
                        continue
                    headline = nxt
                    break
            break
    return name, headline


def _split_header_parts(text: str) -> list[str]:
    parts = [p.strip(' ,;()') for p in SEPARATORS.split(text) if p and p.strip(' ,;()')]
    return [p for p in parts if p and not re.fullmatch(r'[\W_]+', p)]


def _assign_title_company(parts: list[str]) -> tuple[str, str, str]:
    title = company = location = ''
    rest = []
    for p in parts:
        if not location and (re.fullmatch(r'(?:remote|hybrid|on-?site)', p, re.IGNORECASE)
                             or (LOCATION_RE.fullmatch(p) and not ROLE_WORDS.search(p))):
            location = p
        elif not title and ROLE_WORDS.search(p):
            title = p
        else:
            rest.append(p)
    if rest:
        company = rest[0]
    if not title and len(rest) > 1:
        title = rest[1]
    return title, company, location


def _is_bullet(line: str) -> bool:
    return bool(BULLET_RE.match(line))


def _strip_bullet(line: str) -> str:
    return BULLET_RE.sub('', line).strip()


def parse_experience(lines: list[str]) -> list[dict]:
    entries: list[dict] = []
    pending: list[str] = []
    current: dict | None = None

    def start_entry(header_lines: list[str], date_line: str | None):
        nonlocal current
        dates = {'start_date': None, 'end_date': None, 'is_current': False}
        texts = list(header_lines)
        loc_hint = ''
        if date_line is not None:
            m = DATE_RANGE_RE.search(date_line)
            if m:
                dates['start_date'], _ = _parse_date(m.group('start'))
                dates['end_date'], present = _parse_date(m.group('end'))
                dates['is_current'] = present
                remainder = re.sub(r'\(\s*\)', '', (date_line[:m.start()] + ' ' + date_line[m.end():])).strip(' ,|-–—')
            else:
                remainder = date_line
            paren = re.search(r'\(([^)]{2,40})\)', remainder)
            if paren:
                loc_hint = paren.group(1).strip()
                remainder = (remainder[:paren.start()] + remainder[paren.end():]).strip(' ,|-–—')
            own_parts = _split_header_parts(remainder) if remainder else []
            if len(own_parts) >= 2:
                # The date line carries title + company itself; anything pending
                # belonged to the previous entry.
                if current is not None:
                    current['bullets'].extend(texts)
                texts = []
            elif texts and len(own_parts) == 1:
                if current is not None and len(texts) > 1:
                    current['bullets'].extend(texts[:-1])
                texts = texts[-1:]
            if remainder:
                texts.append(remainder)
        parts: list[str] = []
        for t in texts:
            paren = re.search(r'\(([^)]{2,40})\)', t)
            if paren and not loc_hint:
                loc_hint = paren.group(1).strip()
                t = (t[:paren.start()] + t[paren.end():]).strip()
            parts.extend(_split_header_parts(t))
        title, company, location = _assign_title_company(parts)
        location = location or loc_hint
        current = {
            'title': title[:255], 'company': company[:255], 'location': location[:255],
            'bullets': [], **dates,
        }
        entries.append(current)

    for raw in lines:
        line = _clean(raw)
        if not line:
            continue
        if DATE_RANGE_RE.search(line) and not _is_bullet(line) and len(line.split()) <= 18:
            start_entry(pending[-2:], line)
            pending = []
            continue
        if _is_bullet(line):
            if pending and current is None:
                start_entry(pending[-2:], None)
                pending = []
            elif len(pending) >= 2 and current is not None:
                start_entry(pending[-2:], None)
                pending = []
            elif pending and current is not None:
                current['bullets'].extend(pending)
                pending = []
            if current is not None:
                current['bullets'].append(_strip_bullet(line))
            continue
        # Non-bullet, no date: either a wrapped bullet, a sentence-style
        # bullet, or the start of the next entry's header.
        prev = current['bullets'][-1] if current is not None and current['bullets'] else ''
        if prev and not pending and (line[0].islower() or line[0].isdigit() or line[0] in ',;&(%'
                                     or re.search(r'(?:,|\b(?:and|or|to|from|of|the|with|for|in|by))$', prev)):
            current['bullets'][-1] = f"{prev} {line}"
        elif current is not None and (len(line.split()) > 12 or (line.endswith('.') and len(line.split()) > 5)):
            current['bullets'].append(line)
        else:
            pending.append(line)
    if pending and current is not None:
        if len(pending) >= 2 and any(ROLE_WORDS.search(p) for p in pending):
            start_entry(pending[-2:], None)
        else:
            current['bullets'].extend(pending)
    return [e for e in entries if e['title'] or e['company']]


def parse_education(lines: list[str]) -> list[dict]:
    entries: list[dict] = []
    current: dict | None = None
    for raw in lines:
        line = _strip_bullet(_clean(raw))
        if not line:
            continue
        is_inst = bool(INSTITUTION_WORDS.search(line))
        degree_m = DEGREE_RE.search(line)
        if is_inst and (current is None or current.get('institution')):
            current = {'institution': '', 'degree': '', 'field_of_study': '',
                       'start_date': None, 'end_date': None, 'gpa': ''}
            entries.append(current)
        elif current is None and degree_m:
            current = {'institution': '', 'degree': '', 'field_of_study': '',
                       'start_date': None, 'end_date': None, 'gpa': ''}
            entries.append(current)
        if current is None:
            continue
        rng = DATE_RANGE_RE.search(line)
        if rng:
            current['start_date'], _ = _parse_date(rng.group('start'))
            current['end_date'], _ = _parse_date(rng.group('end'))
        else:
            years = re.findall(r'\b(19[5-9]\d|20\d\d)\b', line)
            if years:
                current['end_date'] = date(int(years[-1]), 1, 1).isoformat()
        gpa = GPA_RE.search(line)
        if gpa:
            current['gpa'] = gpa.group(1).replace(' ', '')[:16]
        text = DATE_RANGE_RE.sub('', line)
        text = GPA_RE.sub('', text)
        text = re.sub(r'\b(19[5-9]\d|20\d\d)\b', '', text).strip(' ,|()-–—')
        if is_inst and not degree_m and not current['institution']:
            parts = _split_header_parts(re.sub(r'\s*[—–]\s*', ' | ', line)) or [text]
            inst = next((p for p in parts if INSTITUTION_WORDS.search(p)), parts[0])
            current['institution'] = re.sub(r'\b(19[5-9]\d|20\d\d)\b', '', inst).strip(' ,|()-–—')[:255]
            for p in parts:
                if p == inst:
                    continue
                if SCHOOL_RE.search(p) and not current['degree']:
                    current['degree'] = re.sub(r'\b(19[5-9]\d|20\d\d)\b|\d+(?:\.\d+)?\s*%', '', p).strip(' ,|()-–—')[:255]
                pct = re.search(r'(\d{2,3}(?:\.\d+)?)\s*%', p)
                if pct and not current['gpa']:
                    current['gpa'] = f'{pct.group(1)}%'
            continue
        for part in _split_header_parts(text) or [text]:
            if INSTITUTION_WORDS.search(part) and not current['institution']:
                current['institution'] = part[:255]
            elif DEGREE_RE.search(part) and not current['degree']:
                m = re.split(r'\s+(?:in|of)\s+', part, maxsplit=1)
                current['degree'] = m[0][:255]
                if len(m) > 1:
                    current['field_of_study'] = m[1][:255]
            elif current['degree'] and not current['field_of_study'] and len(part.split()) <= 6 \
                    and not INSTITUTION_WORDS.search(part):
                current['field_of_study'] = part[:255]
    for e in entries:
        if not e['institution'] and e['degree']:
            e['institution'] = 'Unknown institution'
    return [e for e in entries if e['institution']]


def parse_projects(lines: list[str]) -> list[dict]:
    projects: list[dict] = []
    current: dict | None = None
    for raw in lines:
        line = _clean(raw)
        if not line:
            continue
        has_sep = bool(re.search(r'\s+[|–—-]\s+|:\s+', line))
        if not _is_bullet(line) and (has_sep or len(line.split()) <= 10) and (current is None or current['description'] or has_sep):
            name_part = re.split(r'\s+[|–—-]\s+|:\s+', line, maxsplit=1)
            current = {'name': name_part[0][:255], 'description': name_part[1] if len(name_part) > 1 else '',
                       'url': '', 'tech_stack': []}
            projects.append(current)
            continue
        if current is None:
            current = {'name': _strip_bullet(line)[:80], 'description': '', 'url': '', 'tech_stack': []}
            projects.append(current)
            continue
        text = _strip_bullet(line)
        current['description'] = f"{current['description']} {text}".strip()
    for p in projects:
        blob = f"{p['name']} {p['description']}"
        p['tech_stack'] = extract_skills(blob)
        url = URL_RE.search(blob)
        if url and ('github' in url.group(0) or 'http' in url.group(0)):
            u = url.group(0)
            p['url'] = u if u.startswith('http') else f'https://{u}'
    return projects[:12]


def parse_skills_section(lines: list[str]) -> list[str]:
    found: list[str] = []
    for raw in lines:
        line = _strip_bullet(_clean(raw))
        if ':' in line:  # "Languages: Python, Go"
            line = line.split(':', 1)[1]
        for item in re.split(r'[,;|•·/]|\s{2,}|\band\b', line):
            item = item.strip(' .()[]')
            if 1 <= len(item) <= 40 and len(item.split()) <= 4 and not re.fullmatch(r'[\d\W]+', item):
                found.append(canonical_skill(item))
    return found


def parse_resume(text: str) -> dict:
    text = (text or '').replace('\r', '')
    lines = [_clean(ln) for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    head, sections = split_sections(lines)

    name, headline = _identity(head, lines)
    contact = _extract_contact(text, head)

    summary_lines = sections.get('summary', [])
    summary = ' '.join(_strip_bullet(x) for x in summary_lines)[:1500]

    experiences = parse_experience(sections.get('experience', []))
    educations = parse_education(sections.get('education', []))
    projects = parse_projects(sections.get('projects', []))

    skills: list[str] = []
    seen: set[str] = set()
    for s in parse_skills_section(sections.get('skills', [])) + extract_skills(text):
        key = s.lower()
        if key not in seen:
            seen.add(key)
            skills.append(s)

    if not headline and experiences:
        headline = experiences[0]['title']
    if not summary:
        # Old behaviour: first few lines; keeps something useful for matching.
        summary = ''
    return {
        'raw_text': text,
        'full_name': name,
        'headline': headline,
        'summary': summary,
        **contact,
        'skills': [{'name': s} for s in skills[:60]],
        'experiences': experiences,
        'educations': educations,
        'projects': projects,
    }
