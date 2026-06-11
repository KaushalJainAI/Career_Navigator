from django.db import models
from django.utils import timezone


class ATSType(models.TextChoices):
    GREENHOUSE = 'greenhouse', 'Greenhouse'
    LEVER = 'lever', 'Lever'
    WORKDAY = 'workday', 'Workday'
    SMARTRECRUITERS = 'smartrecruiters', 'SmartRecruiters'
    OTHER = 'other', 'Other'


class Company(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    domain = models.CharField(max_length=255, blank=True, db_index=True)
    ats_type = models.CharField(max_length=32, choices=ATSType.choices, default=ATSType.OTHER)
    careers_url = models.URLField(blank=True)
    description = models.TextField(blank=True)

    class Meta:
        unique_together = [('name', 'domain')]

    def __str__(self) -> str:
        return self.name


class Source(models.Model):
    """A configured job-discovery source: an API, a scraper, an email forward, etc."""

    KIND_CHOICES = [
        ('aggregator', 'Aggregator API'),
        ('ats_public', 'Public ATS board'),
        ('scraper', 'Custom scraper'),
        ('email_forward', 'Email forward'),
        ('web_search', 'Web search'),
        ('cli_delegate', 'CLI delegate'),
        ('linkedin', 'LinkedIn (best-effort)'),
    ]

    name = models.CharField(max_length=128, unique=True)
    kind = models.CharField(max_length=32, choices=KIND_CHOICES)
    config = models.JSONField(default=dict, blank=True)
    enabled = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f'{self.name} ({self.kind})'


class JobPosting(models.Model):
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name='jobs')
    external_id = models.CharField(max_length=255, db_index=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='jobs')
    title = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True, db_index=True)
    remote = models.BooleanField(default=False)
    salary_min = models.IntegerField(null=True, blank=True)
    salary_max = models.IntegerField(null=True, blank=True)
    salary_currency = models.CharField(max_length=8, blank=True)
    apply_url = models.URLField(blank=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    raw = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Ghost-Job Shield: liveness + repost tracking and the derived risk score.
    # first_seen_at is the moment we first saw THIS copy (resets when the JD
    # text/salary changes); last_seen_at is the most recent ingestion run that
    # still carried it; content_fingerprint detects unchanged-copy reposts.
    first_seen_at = models.DateTimeField(default=timezone.now, db_index=True)
    last_seen_at = models.DateTimeField(default=timezone.now)
    content_fingerprint = models.CharField(max_length=64, blank=True, db_index=True)
    repost_count = models.PositiveIntegerField(default=0)
    ghost_risk = models.PositiveSmallIntegerField(default=0, db_index=True)
    ghost_reasons = models.JSONField(default=list, blank=True)

    class Meta:
        unique_together = [('source', 'external_id')]
        ordering = ['-posted_at', '-created_at']

    def __str__(self) -> str:
        return f'{self.title} @ {self.company}'
