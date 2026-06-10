import pytest

from agent.models import AgentSession
from agent.onboarding import extract_onboarding_facts
from profiles.models import Skill, StructuredProfile

pytestmark = pytest.mark.django_db


def test_extract_onboarding_facts_from_natural_language():
    out = extract_onboarding_facts(
        'My name is Alice Patel and I am based in Pune. '
        'I work as Backend Engineer. Skills: Python, Django and React. '
        'github https://github.com/alice linkedin https://linkedin.com/in/alice'
    )

    assert out.fields['full_name'] == 'Alice Patel'
    assert out.fields['location'] == 'Pune'
    assert out.fields['headline'] == 'Backend Engineer'
    assert out.fields['github'] == 'https://github.com/alice'
    assert out.fields['linkedin'] == 'https://linkedin.com/in/alice'
    assert out.skills == ['Python', 'Django', 'React']


def test_onboarding_chat_updates_profile_and_returns_reply(auth_client, user):
    session = AgentSession.objects.create(user=user, kind='onboarding')

    response = auth_client.post(
        f'/api/v1/agent/sessions/{session.id}/chat/',
        {'message': 'My name is Alice Patel. I live in Bengaluru. Skills: Python, Django.'},
        format='json',
    )

    assert response.status_code == 200
    assert response.data['halt'] is True
    assert response.data['reply'].startswith('Saved:')

    profile = StructuredProfile.objects.get(user=user)
    assert profile.full_name == 'Alice Patel'
    assert profile.location == 'Bengaluru'
    assert set(Skill.objects.filter(profile=profile).values_list('name', flat=True)) == {'Python', 'Django'}

    session.refresh_from_db()
    assert session.state['last_onboarding_result']['profile']['full_name'] == 'Alice Patel'
