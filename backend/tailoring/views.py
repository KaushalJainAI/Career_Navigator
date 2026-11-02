from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ai.providers import configured_model_label, get_configured_llm
from applications.models import Application, ApplicationEvent, ApplicationStatus
from jobs.views import visible_jobs
from resumes.ats_export import build_ats_docx, build_ats_resume

from .engine import (
    draft_cover_letter,
    llm_polish,
    profile_snapshot,
    tailor,
    verify_cover_letter,
)
from .models import CoverLetter, TailoredResume


def _export_dict(user, tailored_summary: str = '') -> dict:
    """ATS-export dict from the user's profile, optionally with a tailored summary."""
    data = profile_snapshot(user)
    if not data.get('full_name'):
        data['full_name'] = user.get_full_name() or user.username
    if tailored_summary:
        data['summary'] = tailored_summary
    return data


def _application_for(request) -> Application | None:
    """Accept application_id, or job_id (creating a 'saved' application)."""
    app_id = request.data.get('application_id') or request.query_params.get('application_id')
    if app_id:
        return Application.objects.select_related('job', 'job__company').filter(
            pk=app_id, user=request.user).first()
    job_id = request.data.get('job_id') or request.query_params.get('job_id')
    if job_id:
        job = visible_jobs(request.user).filter(pk=job_id).first()
        if job is None:
            return None
        app, _ = Application.objects.get_or_create(user=request.user, job=job)
        return app
    return None


def _has_facts(snapshot: dict) -> bool:
    return bool(snapshot.get('experiences') or snapshot.get('skills') or snapshot.get('summary'))


def _llm_or_none():
    llm = get_configured_llm()
    if llm is None:
        return None
    # A configured provider without credentials returns ''; treat as absent.
    return llm


def _tailored_payload(tr: TailoredResume, app: Application) -> dict:
    return {'id': tr.id, 'application_id': app.id, 'content': tr.content,
            'diff_from_master': tr.diff_from_master, 'model_used': tr.model_used,
            'created_at': tr.created_at}


class ExportResumeView(APIView):
    """ATS-safe résumé download. With `?application_id=` the full tailored
    résumé for that application is exported; otherwise the master profile."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = _export_dict(request.user)
        app_id = request.query_params.get('application_id')
        if app_id:
            app = Application.objects.filter(pk=app_id, user=request.user).first()
            if app is None:
                return Response({'detail': 'Application not found.'}, status=404)
            tailored = TailoredResume.objects.filter(application=app).first()
            if tailored and tailored.content:
                content = tailored.content
                if content.get('experiences') is not None or content.get('skills') is not None:
                    data = {**data, **{k: v for k, v in content.items() if v not in (None, '')}}
                elif content.get('summary'):
                    data['summary'] = content['summary']
        # NB: use `fmt`, not `format` — DRF reserves `?format=` for content negotiation.
        fmt = request.query_params.get('fmt', 'txt').lower()
        base = (data.get('full_name') or 'resume').strip().lower().replace(' ', '-') or 'resume'
        if fmt == 'docx':
            payload = build_ats_docx(data)
            response = HttpResponse(
                payload,
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            )
            response['Content-Disposition'] = f'attachment; filename="{base}-resume-ats.docx"'
            return response
        response = HttpResponse(build_ats_resume(data), content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{base}-resume-ats.txt"'
        return response


class TailorResumeView(APIView):
    """POST: generate (or regenerate) the tailored résumé for an application.
    GET:  fetch the existing one (404 if none)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        app = _application_for(request)
        if app is None:
            return Response({'detail': 'Application not found.'}, status=404)
        tr = TailoredResume.objects.filter(application=app).first()
        if tr is None:
            return Response({'detail': 'Not generated yet.'}, status=404)
        return Response(_tailored_payload(tr, app))

    def post(self, request):
        app = _application_for(request)
        if app is None:
            return Response({'detail': 'Application not found.'}, status=404)
        snapshot = profile_snapshot(request.user)
        if not _has_facts(snapshot):
            return Response({'detail': 'Upload your résumé or fill in your profile first.'}, status=400)
        job = app.job
        result = tailor(snapshot, job_title=job.title, company=job.company.name,
                        description=job.description, jd_skills=job.skills or None)
        result = llm_polish(result, snapshot, job_title=job.title, company=job.company.name,
                            llm=_llm_or_none())
        diff = {**result['diff_from_master'],
                'keyword_coverage': result['keyword_coverage'],
                'missing_skills': result['missing_skills'],
                'suggestions': result['suggestions'],
                'verification': result.get('verification', [])}
        tr, _ = TailoredResume.objects.update_or_create(
            application=app,
            defaults={
                'content': result['content'],
                'diff_from_master': diff,
                'model_used': configured_model_label() if result.get('model_used') else 'deterministic',
            },
        )
        if app.status == ApplicationStatus.SAVED:
            app.status = ApplicationStatus.TAILORED
            app.save(update_fields=['status', 'updated_at'])
        ApplicationEvent.objects.create(application=app, type='tailored_resume_generated',
                                        payload={'tailored_resume_id': tr.id})
        return Response(_tailored_payload(tr, app))


