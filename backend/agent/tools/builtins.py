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


@tool('find_referral_contacts', description='Rank the user contacts most relevant for a job referral.',
      phase=2, hitl=HITL_NONE, params_schema={'user_id': 'int', 'job_id': 'int', 'limit': 'int'})
def find_referral_contacts(*, user_id: int, job_id: int, limit: int = 10):
    from django.contrib.auth import get_user_model
    from jobs.models import JobPosting
    from networking.services import rank_contacts_for_job

    user = get_user_model().objects.get(pk=user_id)
    job = JobPosting.objects.select_related('company').get(pk=job_id)
    opportunities = rank_contacts_for_job(user=user, job=job, limit=limit)
    return [
        {
            'id': item.id,
            'contact_id': item.contact_id,
            'contact_name': item.contact.name,
            'contact_title': item.contact.title,
            'score': item.score,
            'reason': item.reason,
            'next_action': item.next_action,
        }
        for item in opportunities
    ]


@tool('draft_outreach_message', description='Draft a referral or recruiter outreach message for review.',
      phase=2, hitl=HITL_NONE,
      params_schema={'user_id': 'int', 'contact_id': 'int', 'job_id': 'int', 'channel': 'str'})
def draft_outreach_message(*, user_id: int, contact_id: int, job_id: int | None = None,
                           channel: str = 'manual'):
    from django.contrib.auth import get_user_model
    from jobs.models import JobPosting
    from networking.models import Contact
    from networking.services import draft_referral_message

    user = get_user_model().objects.get(pk=user_id)
    contact = Contact.objects.get(pk=contact_id, user=user)
    job = JobPosting.objects.select_related('company').get(pk=job_id) if job_id else None
    message = draft_referral_message(user=user, contact=contact, job=job, channel=channel)
    return {
        'id': message.id,
        'contact_id': message.contact_id,
        'job_id': message.job_id,
        'channel': message.channel,
        'subject': message.subject,
        'draft_body': message.draft_body,
        'status': message.status,
    }


@tool('find_warm_intros',
      description='Rank contacts who can warm-intro the user to people at a target company.',
      phase=2, hitl=HITL_NONE,
      params_schema={'user_id': 'int', 'company_id': 'int', 'max_hops': 'int', 'limit': 'int'})
def find_warm_intros(*, user_id: int, company_id: int, max_hops: int = 2, limit: int = 25):
    from django.contrib.auth import get_user_model
    from jobs.models import Company
    from networking.graph import warm_intros_to_company

    user = get_user_model().objects.get(pk=user_id)
    company = Company.objects.get(pk=company_id)
    return warm_intros_to_company(user=user, company=company, max_hops=max_hops, limit=limit)


@tool('explore_network',
      description='Return graph nodes+edges around a contact, company, or the user.',
      phase=1, hitl=HITL_NONE,
      params_schema={'user_id': 'int', 'root_kind': 'str', 'root_id': 'int', 'depth': 'int'})
def explore_network(*, user_id: int, root_kind: str = 'user', root_id: int = 0,
                    depth: int = 1):
    from django.contrib.auth import get_user_model
    from networking.graph import neighborhood

    user = get_user_model().objects.get(pk=user_id)
    if root_kind == 'user':
        root_id = user.id
    return neighborhood(user=user, root_kind=root_kind, root_id=root_id, depth=depth)


@tool('approve_outreach_message', description='Record user approval for the exact outreach content.',
      phase=2, hitl=HITL_CONFIRM,
      params_schema={'user_id': 'int', 'message_id': 'int', 'approved_body': 'str'})
def approve_outreach_tool(*, user_id: int, message_id: int, approved_body: str = ''):
    from django.contrib.auth import get_user_model
    from networking.models import OutreachMessage
    from networking.services import approve_outreach_message

    user = get_user_model().objects.get(pk=user_id)
    message = OutreachMessage.objects.get(pk=message_id, user=user)
    consent = approve_outreach_message(
        user=user,
        message=message,
        approved_body=approved_body or None,
    )
    return {
        'ok': True,
        'message_id': message.id,
        'approval_token': consent.approval_token,
        'expires_at': consent.expires_at.isoformat(),
    }


@tool('send_outreach_message', description='Mark/send outreach after user approval. Requires approval token.',
      phase=3, hitl=HITL_HARD_GATE,
      params_schema={'user_id': 'int', 'message_id': 'int', 'approval_token': 'str'})
def send_outreach_message(*, user_id: int, message_id: int, approval_token: str = ''):
    from django.contrib.auth import get_user_model
    from networking.models import OutreachMessage
    from networking.services import mark_outreach_sent

    user = get_user_model().objects.get(pk=user_id)
    message = OutreachMessage.objects.get(pk=message_id, user=user)
    return mark_outreach_sent(user=user, message=message, approval_token=approval_token)


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
