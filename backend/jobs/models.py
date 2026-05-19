from django.db import models


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

    class Meta:
        unique_together = [('source', 'external_id')]
        ordering = ['-posted_at', '-created_at']

    def __str__(self) -> str:
        return f'{self.title} @ {self.company}'
