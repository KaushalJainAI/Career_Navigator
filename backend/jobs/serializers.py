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

    class Meta:
        model = JobPosting
        fields = '__all__'

    def get_ghost_band(self, obj) -> str:
        return band_for(obj.ghost_risk)
