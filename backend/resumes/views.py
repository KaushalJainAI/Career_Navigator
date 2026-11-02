from django.core.files.base import ContentFile
from django.db import transaction
from rest_framework import generics, parsers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from profiles.models import StructuredProfile
from profiles.services import apply_parsed_resume

from .models import Resume
from .parsing import extract_text, naive_structured_parse
from .serializers import ResumeSerializer


def _parse_into(resume: Resume, text: str | None = None) -> None:
    try:
        if text is None:
            resume.file.open('rb')
            text = extract_text(resume.file, resume.file.name)
        if not (text or '').strip():
            raise ValueError('No text could be extracted. If this is a scanned PDF, paste the text instead.')
        resume.parsed_json = naive_structured_parse(text)
        resume.parse_status = 'done'
        resume.parse_error = ''
    except Exception as exc:  # noqa: BLE001
        resume.parse_status = 'failed'
        resume.parse_error = str(exc)
    finally:
        try:
            resume.file.close()
        except Exception:  # noqa: BLE001
            pass


def _finalise(request, resume: Resume) -> dict:
    """Make the first parsed résumé the master and fill the profile from it."""
    user = request.user
    result = {'changed': [], 'added_skills': []}
    with transaction.atomic():
        if resume.parse_status == 'done' and not Resume.objects.filter(user=user, is_master=True).exists():
            resume.is_master = True
        resume.save()
        if resume.parse_status == 'done' and resume.is_master:
            profile, _ = StructuredProfile.objects.get_or_create(user=user)
            parsed = dict(resume.parsed_json or {})
            result = apply_parsed_resume(profile, parsed)
    return result


class ResumeListCreateView(generics.ListCreateAPIView):
    serializer_class = ResumeSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def get_queryset(self):
        return Resume.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        resume = serializer.save(user=request.user)
        _parse_into(resume)
        profile_update = _finalise(request, resume)
        data = ResumeSerializer(resume, context={'request': request}).data
        data['profile_update'] = profile_update
        return Response(data, status=status.HTTP_201_CREATED)


class ResumeImportTextView(APIView):
    """Paste résumé text instead of uploading a file (scanned PDFs, Google Docs...)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        text = (request.data.get('text') or '').strip()
        if len(text) < 40:
            return Response({'detail': 'Paste the full text of your résumé.'}, status=400)
        label = request.data.get('label') or 'Pasted resume'
        resume = Resume(user=request.user, label=label[:255])
        resume.file.save('resume.txt', ContentFile(text.encode('utf-8')), save=False)
        _parse_into(resume, text)
        profile_update = _finalise(request, resume)
        data = ResumeSerializer(resume, context={'request': request}).data
        data['profile_update'] = profile_update
        return Response(data, status=201)


class ResumeMakeMasterView(APIView):
    """Make this résumé the master and (optionally) re-import it into the profile."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int):
        resume = Resume.objects.filter(user=request.user, pk=pk).first()
        if resume is None:
            return Response({'detail': 'Not found.'}, status=404)
        if resume.parse_status != 'done':
            return Response({'detail': 'This résumé could not be parsed.'}, status=400)
        overwrite = bool(request.data.get('overwrite_profile'))
        with transaction.atomic():
            Resume.objects.filter(user=request.user, is_master=True).exclude(pk=pk).update(is_master=False)
            resume.is_master = True
            resume.save(update_fields=['is_master', 'updated_at'])
            profile, _ = StructuredProfile.objects.get_or_create(user=request.user)
            result = apply_parsed_resume(profile, resume.parsed_json or {}, overwrite=overwrite)
        return Response({'id': resume.id, 'is_master': True, 'profile_update': result})


class ResumeDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = ResumeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Resume.objects.filter(user=self.request.user)
