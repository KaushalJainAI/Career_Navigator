from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework import generics, serializers as drf_serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from jobs.models import JobPosting

from jobs.models import Company

from .graph import neighborhood, warm_intros_to_company
from .models import (
    ActionQueueItem,
    CompanyRelationship,
    Contact,
    ContactEmployment,
    ContactRelationship,
    OutreachMessage,
    ReferralOpportunity,
)
from .serializers import (
    ActionQueueItemSerializer,
    CompanyRelationshipSerializer,
    ContactEmploymentSerializer,
    ContactRelationshipSerializer,
    ContactSerializer,
    OutreachApprovalSerializer,
    OutreachMessageSerializer,
    ReferralOpportunitySerializer,
)
from .services import approve_outreach_message, draft_referral_message, rank_contacts_for_job


class ContactListCreateView(generics.ListCreateAPIView):
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Contact.objects.filter(user=self.request.user).select_related('company')
        company_id = self.request.query_params.get('company_id')
        if company_id:
            qs = qs.filter(company_id=company_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ContactDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user)


class JobReferralSuggestionsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, job_id: int):
        job = get_object_or_404(JobPosting, pk=job_id)
        limit = int(request.data.get('limit', 10))
        opportunities = rank_contacts_for_job(user=request.user, job=job, limit=limit)
        return Response(ReferralOpportunitySerializer(opportunities, many=True).data)


class ReferralOpportunityListView(generics.ListAPIView):
    serializer_class = ReferralOpportunitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = ReferralOpportunity.objects.filter(user=self.request.user).select_related('job', 'contact')
        job_id = self.request.query_params.get('job_id')
        if job_id:
            qs = qs.filter(job_id=job_id)
        return qs


class OutreachMessageListCreateView(generics.ListCreateAPIView):
    serializer_class = OutreachMessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return OutreachMessage.objects.filter(user=self.request.user).select_related('contact', 'job')

    def create(self, request, *args, **kwargs):
        contact = get_object_or_404(Contact, pk=request.data.get('contact_id'), user=request.user)
        job = None
        if request.data.get('job_id'):
            job = get_object_or_404(JobPosting, pk=request.data['job_id'])
        message = draft_referral_message(
            user=request.user,
            contact=contact,
            job=job,
            channel=request.data.get('channel', 'manual'),
        )
        return Response(OutreachMessageSerializer(message).data, status=status.HTTP_201_CREATED)


class OutreachMessageDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = OutreachMessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return OutreachMessage.objects.filter(user=self.request.user)


class OutreachApproveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int):
        message = get_object_or_404(OutreachMessage, pk=pk, user=request.user)
        serializer = OutreachApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        consent = approve_outreach_message(
            user=request.user,
            message=message,
            approved_body=serializer.validated_data.get('approved_body'),
        )
        return Response({
            'approval_token': consent.approval_token,
            'expires_at': consent.expires_at,
            'message': OutreachMessageSerializer(message).data,
        })


class ActionQueueListView(generics.ListAPIView):
    serializer_class = ActionQueueItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        status_filter = self.request.query_params.get('status', 'open')
        qs = ActionQueueItem.objects.filter(user=self.request.user).select_related('job', 'contact')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


def _user_contact_or_404(user, pk: int) -> Contact:
    return get_object_or_404(Contact, pk=pk, user=user)


class ContactEmploymentListCreateView(generics.ListCreateAPIView):
    """List/create employment rows for one of the user's contacts."""

    serializer_class = ContactEmploymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        contact = _user_contact_or_404(self.request.user, self.kwargs['pk'])
        return contact.employments.select_related('company').order_by('-is_current', '-started_at')

    def perform_create(self, serializer):
        contact = _user_contact_or_404(self.request.user, self.kwargs['pk'])
        serializer.save(contact=contact)
        # After mutation: re-infer colleague edges for this contact.
        from .graph import infer_colleague_relationships
        infer_colleague_relationships(user=self.request.user, contact=contact)


class ContactEmploymentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ContactEmploymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ContactEmployment.objects.filter(contact__user=self.request.user)


class ContactRelationshipListCreateView(generics.ListCreateAPIView):
    serializer_class = ContactRelationshipSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        contact = _user_contact_or_404(self.request.user, self.kwargs['pk'])
        return ContactRelationship.objects.filter(
            user=self.request.user, from_contact=contact
        ).select_related('from_contact', 'to_contact')

    def perform_create(self, serializer):
        from_contact = _user_contact_or_404(self.request.user, self.kwargs['pk'])
        to_contact = serializer.validated_data.get('to_contact')
        if to_contact.user_id != self.request.user.id:
            raise PermissionDenied('to_contact must belong to the requesting user.')
        try:
            serializer.save(user=self.request.user, from_contact=from_contact, inferred=False)
        except IntegrityError as exc:
            raise drf_serializers.ValidationError(
                {'detail': 'A relationship of this kind already exists between these contacts.'}
            ) from exc


class ContactRelationshipDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = ContactRelationshipSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ContactRelationship.objects.filter(user=self.request.user)


class CompanyRelationshipListCreateView(generics.ListCreateAPIView):
    serializer_class = CompanyRelationshipSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CompanyRelationship.objects.filter(
            from_company_id=self.kwargs['pk']
        ).select_related('from_company', 'to_company')

    def perform_create(self, serializer):
        from_company = get_object_or_404(Company, pk=self.kwargs['pk'])
        serializer.save(from_company=from_company)


class GraphNeighborhoodView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        root = request.query_params.get('root', f'user:{request.user.id}')
        try:
            root_kind, root_id_str = root.split(':', 1)
            root_id = int(root_id_str)
        except (ValueError, AttributeError):
            return Response({'detail': "root must be 'user:<id>', 'contact:<id>', or 'company:<id>'."},
                            status=status.HTTP_400_BAD_REQUEST)
        if root_kind not in {'user', 'contact', 'company'}:
            return Response({'detail': f'unknown root kind {root_kind!r}'},
                            status=status.HTTP_400_BAD_REQUEST)
        if root_kind == 'user' and root_id != request.user.id:
            return Response({'detail': 'user root must be self.'},
                            status=status.HTTP_403_FORBIDDEN)
        depth = int(request.query_params.get('depth', '1') or '1')
        data = neighborhood(user=request.user, root_kind=root_kind, root_id=root_id, depth=depth)
        return Response(data)


class WarmIntrosView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, company_id: int):
        company = get_object_or_404(Company, pk=company_id)
        max_hops = int(request.query_params.get('max_hops', '2') or '2')
        limit = int(request.query_params.get('limit', '25') or '25')
        results = warm_intros_to_company(
            user=request.user, company=company, max_hops=max_hops, limit=limit,
        )
        return Response({'company': {'id': company.id, 'name': company.name},
                         'results': results})
