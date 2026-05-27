"""Endpoints consumed by the MV3 browser extension.

Page-context and submit-event flow follows the user-driven autofill tier described in
docs/job-search-skills-workflows-plan.md Workflow E. Profile-context populates the
contact + employment history graph used by the warm-intros feature."""

from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import UserProfile
from applications.models import Application, ApplicationEvent
from ingestion.services import upsert_postings
from jobs.models import Company, JobPosting, Source
from networking.graph import infer_colleague_relationships
from networking.models import Contact, ContactEmployment, ContactSource
from profiles.models import StructuredProfile

from .serializers import (
    PageContextSerializer,
    ProfileContextSerializer,
    SubmitEventSerializer,
)


_SOURCE_NAMES = {
    'linkedin': ('linkedin_extension', 'scraper'),
    'greenhouse': ('greenhouse_extension', 'scraper'),
    'lever': ('lever_extension', 'scraper'),
    'naukri': ('naukri_extension', 'scraper'),
    'unstop': ('unstop_extension', 'scraper'),
    'mercor': ('mercor_extension', 'scraper'),
}


def _resolve_source(parser: str) -> Source:
    name, kind = _SOURCE_NAMES[parser]
    source, _ = Source.objects.get_or_create(name=name, defaults={'kind': kind})
    return source


def _stealth_blocked(user, domain: str) -> bool:
    if not domain:
        return False
    profile = UserProfile.objects.filter(user=user).first()
    if profile is None:
        return False
    blocked = {(d or '').lower() for d in (profile.stealth_domains or [])}
    return domain.lower() in blocked


class PageContextView(APIView):
    """Extension content script POSTs the parsed job posting from a page the user
    is viewing. We upsert a JobPosting via the canonical ingestion pipeline."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PageContextSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        company_data = data['company'] or {}
        if _stealth_blocked(request.user, company_data.get('domain', '')):
            return Response({'job_id': None, 'stealth_blocked': True})

        source = _resolve_source(data['parser'])
        normalised = {
            'external_id': data['external_id'],
            'title': data['title'],
            'description': data.get('description', ''),
            'location': data.get('location', ''),
            'remote': data.get('remote', False),
            'salary_min': data.get('salary_min'),
            'salary_max': data.get('salary_max'),
            'salary_currency': data.get('salary_currency', ''),
            'apply_url': data.get('apply_url', ''),
            'company': {
                'name': company_data.get('name', '') or 'Unknown',
                'domain': company_data.get('domain', ''),
                'ats_type': company_data.get('ats_type', 'other'),
            },
            'raw': data.get('raw', {}),
        }
        stats = upsert_postings(source, [normalised])
        job = JobPosting.objects.get(source=source, external_id=data['external_id'])
        return Response({'job_id': job.id, 'stats': stats, 'stealth_blocked': False})


class AutofillView(APIView):
    """Return the values the extension should pre-fill in the page's apply form,
    along with per-field confidence scores (0.0–1.0)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        job_id = request.query_params.get('job_id')
        application = None
        if job_id:
            application = Application.objects.filter(job_id=job_id, user=request.user).first()
        profile = StructuredProfile.objects.filter(user=request.user).first()
        fields = {
            'full_name': getattr(profile, 'full_name', '') if profile else '',
            'email': request.user.email,
            'phone': getattr(profile, 'phone', '') if profile else '',
            'linkedin': getattr(profile, 'linkedin', '') if profile else '',
            'github': getattr(profile, 'github', '') if profile else '',
        }
        confidence = {
            'full_name': 1.0 if fields['full_name'] else 0.0,
            'email': 1.0 if fields['email'] else 0.0,
            'phone': 0.9 if fields['phone'] else 0.0,
            'linkedin': 0.9 if fields['linkedin'] else 0.0,
            'github': 0.9 if fields['github'] else 0.0,
        }
        return Response({
            'application_id': application.id if application else None,
            'fields': fields,
            'field_confidence': confidence,
        })


class SubmitEventView(APIView):
    """Record that the user clicked Submit on an apply page. Upserts an Application
    and writes an ApplicationEvent('extension_submit') for the audit trail."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SubmitEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            job = JobPosting.objects.get(pk=data['job_id'])
        except JobPosting.DoesNotExist:
            return Response({'detail': 'unknown job_id'}, status=status.HTTP_404_NOT_FOUND)

        app, _ = Application.objects.update_or_create(
            user=request.user,
            job=job,
            defaults={'status': data.get('status', 'applied'),
                      'tier_used': data.get('tier', 'autofill')},
        )
        ApplicationEvent.objects.create(
            application=app,
            type='extension_submit',
            payload={
                'parser': data.get('parser', ''),
                'parser_version': data.get('parser_version', ''),
                'url': data.get('url', ''),
                'field_values': data.get('field_values', {}),
            },
        )
        return Response({'ok': True, 'application_id': app.id, 'status': app.status})


class ProfileContextView(APIView):
    """Extension POSTs a parsed LinkedIn profile (or similar). Upserts a Contact
    plus one ContactEmployment row per experience entry. Triggers colleague-
    edge inference so the network graph stays warm."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ProfileContextSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        contact, contact_created = Contact.objects.update_or_create(
            user=request.user,
            profile_url=data['profile_url'],
            defaults={
                'name': data['name'],
                'title': data.get('headline', ''),
                'location': data.get('location', ''),
                'email': data.get('email', '') or '',
                'source': ContactSource.PROFILE_URL,
            },
        )

        emp_created = 0
        emp_updated = 0
        for exp in data.get('experiences', []) or []:
            company_name = exp['company_name']
            company, _ = Company.objects.get_or_create(
                name=company_name,
                domain=exp.get('company_domain', '') or '',
                defaults={'ats_type': 'other'},
            )
            obj, was_created = ContactEmployment.objects.update_or_create(
                contact=contact,
                company=company,
                title=exp.get('title', ''),
                started_at=exp.get('started_at'),
                defaults={
                    'ended_at': exp.get('ended_at'),
                    'is_current': exp.get('is_current', False),
                    'source': ContactSource.PROFILE_URL,
                    'raw': exp.get('raw', {}),
                },
            )
            if was_created:
                emp_created += 1
            else:
                emp_updated += 1

        # Set current employer hint on the Contact.company FK from the first current row.
        current = (
            contact.employments
            .filter(is_current=True)
            .select_related('company')
            .order_by('-started_at')
            .first()
        )
        if current is not None and contact.company_id != current.company_id:
            contact.company = current.company
            contact.save(update_fields=['company', 'updated_at'])

        inferred = infer_colleague_relationships(user=request.user, contact=contact)

        return Response({
            'contact_id': contact.id,
            'contact_created': contact_created,
            'employments_created': emp_created,
            'employments_updated': emp_updated,
            'colleagues_inferred': inferred,
        })
