from rest_framework import serializers

from .models import Resume


class ResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = [
            'id', 'label', 'file', 'parsed_json', 'parse_status', 'parse_error',
            'is_master', 'created_at', 'updated_at',
        ]
        read_only_fields = ['parsed_json', 'parse_status', 'parse_error', 'created_at', 'updated_at']
