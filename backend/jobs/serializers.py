from rest_framework import serializers

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

    class Meta:
        model = JobPosting
        fields = '__all__'
