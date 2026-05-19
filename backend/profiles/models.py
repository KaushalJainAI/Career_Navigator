from django.conf import settings
from django.db import models


class StructuredProfile(models.Model):
    """Detailed user profile collected via the natural-language onboarding chat."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='structured_profile'
    )
    full_name = models.CharField(max_length=255, blank=True)
    headline = models.CharField(max_length=255, blank=True)
    summary = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=64, blank=True)
    website = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    github = models.URLField(blank=True)
    onboarding_complete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f'Profile of {self.user}'


class Experience(models.Model):
    profile = models.ForeignKey(StructuredProfile, on_delete=models.CASCADE, related_name='experiences')
    company = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    bullets = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-start_date']


class Education(models.Model):
    profile = models.ForeignKey(StructuredProfile, on_delete=models.CASCADE, related_name='educations')
    institution = models.CharField(max_length=255)
    degree = models.CharField(max_length=255, blank=True)
    field_of_study = models.CharField(max_length=255, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    gpa = models.CharField(max_length=16, blank=True)


class Skill(models.Model):
    profile = models.ForeignKey(StructuredProfile, on_delete=models.CASCADE, related_name='skills')
    name = models.CharField(max_length=128)
    proficiency = models.CharField(max_length=32, blank=True)
    years = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = [('profile', 'name')]


class Project(models.Model):
    profile = models.ForeignKey(StructuredProfile, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    url = models.URLField(blank=True)
    tech_stack = models.JSONField(default=list, blank=True)


class Preference(models.Model):
    """Search preferences driving alerts and matching."""

    profile = models.OneToOneField(StructuredProfile, on_delete=models.CASCADE, related_name='preference')
    target_titles = models.JSONField(default=list, blank=True)
    locations = models.JSONField(default=list, blank=True)
    remote = models.BooleanField(default=True)
    salary_min = models.IntegerField(null=True, blank=True)
    seniority = models.CharField(max_length=32, blank=True)
    keywords = models.JSONField(default=list, blank=True)
    exclude_companies = models.JSONField(default=list, blank=True)
    work_auth = models.CharField(max_length=64, blank=True)
    stealth_mode = models.BooleanField(default=False)
