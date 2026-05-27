from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ai.providers import configured_model_label, get_configured_llm
from applications.models import Application
from resumes.models import Resume

from .generators import draft_cover_letter, tailor_resume
from .models import CoverLetter, TailoredResume


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
        return Response({'id': cl.id, 'content': cl.content})
