from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ai.providers import configured_model_label, get_configured_llm
from applications.models import Application, ApplicationEvent, ApplicationStatus
from resumes.ats_export import build_ats_docx, build_ats_resume
from resumes.models import Resume

from .generators import draft_cover_letter, tailor_resume
from .models import CoverLetter, TailoredResume


def _export_dict(user, tailored_summary: str = '') -> dict:
    """Assemble the ATS-export dict from the user's StructuredProfile, overlaying
    a tailored summary when one was generated for this application."""
    profile = getattr(user, 'structured_profile', None)
    if profile is None:
        return {'full_name': user.get_full_name() or user.username,
                'email': user.email, 'summary': tailored_summary}
    return {
        'full_name': profile.full_name or user.get_full_name() or user.username,
        'headline': profile.headline,
        'email': user.email,
        'phone': profile.phone,
        'location': profile.location,
        'links': [link for link in (profile.website, profile.linkedin, profile.github) if link],
        'summary': tailored_summary or profile.summary,
        'skills': [{'name': s.name} for s in profile.skills.all()],
        'experiences': [{
            'title': e.title, 'company': e.company, 'location': e.location,
            'start': e.start_date.isoformat() if e.start_date else '',
            'end': e.end_date.isoformat() if e.end_date else '',
            'is_current': e.is_current, 'bullets': e.bullets or [],
        } for e in profile.experiences.all()],
        'educations': [{
            'degree': ed.degree, 'field_of_study': ed.field_of_study,
            'institution': ed.institution,
            'end': ed.end_date.isoformat() if ed.end_date else '', 'gpa': ed.gpa,
        } for ed in profile.educations.all()],
        'projects': [{'name': p.name, 'description': p.description} for p in profile.projects.all()],
    }


class ExportResumeView(APIView):
    """ATS-safe résumé download. `?application_id=` overlays that application's
    tailored summary; `?format=docx` returns a .docx, otherwise plain text."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        tailored_summary = ''
        app_id = request.query_params.get('application_id')
        if app_id:
            app = Application.objects.filter(pk=app_id, user=request.user).first()
            if app is None:
                return Response({'detail': 'Application not found.'}, status=404)
            tailored = TailoredResume.objects.filter(application=app).first()
            if tailored:
                tailored_summary = (tailored.content or {}).get('summary', '')

        data = _export_dict(request.user, tailored_summary)
        # NB: use `fmt`, not `format` — DRF reserves `?format=` for content
        # negotiation and raises Http404 for an unknown renderer name.
        fmt = request.query_params.get('fmt', 'txt').lower()
        if fmt == 'docx':
            payload = build_ats_docx(data)
            response = HttpResponse(
                payload,
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            )
            response['Content-Disposition'] = 'attachment; filename="resume-ats.docx"'
            return response
        response = HttpResponse(build_ats_resume(data), content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="resume-ats.txt"'
        return response


class TailorResumeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        app_id = request.data.get('application_id')
        app = Application.objects.select_related('job', 'job__company').get(pk=app_id, user=request.user)
        master = Resume.objects.filter(user=request.user, is_master=True).first()
        if master is None:
            return Response({'detail': 'No master resume.'}, status=400)
        llm = get_configured_llm()
        out = tailor_resume(
            master.parsed_json or {},
            app.job.title,
            app.job.description,
            llm=llm,
        )
        tr, _ = TailoredResume.objects.update_or_create(
            application=app,
            defaults={
                'content': out['content'],
                'diff_from_master': out['diff_from_master'],
                'model_used': configured_model_label() if llm else '',
            },
        )
        if app.status == ApplicationStatus.SAVED:
            app.status = ApplicationStatus.TAILORED
            app.save(update_fields=['status', 'updated_at'])
        ApplicationEvent.objects.create(application=app, type='tailored_resume_generated', payload={'tailored_resume_id': tr.id})
        return Response({'id': tr.id, 'content': tr.content})


class DraftCoverLetterView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        app_id = request.data.get('application_id')
        app = Application.objects.select_related('job', 'job__company').get(pk=app_id, user=request.user)
        master = Resume.objects.filter(user=request.user, is_master=True).first()
        llm = get_configured_llm()
        text = draft_cover_letter(
            master.parsed_json if master else {},
            app.job.title,
            app.job.company.name,
            app.job.description,
            llm=llm,
        )
        cl, _ = CoverLetter.objects.update_or_create(
            application=app,
            defaults={'content': text, 'model_used': configured_model_label() if llm else ''},
        )
        ApplicationEvent.objects.create(application=app, type='cover_letter_generated', payload={'cover_letter_id': cl.id})
        return Response({'id': cl.id, 'content': cl.content})
