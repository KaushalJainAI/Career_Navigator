"""Company hub aggregation — cross-app read model joining a Company to the
user's contacts, open opportunities and applications.

Pure ORM, no I/O. Returns plain dicts so both REST views and agent tools can
reuse it. The company↔application link is *derived* (Application → JobPosting →
Company) rather than stored, so it can never drift out of sync."""

from __future__ import annotations

from django.db.models import Q

from jobs.models import Company, JobPosting
from applications.models import Application

from .models import Contact, ContactEmployment
from .graph import warm_intros_to_company


def relevant_company_ids(user) -> set[int]:
    """Companies the user has a relationship with: a contact placed there,
    an employment record, or an application to one of its jobs."""
    contact_co = (Contact.objects.filter(user=user, company__isnull=False)
                  .values_list('company_id', flat=True))
    emp_co = (ContactEmployment.objects.filter(contact__user=user)
              .values_list('company_id', flat=True))
    app_co = (Application.objects.filter(user=user)
              .values_list('job__company_id', flat=True))
    return set(contact_co) | set(emp_co) | set(app_co)


def _contacts_at(user, company: Company):
    return (Contact.objects
            .filter(user=user)
            .filter(Q(company=company) | Q(employments__company=company))
            .distinct())


def company_summary(user, company: Company) -> dict:
    contacts = _contacts_at(user, company)
    jobs = JobPosting.objects.filter(company=company)
    apps = Application.objects.filter(user=user, job__company=company)
    return {
        'id': company.id,
        'name': company.name,
        'domain': company.domain,
        'careers_url': company.careers_url,
        'ats_type': company.ats_type,
        'contact_count': contacts.count(),
        'job_count': jobs.count(),
        'application_count': apps.count(),
    }


def company_detail(user, company: Company) -> dict:
    contacts = _contacts_at(user, company).order_by('-relationship_strength', 'name')
    jobs = JobPosting.objects.filter(company=company).order_by('-first_seen_at')[:50]
    apps = (Application.objects.filter(user=user, job__company=company)
            .select_related('job').order_by('-updated_at'))
    intros = warm_intros_to_company(user=user, company=company, max_hops=2, limit=5)
    return {
        'id': company.id,
        'name': company.name,
        'domain': company.domain,
        'careers_url': company.careers_url,
        'ats_type': company.ats_type,
        'description': company.description,
        'counts': {
            'contacts': contacts.count(),
            'jobs': jobs.count() if len(jobs) < 50 else JobPosting.objects.filter(company=company).count(),
            'applications': apps.count(),
        },
        'contacts': [{
            'id': c.id,
            'name': c.name,
            'title': c.title,
            'relationship_strength': c.relationship_strength,
            'profile_url': c.profile_url,
        } for c in contacts],
        'jobs': [{
            'id': j.id,
            'title': j.title,
            'location': j.location,
            'remote': j.remote,
            'apply_url': j.apply_url,
        } for j in jobs],
        'applications': [{
            'id': a.id,
            'status': a.status,
            'job_id': a.job_id,
            'job_title': a.job.title,
            'next_action': a.next_action,
            'follow_up_on': a.follow_up_on,
        } for a in apps],
        'warm_intros': intros,
    }


def company_list(user) -> list[dict]:
    ids = relevant_company_ids(user)
    companies = Company.objects.filter(id__in=ids)
    data = [company_summary(user, co) for co in companies]
    data.sort(key=lambda d: (-d['contact_count'], -d['application_count'], d['name'].lower()))
    return data
