from rest_framework import serializers

from .models import (
    ActionQueueItem,
    CompanyRelationship,
    Contact,
    ContactEmployment,
    ContactRelationship,
    OutreachMessage,
    ReferralOpportunity,
    UserConsentEvent,
)


class ContactSerializer(serializers.ModelSerializer):
    # Read the linked company's name for display; accept a `company_name` on write
    # and get_or_create the Company so the UI can just type a name.
    company_name = serializers.SerializerMethodField()

    class Meta:
        model = Contact
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'updated_at']

    def get_company_name(self, obj):
        return obj.company.name if obj.company_id else ''

    def _apply_company(self, validated_data):
        name = (self.initial_data.get('company_name') or '').strip() if hasattr(self, 'initial_data') else ''
        if name:
            from jobs.models import Company
            validated_data['company'] = Company.objects.get_or_create(name=name)[0]
        return validated_data

    def create(self, validated_data):
        return super().create(self._apply_company(validated_data))

    def update(self, instance, validated_data):
        return super().update(instance, self._apply_company(validated_data))


class ReferralOpportunitySerializer(serializers.ModelSerializer):
    contact = ContactSerializer(read_only=True)
    contact_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = ReferralOpportunity
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'updated_at']


class OutreachMessageSerializer(serializers.ModelSerializer):
    contact = ContactSerializer(read_only=True)

    class Meta:
        model = OutreachMessage
        fields = '__all__'
        read_only_fields = [
            'user',
            'approved_body',
            'payload_hash',
            'status',
            'sent_at',
            'created_at',
            'updated_at',
        ]


class OutreachApprovalSerializer(serializers.Serializer):
    approved_body = serializers.CharField(required=False, allow_blank=False)


class UserConsentEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserConsentEvent
        fields = ['id', 'action_type', 'target_type', 'target_id', 'expires_at', 'created_at']


class ActionQueueItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionQueueItem
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'updated_at']


class ContactEmploymentSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = ContactEmployment
        fields = ['id', 'contact', 'company', 'company_name', 'title',
                  'started_at', 'ended_at', 'is_current', 'source', 'raw',
                  'created_at', 'updated_at']
        read_only_fields = ['contact', 'created_at', 'updated_at', 'company_name']


class ContactRelationshipSerializer(serializers.ModelSerializer):
    from_contact_name = serializers.CharField(source='from_contact.name', read_only=True)
    to_contact_name = serializers.CharField(source='to_contact.name', read_only=True)

    class Meta:
        model = ContactRelationship
        fields = ['id', 'from_contact', 'to_contact', 'from_contact_name',
                  'to_contact_name', 'kind', 'strength', 'inferred', 'notes',
                  'created_at']
        read_only_fields = ['user', 'from_contact', 'created_at', 'inferred',
                            'from_contact_name', 'to_contact_name']


class CompanyRelationshipSerializer(serializers.ModelSerializer):
    from_company_name = serializers.CharField(source='from_company.name', read_only=True)
    to_company_name = serializers.CharField(source='to_company.name', read_only=True)

    class Meta:
        model = CompanyRelationship
        fields = ['id', 'from_company', 'to_company', 'from_company_name',
                  'to_company_name', 'kind', 'effective_date', 'source_url',
                  'notes', 'created_at']
        read_only_fields = ['from_company', 'created_at', 'from_company_name', 'to_company_name']
