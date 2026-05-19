import pytest

from profiles.models import (
    Education,
    Experience,
    Preference,
    Project,
    Skill,
    StructuredProfile,
)

pytestmark = pytest.mark.django_db


def test_profile_create_and_related(user):
    profile = StructuredProfile.objects.create(user=user, full_name='Alice')
    Experience.objects.create(profile=profile, company='Acme', title='Engineer')
    Education.objects.create(profile=profile, institution='State U')
    Skill.objects.create(profile=profile, name='Python', proficiency='expert')
    Project.objects.create(profile=profile, name='Demo')
    Preference.objects.create(profile=profile, target_titles=['Senior Engineer'], remote=True)

    assert profile.experiences.count() == 1
    assert profile.educations.count() == 1
    assert profile.skills.count() == 1
    assert profile.projects.count() == 1
    assert profile.preference.target_titles == ['Senior Engineer']


def test_skill_unique_per_profile(user):
    profile = StructuredProfile.objects.create(user=user)
    Skill.objects.create(profile=profile, name='Python')
    with pytest.raises(Exception):
        Skill.objects.create(profile=profile, name='Python')
