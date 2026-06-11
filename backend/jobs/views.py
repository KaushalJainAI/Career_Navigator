from rest_framework import filters, generics
from rest_framework.permissions import IsAuthenticated

from .models import JobPosting
from .serializers import JobPostingSerializer


class JobListView(generics.ListAPIView):
    serializer_class = JobPostingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'company__name', 'location']
    ordering_fields = ['posted_at', 'created_at', 'ghost_risk']

    def get_queryset(self):
        qs = JobPosting.objects.select_related('company', 'source')
        remote = self.request.query_params.get('remote')
        if remote in {'true', '1'}:
            qs = qs.filter(remote=True)
        location = self.request.query_params.get('location')
        if location:
            qs = qs.filter(location__icontains=location)
        # Ghost-Job Shield: let callers cap the ghost-risk of returned jobs.
        max_ghost_risk = self.request.query_params.get('max_ghost_risk')
        if max_ghost_risk is not None:
            try:
                qs = qs.filter(ghost_risk__lte=int(max_ghost_risk))
            except ValueError:
                pass
        # Honour stealth_domains from the user's UserProfile
        domains = getattr(getattr(self.request.user, 'cn_profile', None), 'stealth_domains', []) or []
        if domains:
            qs = qs.exclude(company__domain__in=domains)
        return qs


class JobDetailView(generics.RetrieveAPIView):
    queryset = JobPosting.objects.select_related('company', 'source')
    serializer_class = JobPostingSerializer
    permission_classes = [IsAuthenticated]
