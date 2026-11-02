"""The Today plan: what should this job seeker do next?

Built only from real state — profile, jobs, applications, interviews — so the
home screen never shows made-up numbers. Steps are ordered by urgency:
setup gaps → upcoming interviews → follow-ups due → unfinished applications →
fresh strong matches.
"""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from .models import Application, ApplicationStatus

IN_PROGRESS = (ApplicationStatus.SAVED, ApplicationStatus.TAILORED, ApplicationStatus.READY)
INTERVIEWING = (ApplicationStatus.ASSESSMENT, ApplicationStatus.PHONE, ApplicationStatus.ONSITE)
SUBMITTED = (ApplicationStatus.APPLIED, ApplicationStatus.ASSESSMENT, ApplicationStatus.PHONE, ApplicationStatus.ONSITE,
             ApplicationStatus.OFFER, ApplicationStatus.REJECTED)


def _step(kind, title, detail, label, to, priority, **extra):
    return {'kind': kind, 'title': title, 'detail': detail,
            'action': {'label': label, 'to': to}, 'priority': priority, **extra}


def build_today(user, *, now=None) -> dict:
    from interview.models import InterviewSession
    from matching.views import feed_row, rank_for_user
    from profiles.models import StructuredProfile
    from resumes.models import Resume

    now = now or timezone.now()
    profile = StructuredProfile.objects.filter(user=user).first()
    try:
        pref = profile.preference if profile else None
    except Exception:  # noqa: BLE001
        pref = None
    has_resume = Resume.objects.filter(user=user, parse_status='done').exists()
    has_experience = bool(profile and profile.experiences.exists())
    has_skills = bool(profile and profile.skills.exists())
    targets = list(pref.target_titles or []) if pref else []
    weekly_goal = pref.weekly_goal if pref else 5

    apps = list(Application.objects.filter(user=user).select_related('job', 'job__company'))
    steps: list[dict] = []

    if not (has_resume or has_experience):
        steps.append(_step('setup', 'Add your résumé',
                           'Upload or paste it once — we build your profile from it and use it for every match.',
                           'Add résumé', '/setup', 0))
    if not targets:
        steps.append(_step('setup', 'Tell us the roles you want',
                           'Target titles drive which jobs we find and how we rank them.',
                           'Set targets', '/setup?step=targets', 1))

    rows, app_by_job, cand = ([], {}, None)
    if has_resume or has_experience or has_skills:
        rows, app_by_job, cand = rank_for_user(user)
    from jobs.views import visible_jobs
    total_jobs = visible_jobs(user).count()
    if targets and total_jobs == 0:
        steps.append(_step('setup', 'Find jobs for your target roles',
                           f'We will search public company boards and job APIs for: {", ".join(targets[:3])}.',
                           'Find jobs', '/jobs?refresh=1', 2))

    # Interviews: prepare.
    prepped = set(InterviewSession.objects.filter(user=user, status='done').values_list('job_id', flat=True))
    for a in sorted((a for a in apps if a.status in INTERVIEWING),
                    key=lambda a: a.next_interview_at or now + timedelta(days=365)):
        when = ''
        if a.next_interview_at:
            days = (a.next_interview_at.date() - now.date()).days
            when = 'today' if days == 0 else ('tomorrow' if days == 1 else (f'in {days} days' if days > 0 else ''))
        stage = {'assessment': 'online assessment', 'phone': 'interview', 'onsite': 'final round'}[a.status]
        steps.append(_step(
            'interview', f'Prepare for your {a.job.company.name} {stage}' + (f' {when}' if when else ''),
            'Run a practice round built from this job description.' if a.job_id not in prepped
            else 'You practised once — another round on your weak spots helps.',
            'Practise now', f'/practice?application={a.id}', 3, application_id=a.id))

    # Follow-ups due.
    for a in apps:
        if a.status == ApplicationStatus.APPLIED and a.follow_up_at and a.follow_up_at <= now:
            days = (now - (a.applied_at or a.created_at)).days
            steps.append(_step(
                'follow_up', f'Follow up with {a.job.company.name}',
                f'You applied for {a.job.title} {days} days ago with no response yet. A short, polite note helps.',
                'Mark followed up', f'/pipeline?focus={a.id}', 4, application_id=a.id))

    # Deadlines in the next 7 days for things not yet applied to.
    today_d = now.date()
    for a in sorted((a for a in apps if a.status in IN_PROGRESS and a.deadline), key=lambda a: a.deadline):
        days = (a.deadline - today_d).days
        if days < 0 or days > 7:
            continue
        when = 'today' if days == 0 else ('tomorrow' if days == 1 else f'in {days} days')
        steps.append(_step('deadline', f'{a.job.company.name} closes {when}',
                           f'Apply for {a.job.title} before {a.deadline:%d %b}.', 'Open', f'/jobs/{a.job_id}',
                           2.5 if days <= 2 else 4.5, application_id=a.id))

    # Unfinished applications.
    unfinished = [a for a in apps if a.status in IN_PROGRESS]
    deadline_ids = {s.get('application_id') for s in steps if s['kind'] == 'deadline'}
    for a in sorted((a for a in unfinished if a.id not in deadline_ids), key=lambda a: a.updated_at, reverse=True)[:3]:
        what = {'saved': 'Tailor your résumé and apply', 'tailored': 'Review your materials and apply',
                'ready': 'Submit your application'}[a.status]
        steps.append(_step('apply', f'{a.job.title} at {a.job.company.name}', what + '.',
                           'Open', f'/jobs/{a.job_id}', 5, application_id=a.id))

    strong = [(j, r) for j, r in rows if r and r['fit'] >= 70 and j.pk not in app_by_job]
    if strong:
        steps.append(_step('discover', f'{len(strong)} strong match{"es" if len(strong) != 1 else ""} to review',
                           'Roles where you already have most of what they ask for.',
                           'Review matches', '/jobs?min_fit=70', 6))

    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    applied_this_week = sum(1 for a in apps if a.applied_at and a.applied_at >= week_start)
    submitted = [a for a in apps if a.status in SUBMITTED or a.applied_at]
    responded = [a for a in submitted if a.status in (ApplicationStatus.ASSESSMENT, ApplicationStatus.PHONE, ApplicationStatus.ONSITE,
                                                      ApplicationStatus.OFFER)
                 or a.events.filter(type='status_changed', payload__status__in=['assessment', 'phone', 'onsite', 'offer']).exists()]

    return {
        'setup': {
            'has_resume': has_resume or has_experience,
            'has_targets': bool(targets),
            'has_jobs': total_jobs > 0,
            'complete': (has_resume or has_experience) and bool(targets) and total_jobs > 0,
        },
        'steps': sorted(steps, key=lambda s: s['priority'])[:8],
        'week': {'applied': applied_this_week, 'goal': weekly_goal},
        'stats': {
            'jobs_available': total_jobs,
            'strong_matches': len(strong),
            'in_progress': len(unfinished),
            'applied': len(submitted),
            'responses': len(responded),
            'response_rate': round(len(responded) / len(submitted), 3) if submitted else None,
            'interviewing': sum(1 for a in apps if a.status in INTERVIEWING),
            'offers': sum(1 for a in apps if a.status == ApplicationStatus.OFFER),
        },
        'top_matches': [feed_row(j, r, None) for j, r in strong[:3]] if strong else
                       [feed_row(j, r, None) for j, r in rows[:3] if j.pk not in app_by_job],
        'targets': targets,
    }
