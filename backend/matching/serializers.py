from rest_framework import serializers

from .models import MatchScore


class MatchScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = MatchScore
        fields = '__all__'
