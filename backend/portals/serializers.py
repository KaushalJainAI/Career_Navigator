from rest_framework import serializers

from .models import PortalScrapeRun


class PortalScrapeRunSerializer(serializers.ModelSerializer):
    portal = serializers.CharField(source='portal.name', read_only=True)

    class Meta:
        model = PortalScrapeRun
        fields = ['id', 'portal', 'query', 'status', 'stats', 'error', 'started_at', 'finished_at']


class StoreSessionSerializer(serializers.Serializer):
    """Accepts a raw session cookie value or a full Playwright storage_state dict.
    Write-only — the session is never read back out."""

    cookie = serializers.CharField(required=False, allow_blank=True, write_only=True)
    storage_state = serializers.JSONField(required=False, write_only=True)

    def validate(self, attrs):
        if not attrs.get('cookie') and not attrs.get('storage_state'):
            raise serializers.ValidationError('Provide a cookie or a storage_state.')
        return attrs


class ScrapeRequestSerializer(serializers.Serializer):
    keywords = serializers.CharField(required=False, allow_blank=True, default='')
    location = serializers.CharField(required=False, allow_blank=True, default='')
    remote = serializers.BooleanField(required=False, default=False)
    max_results = serializers.IntegerField(required=False, min_value=1, max_value=100, default=25)
