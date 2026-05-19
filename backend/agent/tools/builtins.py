"""Built-in tools exposed to the LangGraph orchestrator.
Each handler is intentionally thin — it delegates to the relevant Django service."""

from __future__ import annotations

from .registry import HITL_CONFIRM, HITL_HARD_GATE, HITL_NONE, tool


@tool('search_jobs', description='Search the JobPosting index with simple filters.',
      phase=1, hitl=HITL_NONE,
      params_schema={'query': 'str', 'location': 'str', 'remote': 'bool'})
def search_jobs(*, query: str = '', location: str = '', remote: bool | None = None,
                limit: int = 20):
    from jobs.models import JobPosting

    qs = JobPosting.objects.all()
    if query:
        qs = qs.filter(title__icontains=query)
    if location:
        qs = qs.filter(location__icontains=location)
    if remote is not None:
        qs = qs.filter(remote=bool(remote))
    return [
        {'id': j.id, 'title': j.title, 'company': j.company.name, 'location': j.location,
         'remote': j.remote, 'apply_url': j.apply_url}
        for j in qs[:limit]
    ]


@tool('score_match', description='Score a resume against a JobPosting.',
      phase=1, params_schema={'resume_id': 'int', 'job_id': 'int'})
def score_match(*, resume_id: int, job_id: int):
    from jobs.models import JobPosting
    from matching.scorer import score_resume_against_job
    from resumes.models import Resume

    resume = Resume.objects.get(pk=resume_id)
    job = JobPosting.objects.get(pk=job_id)
    return score_resume_against_job(resume.parsed_json or {}, job.title, job.description)


@tool('update_profile_field', description='Update one field on the user’s structured profile.',
      phase=1, params_schema={'user_id': 'int', 'field': 'str', 'value': 'any'})
def update_profile_field(*, user_id: int, field: str, value):
    from profiles.models import StructuredProfile

    profile, _ = StructuredProfile.objects.get_or_create(user_id=user_id)
    if not hasattr(profile, field):
        return {'ok': False, 'error': f'unknown field {field!r}'}
    setattr(profile, field, value)
    profile.save(update_fields=[field, 'updated_at'])
    return {'ok': True, 'field': field, 'value': value}


@tool('autofill_form', description='Generate the autofill payload for a job application.',
      phase=2, hitl=HITL_CONFIRM,
      params_schema={'application_id': 'int'})
def autofill_form(*, application_id: int):
    from applications.models import Application

    app = Application.objects.select_related('user', 'job').get(pk=application_id)
    profile = getattr(app.user, 'structured_profile', None)
    return {
        'application_id': app.id,
        'job_url': app.job.apply_url,
        'fields': {
            'full_name': getattr(profile, 'full_name', '') if profile else '',
            'email': app.user.email,
            'phone': getattr(profile, 'phone', '') if profile else '',
            'linkedin': getattr(profile, 'linkedin', '') if profile else '',
        },
    }


@tool('submit_application', description='Submit an application via the autonomous-apply pipeline. '
      'Requires user approval — orchestrator MUST refuse if no approval token is present.',
      phase=3, hitl=HITL_HARD_GATE,
      params_schema={'application_id': 'int', 'approval_token': 'str'})
def submit_application(*, application_id: int, approval_token: str = ''):
    from applications.models import Application

    app = Application.objects.get(pk=application_id)
    if not approval_token or app.auto_apply_session is None:
        return {'ok': False, 'error': 'missing approval_token'}
    if app.auto_apply_session.approval_token != approval_token:
        return {'ok': False, 'error': 'invalid approval_token'}
    app.status = 'applied'
    app.save(update_fields=['status', 'updated_at'])
    return {'ok': True, 'application_id': app.id, 'status': app.status}
