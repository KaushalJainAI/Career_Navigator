"""DRF serializers for the MV3 browser-extension endpoints."""

from rest_framework import serializers


class CompanyPayloadSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, allow_blank=True, required=False, default='')
    domain = serializers.CharField(max_length=255, allow_blank=True, required=False, default='')
    ats_type = serializers.CharField(max_length=32, required=False, default='other')


class PageContextSerializer(serializers.Serializer):
    """Body of POST /api/v1/ext/page-context/.
    Shape matches the normalised posting dict consumed by ingestion.services.upsert_postings."""

    parser = serializers.ChoiceField(choices=[
        'linkedin', 'greenhouse', 'lever',
        'naukri', 'unstop', 'mercor',
    ])
    external_id = serializers.CharField(max_length=512)
    title = serializers.CharField(max_length=512)
    description = serializers.CharField(allow_blank=True, required=False, default='')
    location = serializers.CharField(max_length=255, allow_blank=True, required=False, default='')
    remote = serializers.BooleanField(required=False, default=False)
    salary_min = serializers.IntegerField(required=False, allow_null=True)
    salary_max = serializers.IntegerField(required=False, allow_null=True)
    salary_currency = serializers.CharField(max_length=8, allow_blank=True, required=False, default='')
    apply_url = serializers.CharField(required=False, allow_blank=True, default='')
    company = CompanyPayloadSerializer()
    raw = serializers.DictField(required=False, default=dict)


class SubmitEventSerializer(serializers.Serializer):
    """Body of POST /api/v1/ext/submit-event/."""

    job_id = serializers.IntegerField()
    status = serializers.CharField(max_length=24, required=False, default='applied')
    tier = serializers.CharField(max_length=24, required=False, default='autofill')
    field_values = serializers.DictField(required=False, default=dict)
    parser = serializers.CharField(max_length=32, required=False, allow_blank=True, default='')
    parser_version = serializers.CharField(max_length=32, required=False, allow_blank=True, default='')
    url = serializers.CharField(required=False, allow_blank=True, default='')


class ProfileExperienceSerializer(serializers.Serializer):
    company_name = serializers.CharField(max_length=255)
    company_domain = serializers.CharField(max_length=255, allow_blank=True, required=False, default='')
    title = serializers.CharField(max_length=255, allow_blank=True, required=False, default='')
    started_at = serializers.DateField(required=False, allow_null=True)
    ended_at = serializers.DateField(required=False, allow_null=True)
    is_current = serializers.BooleanField(required=False, default=False)
    raw = serializers.DictField(required=False, default=dict)


class ProfileContextSerializer(serializers.Serializer):
    """Body of POST /api/v1/ext/profile-context/. Captured from linkedin.com/in/*."""

    profile_url = serializers.URLField()
    name = serializers.CharField(max_length=255)
    headline = serializers.CharField(allow_blank=True, required=False, default='')
    location = serializers.CharField(max_length=255, allow_blank=True, required=False, default='')
    email = serializers.EmailField(required=False, allow_blank=True)
    experiences = ProfileExperienceSerializer(many=True, required=False, default=list)
    raw = serializers.DictField(required=False, default=dict)
