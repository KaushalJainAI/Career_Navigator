"""Copilot tools — the actions the chat agent can take on the user's behalf.

Design (mirrors AIAAS chat/tools.py, with a deliberately small tool set):
  - Every tool receives the authenticated `user` from the orchestrator. The
    model never chooses whose data it touches.
  - `risk`:
      'read'    — runs immediately (search, list, explain).
      'draft'   — creates reviewable drafts / saves (tailor, save job); runs immediately.
      'confirm' — changes the user's records (status, profile, contacts); the
                  loop pauses and the user approves the exact call in the UI.
  - Nothing here submits an application or sends a message to another person.
    Those stay human actions (vision principles 1 and 9).
  - Each result is JSON-serialisable and may include `ui` hints the chat UI
    renders as buttons/links (e.g. open a job).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Callable

READ, DRAFT, CONFIRM = 'read', 'draft', 'confirm'


@dataclass
class CopilotTool:
    name: str
    description: str
    params: dict  # JSON-schema "properties"
    required: list[str]
    risk: str
    fn: Callable[..., Any]
    summary: Callable[[dict], str] = field(default=lambda args: '')


TOOLS: dict[str, CopilotTool] = {}


def copilot_tool(name: str, description: str, *, params: dict | None = None, required: list[str] | None = None,
                 risk: str = READ, summary: Callable[[dict], str] | None = None):
    def deco(fn):
        TOOLS[name] = CopilotTool(name=name, description=description, params=params or {}, required=required or [],
                                  risk=risk, fn=fn, summary=summary or (lambda a: ''))
        return fn
    return deco


def schema() -> list[dict]:
    """Tool catalogue for prompts and the MCP server."""
    return [{'name': t.name, 'description': t.description, 'risk': t.risk,
             'input_schema': {'type': 'object', 'properties': t.params, 'required': t.required}}
            for t in TOOLS.values()]


class ToolError(Exception):
    pass


def _app_qs(user):
    from applications.models import Application
    return Application.objects.filter(user=user).select_related('job', 'job__company')


def _find_application(user, *, application_id=None, company=None):
    qs = _app_qs(user)
    if application_id:
        app = qs.filter(pk=application_id).first()
        if app:
            return app
    if company:
        matches = list(qs.filter(job__company__name__icontains=str(company).strip()))
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            names = ', '.join(f'#{a.id} {a.job.title}' for a in matches[:5])
            raise ToolError(f'More than one application at {company}: {names}. Which one?')
    raise ToolError('I could not find that application in your pipeline.')


def _job_brief(j, r=None) -> dict:
    out = {'job_id': j.pk, 'title': j.title, 'company': j.company.name, 'location': j.location,
           'remote': j.remote, 'apply_url': j.apply_url}
    if r:
        out.update({'fit': r['fit'], 'verdict': r['verdict'], 'matched': r['matched_skills'][:5],
                    'missing': r['missing_skills'][:4]})
    return out


def _app_brief(a) -> dict:
    return {'application_id': a.id, 'job_id': a.job_id, 'company': a.job.company.name, 'title': a.job.title,
            'status': a.status, 'applied_at': a.applied_at.date().isoformat() if a.applied_at else None,
            'deadline': a.deadline.isoformat() if a.deadline else None,
            'next_round_at': a.next_interview_at.isoformat() if a.next_interview_at else None,
            'notes': (a.notes or '')[:200]}


# ------------------------------------------------------------------ read

@copilot_tool('get_overview', 'What the user should do today: next steps, deadlines, follow-ups, interviews and honest stats.')
def get_overview(user):
    from applications.today import build_today
    t = build_today(user)
    return {'steps': [{'title': s['title'], 'detail': s['detail'], 'open': s['action']['to']} for s in t['steps']],
            'stats': t['stats'], 'week': t['week'], 'setup': t['setup'], 'targets': t['targets']}


@copilot_tool('get_profile', "Summary of the user's profile: headline, education, skills, experience, projects and job targets.")
def get_profile(user):
    from tailoring.engine import profile_snapshot
    snap = profile_snapshot(user)
    prof = getattr(user, 'structured_profile', None)
    pref = None
    try:
        pref = prof.preference if prof else None
    except Exception:  # noqa: BLE001
        pref = None
    return {
        'name': snap.get('full_name'), 'headline': snap.get('headline'), 'location': snap.get('location'),
        'skills': [s['name'] for s in snap.get('skills') or []][:40],
        'experience': [f"{e['title']} at {e['company']}" for e in snap.get('experiences') or []],
        'education': [f"{e.get('degree', '')} {e.get('field_of_study', '')} — {e.get('institution', '')} "
                      f"{str(e.get('end') or '')[:4]} {('CGPA ' + e['gpa']) if e.get('gpa') else ''}".strip()
                      for e in snap.get('educations') or []],
        'projects': [p['name'] for p in snap.get('projects') or []],
        'targets': {'roles': pref.target_titles if pref else [], 'locations': pref.locations if pref else [],
                    'remote': pref.remote if pref else True, 'weekly_goal': pref.weekly_goal if pref else 5},
    }


@copilot_tool('search_jobs', 'Find jobs ranked by fit for the user. Use for "find me jobs", "best matches", "remote roles at X".',
              params={'query': {'type': 'string', 'description': 'keyword, title or company'},
                      'min_fit': {'type': 'integer', 'description': '0-100'},
                      'remote': {'type': 'boolean'}, 'limit': {'type': 'integer'}})
def search_jobs(user, query: str = '', min_fit: int = 0, remote: bool = False, limit: int = 5):
    from matching.views import rank_for_user
    rows, apps, cand = rank_for_user(user, q=query or '', remote=bool(remote), min_fit=int(min_fit or 0))
    limit = max(1, min(int(limit or 5), 10))
    return {'total': len(rows), 'has_profile': cand.has_data,
            'jobs': [_job_brief(j, r) for j, r in rows[:limit]],
            'ui': [{'type': 'link', 'label': 'See all in Jobs', 'to': '/jobs' + (f'?min_fit={min_fit}' if min_fit else '')}]}


@copilot_tool('get_job', 'Details and fit explanation for one job.', params={'job_id': {'type': 'integer'}}, required=['job_id'])
def get_job(user, job_id: int):
    from jobs.text import description_to_text
    from jobs.views import visible_jobs
    from matching.fit import score_fit
    from matching.views import candidate_for
    j = visible_jobs(user).filter(pk=job_id).first()
    if j is None:
        raise ToolError('Job not found.')
    r = score_fit(candidate_for(user), title=j.title, description=j.description, location=j.location,
                  remote=j.remote, skills=j.skills or None)
    return {**_job_brief(j, r), 'reasons': [x['title'] for x in r['explanation']],
            'description': description_to_text(j.description)[:1500],
            'ui': [{'type': 'link', 'label': 'Open job', 'to': f'/jobs/{j.pk}'}]}


@copilot_tool('list_applications', "The user's pipeline. Optional status filter: saved, tailored, ready, applied, assessment, phone, onsite, offer, rejected.",
              params={'status': {'type': 'string'}, 'company': {'type': 'string'}})
def list_applications(user, status: str = '', company: str = ''):
    qs = _app_qs(user).order_by('-updated_at')
    if status:
        qs = qs.filter(status=status)
    if company:
        qs = qs.filter(job__company__name__icontains=company)
    apps = list(qs[:25])
    return {'count': qs.count(), 'applications': [_app_brief(a) for a in apps],
            'ui': [{'type': 'link', 'label': 'Open pipeline', 'to': '/pipeline'}]}


@copilot_tool('list_contacts', "The user's networking contacts, optionally at one company (for referrals).",
              params={'company': {'type': 'string'}})
def list_contacts(user, company: str = ''):
    from networking.models import Contact
    qs = Contact.objects.filter(user=user).select_related('company')
    if company:
        qs = qs.filter(company__name__icontains=company)
    return {'contacts': [{'contact_id': c.id, 'name': c.name, 'title': c.title,
                          'company': c.company.name if c.company else '', 'email': c.email,
                          'relationship_strength': c.relationship_strength, 'notes': c.notes[:120]}
                         for c in qs[:25]]}


# ------------------------------------------------------------------ draft (safe, reviewable)

@copilot_tool('find_new_jobs', 'Search public company boards and job APIs for new roles matching the user targets. Takes up to a minute.',
              risk=DRAFT)
def find_new_jobs(user):
    from ingestion.discovery import discover_for_candidate
    from matching.views import candidate_for
    cand = candidate_for(user)
    if not cand.titles:
        raise ToolError('Set at least one target role first (e.g. "my target roles are Software Engineer and SDE Intern").')
    prof = getattr(user, 'structured_profile', None)
    try:
        watch = list(prof.preference.watch_companies or []) if prof else []
    except Exception:  # noqa: BLE001
        watch = []
    out = discover_for_candidate(cand, watch=watch)
    return {**out, 'ui': [{'type': 'link', 'label': 'See new jobs', 'to': '/jobs'}]}


@copilot_tool('save_job', 'Save a job to the pipeline (status "saved").', params={'job_id': {'type': 'integer'}},
              required=['job_id'], risk=DRAFT)
def save_job(user, job_id: int):
    from applications.models import Application
    from jobs.views import visible_jobs
    j = visible_jobs(user).filter(pk=job_id).first()
    if j is None:
        raise ToolError('Job not found.')
    app, created = Application.objects.get_or_create(user=user, job=j)
    return {**_app_brief(app), 'created': created,
            'ui': [{'type': 'link', 'label': 'Open job', 'to': f'/jobs/{j.pk}'}]}


@copilot_tool('add_job', 'Add a job the user found elsewhere (campus drive, referral, LinkedIn post). Needs a Greenhouse/Lever/Ashby link, or title + company + description.',
              params={'url': {'type': 'string'}, 'title': {'type': 'string'}, 'company': {'type': 'string'},
                      'description': {'type': 'string'}, 'location': {'type': 'string'},
                      'deadline': {'type': 'string', 'description': 'YYYY-MM-DD'}, 'notes': {'type': 'string'}},
              risk=DRAFT)
def add_job(user, url: str = '', title: str = '', company: str = '', description: str = '', location: str = '',
            deadline: str = '', notes: str = ''):
    from rest_framework.test import APIRequestFactory, force_authenticate
    from jobs.views import AddJobView
    req = APIRequestFactory().post('/api/v1/jobs/add/', {
        'url': url, 'title': title, 'company': company, 'description': description, 'location': location,
        'deadline': deadline, 'notes': notes}, format='json')
    force_authenticate(req, user=user)
    resp = AddJobView.as_view()(req)
    if resp.status_code >= 400:
        raise ToolError(resp.data.get('detail', 'Could not add the job.'))
    return {'job_id': resp.data['id'], 'application_id': resp.data['application_id'], 'title': resp.data['title'],
            'company': resp.data['company']['name'],
            'ui': [{'type': 'link', 'label': 'Open job', 'to': f"/jobs/{resp.data['id']}"}]}


def _ensure_app(user, job_id=None, application_id=None, company=None):
    from applications.models import Application
    from jobs.views import visible_jobs
    if job_id and not application_id:
        j = visible_jobs(user).filter(pk=job_id).first()
        if j is None:
            raise ToolError('Job not found.')
        return Application.objects.get_or_create(user=user, job=j)[0]
    return _find_application(user, application_id=application_id, company=company)


@copilot_tool('tailor_resume', 'Create a truthful tailored résumé for a job (reorders real skills/bullets; never invents). Returns coverage and gaps.',
              params={'job_id': {'type': 'integer'}, 'application_id': {'type': 'integer'}, 'company': {'type': 'string'}},
              risk=DRAFT)
def tailor_resume(user, job_id: int | None = None, application_id: int | None = None, company: str = ''):
    from applications.models import ApplicationEvent, ApplicationStatus
    from tailoring.engine import profile_snapshot, tailor
    from tailoring.models import TailoredResume
    app = _ensure_app(user, job_id, application_id, company)
    snap = profile_snapshot(user)
    if not (snap.get('experiences') or snap.get('skills') or snap.get('projects')):
        raise ToolError('Add your résumé first.')
    j = app.job
    res = tailor(snap, job_title=j.title, company=j.company.name, description=j.description, jd_skills=j.skills or None)
    TailoredResume.objects.update_or_create(application=app, defaults={
        'content': res['content'], 'model_used': 'deterministic',
        'diff_from_master': {**res['diff_from_master'], 'keyword_coverage': res['keyword_coverage'],
                             'missing_skills': res['missing_skills'], 'suggestions': res['suggestions'],
                             'verification': []}})
    if app.status == ApplicationStatus.SAVED:
        app.status = ApplicationStatus.TAILORED
        app.save(update_fields=['status', 'updated_at'])
    ApplicationEvent.objects.create(application=app, type='tailored_resume_generated', payload={'by': 'copilot'})
    return {'application_id': app.id, 'company': j.company.name, 'title': j.title,
            'keyword_coverage': res['keyword_coverage'], 'skills_moved_up': res['matched_skills'][:6],
            'missing_skills': res['missing_skills'][:5], 'summary': res['content']['summary'],
            'ui': [{'type': 'link', 'label': 'Review tailored résumé', 'to': f'/jobs/{j.pk}'}]}


@copilot_tool('draft_cover_letter', 'Draft a factual cover letter for a job for the user to review and edit.',
              params={'job_id': {'type': 'integer'}, 'application_id': {'type': 'integer'}, 'company': {'type': 'string'}},
              risk=DRAFT)
def draft_cover_letter_tool(user, job_id: int | None = None, application_id: int | None = None, company: str = ''):
    from tailoring.engine import draft_cover_letter, profile_snapshot, tailor
    from tailoring.models import CoverLetter
    app = _ensure_app(user, job_id, application_id, company)
    snap = profile_snapshot(user)
    j = app.job
    t = tailor(snap, job_title=j.title, company=j.company.name, description=j.description, jd_skills=j.skills or None)
    text = draft_cover_letter(snap, t, job_title=j.title, company=j.company.name, description=j.description)
    CoverLetter.objects.update_or_create(application=app, defaults={'content': text, 'model_used': 'deterministic'})
    return {'application_id': app.id, 'letter': text,
            'ui': [{'type': 'link', 'label': 'Edit cover letter', 'to': f'/jobs/{j.pk}'}]}


@copilot_tool('draft_referral_message', 'Draft (never send) a referral request to one of the user contacts for a job.',
              params={'contact_id': {'type': 'integer'}, 'job_id': {'type': 'integer'}},
              required=['contact_id'], risk=DRAFT)
def draft_referral(user, contact_id: int, job_id: int | None = None):
    from jobs.views import visible_jobs
    from networking.models import Contact
    from networking.services import draft_referral_message
    contact = Contact.objects.filter(user=user, pk=contact_id).first()
    if contact is None:
        raise ToolError('Contact not found.')
    job = visible_jobs(user).filter(pk=job_id).first() if job_id else None
    msg = draft_referral_message(user=user, contact=contact, job=job, channel='manual')
    return {'to': contact.name, 'subject': msg.subject, 'draft': msg.draft_body,
            'note': 'Draft only — copy it and send it yourself.'}


@copilot_tool('start_practice', 'Prepare an interview practice session for an application. Stages: tech_phone, cs_fundamentals, hr, behavioral, recruiter, system_design.',
              params={'application_id': {'type': 'integer'}, 'company': {'type': 'string'}, 'stage': {'type': 'string'}},
              risk=DRAFT)
def start_practice(user, application_id: int | None = None, company: str = '', stage: str = 'tech_phone'):
    app = _find_application(user, application_id=application_id, company=company)
    valid = {'tech_phone', 'cs_fundamentals', 'hr', 'behavioral', 'recruiter', 'system_design', 'role_specific'}
    stage = stage if stage in valid else 'tech_phone'
    return {'application_id': app.id, 'company': app.job.company.name, 'stage': stage,
            'ui': [{'type': 'link', 'label': f'Start {stage.replace("_", " ")} practice', 'to': f'/practice?application={app.id}'}]}


# ------------------------------------------------------------------ confirm (changes records)

def _parse_dt(value: str) -> datetime | None:
    from django.utils import timezone
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        try:
            dt = datetime.combine(date.fromisoformat(str(value)[:10]), datetime.min.time().replace(hour=10))
        except ValueError:
            raise ToolError(f'Could not read the date "{value}". Use YYYY-MM-DD or YYYY-MM-DDTHH:MM.')
    return timezone.make_aware(dt) if timezone.is_naive(dt) else dt


STATUSES = ['saved', 'tailored', 'ready', 'applied', 'assessment', 'phone', 'onsite', 'offer', 'rejected', 'withdrawn']


@copilot_tool('update_application', 'Change an application: status, notes, next round date-time, or deadline. Identify it by application_id or company.',
              params={'application_id': {'type': 'integer'}, 'company': {'type': 'string'},
                      'status': {'type': 'string', 'enum': STATUSES}, 'notes': {'type': 'string'},
                      'next_round_at': {'type': 'string', 'description': 'ISO date-time'},
                      'deadline': {'type': 'string', 'description': 'YYYY-MM-DD'}},
              risk=CONFIRM,
              summary=lambda a: 'Update ' + (a.get('company') or f"application #{a.get('application_id')}") + ': '
              + ', '.join(f'{k.replace("_", " ")} → {v}' for k, v in a.items() if k not in ('company', 'application_id') and v))
def update_application(user, application_id: int | None = None, company: str = '', status: str = '', notes: str = '',
                       next_round_at: str = '', deadline: str = ''):
    from applications.models import ApplicationEvent
    app = _find_application(user, application_id=application_id, company=company)
    fields = ['updated_at']
    old = app.status
    if status:
        if status not in STATUSES:
            raise ToolError(f'Unknown status {status}.')
        app.status = status
        app.apply_status_side_effects(old)
        fields += ['status', 'applied_at', 'follow_up_at']
    if notes:
        app.notes = (app.notes + '\n' + notes).strip() if app.notes else notes
        fields.append('notes')
    if next_round_at:
        app.next_interview_at = _parse_dt(next_round_at)
        fields.append('next_interview_at')
    if deadline:
        app.deadline = _parse_dt(deadline).date()
        fields.append('deadline')
    app.save(update_fields=list(dict.fromkeys(fields)))
    if status and status != old:
        ApplicationEvent.objects.create(application=app, type='status_changed', payload={'status': status, 'from': old, 'by': 'copilot'})
    return _app_brief(app)


@copilot_tool('update_targets', 'Set the roles/locations the user is targeting, remote preference, or weekly application goal.',
              params={'roles': {'type': 'array', 'items': {'type': 'string'}},
                      'locations': {'type': 'array', 'items': {'type': 'string'}},
                      'remote': {'type': 'boolean'}, 'weekly_goal': {'type': 'integer'},
                      'mode': {'type': 'string', 'enum': ['add', 'replace'], 'description': 'default add'}},
              risk=CONFIRM,
              summary=lambda a: 'Update job targets: ' + ', '.join(f'{k} → {v}' for k, v in a.items() if v not in (None, '', [])))
def update_targets(user, roles: list | None = None, locations: list | None = None, remote: bool | None = None,
                   weekly_goal: int | None = None, mode: str = 'add'):
    from profiles.models import Preference, StructuredProfile
    prof, _ = StructuredProfile.objects.get_or_create(user=user)
    pref, _ = Preference.objects.get_or_create(profile=prof)

    def merge(old, new):
        new = [str(x).strip() for x in (new or []) if str(x).strip()]
        return new if mode == 'replace' else list(dict.fromkeys(list(old or []) + new))
    if roles:
        pref.target_titles = merge(pref.target_titles, roles)
    if locations:
        pref.locations = merge(pref.locations, locations)
    if remote is not None:
        pref.remote = bool(remote)
    if weekly_goal:
        pref.weekly_goal = max(1, min(int(weekly_goal), 100))
    pref.save()
    return {'roles': pref.target_titles, 'locations': pref.locations, 'remote': pref.remote, 'weekly_goal': pref.weekly_goal}


@copilot_tool('update_skills', 'Add or remove skills on the user profile (only skills the user says they have).',
              params={'add': {'type': 'array', 'items': {'type': 'string'}},
                      'remove': {'type': 'array', 'items': {'type': 'string'}}},
              risk=CONFIRM,
              summary=lambda a: ' '.join(x for x in [f"Add skills: {', '.join(a.get('add') or [])}." if a.get('add') else '',
                                                     f"Remove: {', '.join(a.get('remove') or [])}." if a.get('remove') else ''] if x))
def update_skills(user, add: list | None = None, remove: list | None = None):
    from profiles.models import Skill, StructuredProfile
    from resumes.skills import canonical_skill
    prof, _ = StructuredProfile.objects.get_or_create(user=user)
    have = {s.name.lower(): s for s in prof.skills.all()}
    added, removed = [], []
    for raw in add or []:
        name = canonical_skill(str(raw))[:128]
        if name and name.lower() not in have:
            have[name.lower()] = Skill.objects.create(profile=prof, name=name)
            added.append(name)
    for raw in remove or []:
        s = have.pop(canonical_skill(str(raw)).lower(), None)
        if s:
            s.delete()
            removed.append(s.name)
    return {'added': added, 'removed': removed, 'skills': sorted(s.name for s in have.values())}


@copilot_tool('add_contact', 'Save a networking contact (recruiter, alumni, friend at a company) for referrals.',
              params={'name': {'type': 'string'}, 'company': {'type': 'string'}, 'title': {'type': 'string'},
                      'email': {'type': 'string'}, 'profile_url': {'type': 'string'}, 'notes': {'type': 'string'},
                      'relationship_strength': {'type': 'integer', 'description': '0-5'}},
              required=['name'], risk=CONFIRM,
              summary=lambda a: f"Add contact {a.get('name')}" + (f" ({a.get('title')})" if a.get('title') else '')
              + (f" at {a.get('company')}" if a.get('company') else ''))
def add_contact(user, name: str, company: str = '', title: str = '', email: str = '', profile_url: str = '',
                notes: str = '', relationship_strength: int = 2):
    from jobs.models import Company
    from networking.models import Contact
    comp = None
    if company:
        comp = Company.objects.filter(name__iexact=company.strip()).first() or \
            Company.objects.create(name=company.strip(), domain='')
    c = Contact.objects.create(user=user, name=name.strip()[:255], company=comp, title=title[:255], email=email[:254],
                               profile_url=profile_url[:200], notes=notes,
                               relationship_strength=max(0, min(int(relationship_strength or 0), 5)))
    return {'contact_id': c.id, 'name': c.name, 'company': company,
            'ui': [{'type': 'link', 'label': 'Open network', 'to': '/network'}]}


@copilot_tool('navigate', 'Open a page in the app for the user: /, /jobs, /jobs/<id>, /pipeline, /practice, /profile, /setup, /network, /settings.',
              params={'path': {'type': 'string'}}, required=['path'])
def navigate(user, path: str):
    allowed = ('/', '/jobs', '/pipeline', '/practice', '/profile', '/setup', '/network', '/settings')
    if not any(path == p or path.startswith(p + '/') or path.startswith(p + '?') for p in allowed):
        raise ToolError('Unknown page.')
    return {'ui': [{'type': 'navigate', 'to': path}]}