class TailoredResumeEditView(APIView):
    """PATCH the tailored content after reviewing it (summary, skills, bullets)."""

    permission_classes = [IsAuthenticated]
    EDITABLE = {'summary', 'headline', 'skills', 'experiences', 'projects'}

    def patch(self, request, pk: int):
        tr = get_object_or_404(TailoredResume, pk=pk, application__user=request.user)
        content = dict(tr.content or {})
        incoming = request.data.get('content') or {}
        for key, value in incoming.items():
            if key not in self.EDITABLE:
                continue
            if key == 'experiences' and isinstance(value, list):
                # Only bullets are editable; employers/titles/dates stay as in the profile.
                old = content.get('experiences') or []
                for i, e in enumerate(old):
                    if i < len(value) and isinstance(value[i], dict) and isinstance(value[i].get('bullets'), list):
                        e['bullets'] = [str(b) for b in value[i]['bullets'] if str(b).strip()]
                content['experiences'] = old
            else:
                content[key] = value
        tr.content = content
        tr.model_used = tr.model_used if 'edited' in tr.model_used else f'{tr.model_used}+edited'.strip('+')
        tr.save(update_fields=['content', 'model_used'])
        return Response(_tailored_payload(tr, tr.application))


class DraftCoverLetterView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        app = _application_for(request)
        if app is None:
            return Response({'detail': 'Application not found.'}, status=404)
        cl = CoverLetter.objects.filter(application=app).first()
        if cl is None:
            return Response({'detail': 'Not generated yet.'}, status=404)
        return Response({'id': cl.id, 'application_id': app.id, 'content': cl.content, 'model_used': cl.model_used})

    def post(self, request):
        app = _application_for(request)
        if app is None:
            return Response({'detail': 'Application not found.'}, status=404)
        snapshot = profile_snapshot(request.user)
        if not _has_facts(snapshot):
            return Response({'detail': 'Upload your résumé or fill in your profile first.'}, status=400)
        job = app.job
        tailored = tailor(snapshot, job_title=job.title, company=job.company.name,
                          description=job.description, jd_skills=job.skills or None)
        text = draft_cover_letter(snapshot, tailored, job_title=job.title, company=job.company.name,
                                  description=job.description)
        model_used = 'deterministic'
        notes: list[str] = []
        llm = _llm_or_none()
        if llm is not None:
            prompt = (
                'Polish this cover letter. Keep it under 250 words, keep every fact, and do not add any '
                'skill, employer, number or achievement that is not already in it. Return only the letter.\n\n'
                + text
            )
            try:
                polished = (llm(prompt) or '').strip()
            except Exception:  # noqa: BLE001
                polished = ''
            if polished:
                problems = verify_cover_letter(polished, snapshot)
                if problems:
                    notes = ['AI polish rejected: ' + '; '.join(problems)]
                else:
                    text, model_used = polished, configured_model_label()
        cl, _ = CoverLetter.objects.update_or_create(
            application=app, defaults={'content': text, 'model_used': model_used})
        ApplicationEvent.objects.create(application=app, type='cover_letter_generated',
                                        payload={'cover_letter_id': cl.id})
        return Response({'id': cl.id, 'application_id': app.id, 'content': cl.content,
                         'model_used': model_used, 'verification': notes})


class CoverLetterEditView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk: int):
        cl = get_object_or_404(CoverLetter, pk=pk, application__user=request.user)
        content = request.data.get('content')
        if not isinstance(content, str) or not content.strip():
            return Response({'detail': 'content is required'}, status=400)
        cl.content = content
        cl.save(update_fields=['content'])
        return Response({'id': cl.id, 'application_id': cl.application_id, 'content': cl.content,
                         'model_used': cl.model_used})
