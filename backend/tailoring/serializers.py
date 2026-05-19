from rest_framework import serializers

from .models import CoverLetter, TailoredResume


class TailoredResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TailoredResume
        fields = '__all__'


class CoverLetterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoverLetter
        fields = '__all__'
