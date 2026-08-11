from uuid import uuid4

from django.utils import timezone
from rest_framework import serializers

from .ghost import band_for
from .models import Company, JobPosting, Source


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'


class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Source
        fields = '__all__'


class JobPostingSerializer(serializers.ModelSerializer):
    company = CompanySerializer(read_only=True)
    source = SourceSerializer(read_only=True)
    ghost_band = serializers.SerializerMethodField()
    has_full_description = serializers.SerializerMethodField()

    class Meta:
        model = JobPosting
        fields = '__all__'

    def get_ghost_band(self, obj) -> str:
        return band_for(obj.ghost_risk)

    def get_has_full_description(self, obj) -> bool:
        """False means the text shown is the source's truncated teaser."""
        return bool(obj.full_description)


class JobPostingWriteSerializer(serializers.ModelSerializer):
    """Create a job by hand (e.g. one the user found elsewhere). Accepts a plain
    company name, files it under a shared 'Manual entry' source, and — since the
    user vouches for it — marks it zero ghost-risk."""

    company_name = serializers.CharField(write_only=True, max_length=255)
    company_domain = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = JobPosting
        fields = [
            'id', 'company_name', 'company_domain', 'title', 'description',
            'location', 'remote', 'salary_min', 'salary_max', 'salary_currency',
            'apply_url', 'posted_at',
        ]
        read_only_fields = ['id']

    def validate_company_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Company name is required.')
        return value

    def create(self, validated_data):
        name = validated_data.pop('company_name')
        domain = (validated_data.pop('company_domain', '') or '').strip()
        source, _ = Source.objects.get_or_create(
            name='Manual entry', defaults={'kind': 'manual'})
        company, _ = Company.objects.get_or_create(name=name, domain=domain)
        validated_data['source'] = source
        validated_data['company'] = company
        validated_data['external_id'] = f'manual-{uuid4().hex}'
        validated_data['ghost_risk'] = 0
        validated_data.setdefault('posted_at', timezone.now())
        return super().create(validated_data)
