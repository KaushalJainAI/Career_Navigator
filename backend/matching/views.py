from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from jobs.models import JobPosting
from resumes.models import Resume

from .models import MatchScore
from .scorer import score_resume_against_job
from .serializers import MatchScoreSerializer


class JobMatchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id: int):
        job = get_object_or_404(JobPosting, pk=job_id)
        master = Resume.objects.filter(user=request.user, is_master=True).first() or \
            Resume.objects.filter(user=request.user).order_by('-created_at').first()
        if master is None or not master.parsed_json:
            return Response({'detail': 'Upload and parse a resume first.'}, status=400)
        result = score_resume_against_job(master.parsed_json, job.title, job.description)
        score, _ = MatchScore.objects.update_or_create(
            user=request.user, job=job,
            defaults={'score': result['score'], 'breakdown': result['breakdown'], 'gaps': result['gaps']},
        )
        return Response(MatchScoreSerializer(score).data)
