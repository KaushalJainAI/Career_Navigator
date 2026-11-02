"""Apply a parsed résumé to the user's StructuredProfile.

Rules (the candidate stays in control):
- scalar fields are only filled when empty, unless `overwrite=True`;
- skills are merged (never removed);
- experiences / educations / projects are only imported when the profile has
  none yet, or on `overwrite=True` (an explicit "replace from résumé").
"""

from __future__ import annotations

from datetime import date

from django.db import transaction

from .models import Education, Experience, Preference, Project, Skill, StructuredProfile

SCALARS = ['full_name', 'headline', 'summary', 'location', 'phone', 'website', 'linkedin', 'github']


def _d(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


@transaction.atomic
def apply_parsed_resume(profile: StructuredProfile, parsed: dict, *, overwrite: bool = False) -> dict:
    changed: list[str] = []
    for field in SCALARS:
        value = (parsed.get(field) or '').strip() if isinstance(parsed.get(field), str) else ''
        if not value:
            continue
        max_len = profile._meta.get_field(field).max_length
        if max_len:
            value = value[:max_len]
        if overwrite or not getattr(profile, field):
            if getattr(profile, field) != value:
                setattr(profile, field, value)
                changed.append(field)
    profile.save()

    existing = {s.name.lower() for s in profile.skills.all()}
    added_skills = []
    for item in parsed.get('skills') or []:
        name = (item.get('name') if isinstance(item, dict) else str(item)).strip()[:128]
        if name and name.lower() not in existing:
            Skill.objects.create(profile=profile, name=name)
            existing.add(name.lower())
            added_skills.append(name)
    if added_skills:
        changed.append('skills')

    if parsed.get('experiences') and (overwrite or not profile.experiences.exists()):
        profile.experiences.all().delete()
        for e in parsed['experiences']:
            Experience.objects.create(
                profile=profile, company=(e.get('company') or 'Unknown')[:255],
                title=(e.get('title') or '')[:255], location=(e.get('location') or '')[:255],
                start_date=_d(e.get('start_date')), end_date=_d(e.get('end_date')),
                is_current=bool(e.get('is_current')), bullets=e.get('bullets') or [],
            )
        changed.append('experiences')

    if parsed.get('educations') and (overwrite or not profile.educations.exists()):
        profile.educations.all().delete()
        for e in parsed['educations']:
            Education.objects.create(
                profile=profile, institution=(e.get('institution') or '')[:255],
                degree=(e.get('degree') or '')[:255], field_of_study=(e.get('field_of_study') or '')[:255],
                start_date=_d(e.get('start_date')), end_date=_d(e.get('end_date')),
                gpa=(e.get('gpa') or '')[:16],
            )
        changed.append('educations')

    if parsed.get('projects') and (overwrite or not profile.projects.exists()):
        profile.projects.all().delete()
        for p in parsed['projects']:
            url = p.get('url') or ''
            Project.objects.create(
                profile=profile, name=(p.get('name') or 'Project')[:255],
                description=p.get('description') or '', url=url[:200],
                tech_stack=p.get('tech_stack') or [],
            )
        changed.append('projects')

    # Seed search preferences from the résumé so the job feed works immediately.
    pref, created = Preference.objects.get_or_create(profile=profile)
    if not pref.target_titles:
        title = parsed.get('headline') or (parsed.get('experiences') or [{}])[0].get('title', '')
        if title:
            pref.target_titles = [title[:120]]
            changed.append('preference.target_titles')
    if not pref.locations and parsed.get('location') and parsed['location'] != 'Remote':
        pref.locations = [parsed['location']]
        changed.append('preference.locations')
    pref.save()

    return {'changed': changed, 'added_skills': added_skills}
