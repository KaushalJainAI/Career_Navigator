from rest_framework import serializers

from .models import (
    Certification,
    Education,
    Experience,
    Language,
    Preference,
    Project,
    Skill,
    StructuredProfile,
)


class ExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experience
        exclude = ['profile']


class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        exclude = ['profile']


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        exclude = ['profile']


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        exclude = ['profile']


class CertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certification
        exclude = ['profile']


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        exclude = ['profile']


class PreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Preference
        exclude = ['profile']


class StructuredProfileSerializer(serializers.ModelSerializer):
    experiences = ExperienceSerializer(many=True, required=False)
    educations = EducationSerializer(many=True, required=False)
    skills = SkillSerializer(many=True, required=False)
    projects = ProjectSerializer(many=True, required=False)
    certifications = CertificationSerializer(many=True, required=False)
    languages = LanguageSerializer(many=True, required=False)
    preference = PreferenceSerializer(required=False)
    readiness = serializers.SerializerMethodField()

    class Meta:
        model = StructuredProfile
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'updated_at']

    def get_readiness(self, instance):
        checks = {
            'name': bool(instance.full_name),
            'headline': bool(instance.headline),
            'location': bool(instance.location),
            'skills': instance.skills.exists(),
            'experience': instance.experiences.exists(),
            'preferences': hasattr(instance, 'preference'),
        }
        complete_count = sum(1 for ok in checks.values() if ok)
        return {
            'checks': checks,
            'score': round(complete_count / len(checks), 4),
            'missing': [name for name, ok in checks.items() if not ok],
            'ready': complete_count >= 4,
        }

    # Each related list is a *full replacement* of the existing rows: omit a key
    # to leave it untouched, send a list (possibly empty) to overwrite it. This
    # keeps the profile form a single PATCH instead of N sub-resource endpoints.
    _RELATED = {
        'experiences': Experience,
        'educations': Education,
        'skills': Skill,
        'projects': Project,
        'certifications': Certification,
        'languages': Language,
    }

    def update(self, instance, validated_data):
        related = {
            name: validated_data.pop(name, None) for name in self._RELATED
        }
        preference_data = validated_data.pop('preference', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        for name, items in related.items():
            if items is None:
                continue
            getattr(instance, name).all().delete()
            model = self._RELATED[name]
            model.objects.bulk_create([model(profile=instance, **item) for item in items])

        if preference_data is not None:
            Preference.objects.update_or_create(profile=instance, defaults=preference_data)

        instance.refresh_from_db()
        return instance
