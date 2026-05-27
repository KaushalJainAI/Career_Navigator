import hashlib

from django.conf import settings
from django.db import models
from django.utils import timezone

from jobs.models import Company, JobPosting


class ContactSource(models.TextChoices):
    MANUAL = 'manual', 'Manual'
    CSV = 'csv', 'CSV import'
    GOOGLE = 'google', 'Google Contacts'
    PROFILE_URL = 'profile_url', 'User-provided profile URL'
    PUBLIC_PAGE = 'public_page', 'Public page'


class OutreachChannel(models.TextChoices):
    EMAIL = 'email', 'Email'
    LINKEDIN = 'linkedin', 'LinkedIn'
    X = 'x', 'X / Twitter'
    REFERRAL_FORM = 'referral_form', 'Referral form'
    MANUAL = 'manual', 'Manual'


class MessageStatus(models.TextChoices):
    DRAFTED = 'drafted', 'Drafted'
    APPROVED = 'approved', 'Approved'
    SENT = 'sent', 'Sent'
    REPLIED = 'replied', 'Replied'
    FOLLOW_UP_DUE = 'follow_up_due', 'Follow-up due'
    CLOSED = 'closed', 'Closed'


class ReferralStatus(models.TextChoices):
    SUGGESTED = 'suggested', 'Suggested'
    CONTACTED = 'contacted', 'Contacted'
    REFERRED = 'referred', 'Referred'
    DECLINED = 'declined', 'Declined'
    CLOSED = 'closed', 'Closed'


class ActionStatus(models.TextChoices):
    OPEN = 'open', 'Open'
    DONE = 'done', 'Done'
    DISMISSED = 'dismissed', 'Dismissed'


class ConsentAction(models.TextChoices):
    SEND_OUTREACH = 'send_outreach', 'Send outreach'
    SUBMIT_APPLICATION = 'submit_application', 'Submit application'
    USE_CREDENTIALS = 'use_credentials', 'Use credentials'


class Contact(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='contacts')
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='contacts')
    name = models.CharField(max_length=255)
    title = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    profile_url = models.URLField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    source = models.CharField(max_length=32, choices=ContactSource.choices, default=ContactSource.MANUAL)
    seniority = models.CharField(max_length=64, blank=True)
    relationship_strength = models.PositiveSmallIntegerField(default=0)
    notes = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    raw = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['user', 'name']),
            models.Index(fields=['user', 'email']),
        ]

    def __str__(self) -> str:
        return self.name


class ReferralOpportunity(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='referral_opportunities')
    job = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='referral_opportunities')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='referral_opportunities')
    score = models.PositiveSmallIntegerField(default=0)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=32, choices=ReferralStatus.choices,
                              default=ReferralStatus.SUGGESTED)
    next_action = models.CharField(max_length=255, blank=True)
    last_interaction_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('user', 'job', 'contact')]
        ordering = ['-score', '-updated_at']


class OutreachMessage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='outreach_messages')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='outreach_messages')
    job = models.ForeignKey(JobPosting, on_delete=models.SET_NULL, null=True, blank=True,
                            related_name='outreach_messages')
    channel = models.CharField(max_length=32, choices=OutreachChannel.choices, default=OutreachChannel.MANUAL)
    subject = models.CharField(max_length=255, blank=True)
    draft_body = models.TextField()
    approved_body = models.TextField(blank=True)
    payload_hash = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=32, choices=MessageStatus.choices, default=MessageStatus.DRAFTED)
    sent_at = models.DateTimeField(null=True, blank=True)
    follow_up_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def approve(self, body: str | None = None) -> str:
        self.approved_body = body if body is not None else self.draft_body
        self.payload_hash = hashlib.sha256(
            f'{self.contact_id}:{self.job_id}:{self.channel}:{self.approved_body}'.encode()
        ).hexdigest()
        self.status = MessageStatus.APPROVED
        self.save(update_fields=['approved_body', 'payload_hash', 'status', 'updated_at'])
        return self.payload_hash


class ActionQueueItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='action_queue_items')
    action_type = models.CharField(max_length=64)
    title = models.CharField(max_length=255)
    priority = models.PositiveSmallIntegerField(default=50)
    due_at = models.DateTimeField(null=True, blank=True)
    job = models.ForeignKey(JobPosting, on_delete=models.SET_NULL, null=True, blank=True,
                            related_name='action_queue_items')
    contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='action_queue_items')
    status = models.CharField(max_length=32, choices=ActionStatus.choices, default=ActionStatus.OPEN)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['status', 'due_at', '-priority', '-created_at']


class ContactEmployment(models.Model):
    """A contact's employment at a company over a time range.
    The row with `is_current=True` (or `ended_at IS NULL`) is the contact's current job."""

    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='employments')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='employments')
    title = models.CharField(max_length=255, blank=True)
    started_at = models.DateField(null=True, blank=True)
    ended_at = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    source = models.CharField(max_length=32, choices=ContactSource.choices, default=ContactSource.MANUAL)
    raw = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['contact', '-started_at']),
            models.Index(fields=['company', 'is_current']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['contact', 'company', 'title', 'started_at'],
                name='uniq_contact_employment',
            ),
        ]
        ordering = ['-is_current', '-started_at']

    def overlaps(self, other: 'ContactEmployment') -> bool:
        """Date-range overlap, treating None as 'open at that end'."""
        if self.company_id != other.company_id:
            return False
        a_start = self.started_at
        a_end = self.ended_at
        b_start = other.started_at
        b_end = other.ended_at
        if a_start and b_end and a_start > b_end:
            return False
        if b_start and a_end and b_start > a_end:
            return False
        return True


class ContactRelationshipKind(models.TextChoices):
    COLLEAGUE = 'colleague', 'Colleague (overlapping employment)'
    MANAGER = 'manager', 'Manager / report-to'
    REPORT = 'report', 'Direct report'
    REFERENCE = 'reference', 'Professional reference'
    MUTUAL = 'mutual', 'Mutual connection'
    CLASSMATE = 'classmate', 'Classmate'
    FRIEND = 'friend', 'Friend'


class ContactRelationship(models.Model):
    """Directed edge between two contacts in the user's network.
    Bidirectional kinds (colleague, mutual, friend) are stored as two rows."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='contact_relationships')
    from_contact = models.ForeignKey(Contact, on_delete=models.CASCADE,
                                     related_name='outgoing_relationships')
    to_contact = models.ForeignKey(Contact, on_delete=models.CASCADE,
                                   related_name='incoming_relationships')
    kind = models.CharField(max_length=32, choices=ContactRelationshipKind.choices)
    strength = models.PositiveSmallIntegerField(default=3)
    inferred = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('user', 'from_contact', 'to_contact', 'kind')]
        indexes = [
            models.Index(fields=['user', 'from_contact']),
            models.Index(fields=['user', 'to_contact']),
        ]


class CompanyRelationshipKind(models.TextChoices):
    ACQUIRED = 'acquired', 'Acquired by'
    PARENT = 'parent', 'Parent of'
    SUBSIDIARY = 'subsidiary', 'Subsidiary of'
    SPINOFF = 'spinoff', 'Spinoff from'
    COMPETITOR = 'competitor', 'Competitor of'
    PARTNER = 'partner', 'Partner of'


class CompanyRelationship(models.Model):
    """Directed edge between companies. Global, not per-user."""

    from_company = models.ForeignKey(Company, on_delete=models.CASCADE,
                                     related_name='outgoing_company_rels')
    to_company = models.ForeignKey(Company, on_delete=models.CASCADE,
                                   related_name='incoming_company_rels')
    kind = models.CharField(max_length=32, choices=CompanyRelationshipKind.choices)
    effective_date = models.DateField(null=True, blank=True)
    source_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('from_company', 'to_company', 'kind')]


class UserConsentEvent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='consent_events')
    action_type = models.CharField(max_length=64, choices=ConsentAction.choices)
    target_type = models.CharField(max_length=64)
    target_id = models.PositiveBigIntegerField()
    payload_hash = models.CharField(max_length=64)
    approval_token = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def is_valid(self) -> bool:
        return self.used_at is None and self.expires_at > timezone.now()
