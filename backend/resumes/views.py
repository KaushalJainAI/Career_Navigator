from rest_framework import generics, parsers
from rest_framework.permissions import IsAuthenticated

from .models import Resume
from .parsing import extract_text, naive_structured_parse
from .serializers import ResumeSerializer


class ResumeListCreateView(generics.ListCreateAPIView):
    serializer_class = ResumeSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def get_queryset(self):
        return Resume.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        resume = serializer.save(user=self.request.user)
        try:
            resume.file.open('rb')
            text = extract_text(resume.file, resume.file.name)
            resume.parsed_json = naive_structured_parse(text)
            resume.parse_status = 'done'
        except Exception as exc:  # noqa: BLE001
            resume.parse_status = 'failed'
            resume.parse_error = str(exc)
        finally:
            try:
                resume.file.close()
            except Exception:  # noqa: BLE001
                pass
        resume.save()


class ResumeDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = ResumeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Resume.objects.filter(user=self.request.user)
