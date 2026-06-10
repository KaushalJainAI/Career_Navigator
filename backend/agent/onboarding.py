from __future__ import annotations

import re
from dataclasses import dataclass, field

from profiles.models import Skill, StructuredProfile


URL_RE = re.compile(r'https?://[^\s,]+', re.IGNORECASE)
PHONE_RE = re.compile(r'(?:(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{3,5}\)?[\s-]?)?\d{3,5}[\s-]?\d{4})')


@dataclass
class OnboardingExtraction:
    fields: dict[str, str | bool] = field(default_factory=dict)
    skills: list[str] = field(default_factory=list)


def extract_onboarding_facts(message: str) -> OnboardingExtraction:
    text = (message or '').strip()
    lowered = text.lower()
    out = OnboardingExtraction()

    name = _match_first(text, [
        r'\bmy name is\s+([A-Z][A-Za-z .-]{1,80})',
        r'\bi am\s+([A-Z][A-Za-z .-]{1,80})',
        r"\bi'm\s+([A-Z][A-Za-z .-]{1,80})",
    ])
    if name:
        out.fields['full_name'] = _clean_phrase(name)

    location = _match_first(text, [
        r'\b(?:based in|located in|live in|from)\s+([A-Za-z ,.-]{2,80})',
    ])
    if location:
        out.fields['location'] = _clean_phrase(location)

    headline = _match_first(text, [
        r'\b(?:work as|working as|role is|title is)\s+([A-Za-z0-9 +/#.,-]{2,100})',
        r'\b(?:backend engineer|frontend engineer|full stack engineer|data scientist|product manager|designer|developer)\b',
    ])
    if headline:
        out.fields['headline'] = _clean_phrase(headline)

    phone = PHONE_RE.search(text)
    if phone:
        out.fields['phone'] = phone.group(0).strip()

    for url in URL_RE.findall(text):
        value = url.rstrip('.,)')
        if 'linkedin.com' in value.lower():
            out.fields['linkedin'] = value
        elif 'github.com' in value.lower():
            out.fields['github'] = value
        else:
            out.fields.setdefault('website', value)

    skills = _extract_skills(text)
    if skills:
        out.skills = skills

    if any(word in lowered for word in ('done onboarding', 'profile complete', 'finish onboarding')):
        out.fields['onboarding_complete'] = True

    return out


def apply_onboarding_facts(user, message: str) -> dict:
    extraction = extract_onboarding_facts(message)
    profile, _ = StructuredProfile.objects.get_or_create(user=user)
    changed_fields = []
    for field_name, value in extraction.fields.items():
        if hasattr(profile, field_name) and getattr(profile, field_name) != value:
            setattr(profile, field_name, value)
            changed_fields.append(field_name)
    if changed_fields:
        profile.save(update_fields=[*changed_fields, 'updated_at'])

    skill_names = []
    for skill in extraction.skills:
        obj, _ = Skill.objects.get_or_create(profile=profile, name=skill)
        skill_names.append(obj.name)

    return {
        'updated_fields': changed_fields,
        'skills': skill_names,
        'profile': {
            'full_name': profile.full_name,
            'headline': profile.headline,
            'location': profile.location,
            'phone': profile.phone,
            'linkedin': profile.linkedin,
            'github': profile.github,
            'onboarding_complete': profile.onboarding_complete,
        },
    }


def onboarding_reply(result: dict) -> str:
    updates = [field.replace('_', ' ') for field in result.get('updated_fields', [])]
    skills = result.get('skills', [])
    parts = []
    if updates:
        parts.append('updated ' + ', '.join(updates))
    if skills:
        parts.append('added skills: ' + ', '.join(skills))
    if not parts:
        return 'I did not find a profile detail to save yet. Tell me your name, role, location, links, or skills.'
    return 'Saved: ' + '; '.join(parts) + '.'


def _match_first(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1) if match.groups() else match.group(0)
    return ''


def _clean_phrase(value: str) -> str:
    value = re.split(
        r'[.!?]|\b(?:and|with|my|skills?|phone|linkedin|github|work as|working as|role is|title is|live in|based in|located in|from)\b',
        value,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    return value.strip(' .,;-')


def _extract_skills(text: str) -> list[str]:
    match = re.search(r'\bskills?\s*(?:are|:|-)?\s*([A-Za-z0-9 +#.,/-]{2,160})', text, flags=re.IGNORECASE)
    if not match:
        return []
    raw = re.split(r'\b(?:and I|my phone|linkedin|github|located|based)\b', match.group(1), maxsplit=1, flags=re.IGNORECASE)[0]
    values = [item.strip(' .;') for item in re.split(r',|/|\band\b', raw) if item.strip(' .;')]
    seen = set()
    out = []
    for item in values:
        if len(item) > 40:
            continue
        key = item.lower()
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out[:12]
