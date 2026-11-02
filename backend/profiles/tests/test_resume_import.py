from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile

from profiles.models import Skill, StructuredProfile

FIX = Path(__file__).resolve().parents[2] / 'resumes' / 'tests' / 'fixtures' / 'backend_engineer.txt'


def test_upload_fills_profile_and_becomes_master(auth_client, user):
    upload = SimpleUploadedFile('cv.txt', FIX.read_bytes(), content_type='text/plain')
    r = auth_client.post('/api/v1/resumes/', {'file': upload, 'label': 'CV'}, format='multipart')
    assert r.status_code == 201, r.content
    assert r.data['is_master'] is True
    assert 'experiences' in r.data['profile_update']['changed']
    profile = StructuredProfile.objects.get(user=user)
    assert profile.full_name == 'Priya Sharma'
    assert profile.experiences.count() == 2
    assert profile.preference.target_titles == ['Senior Backend Engineer']
    assert Skill.objects.filter(profile=profile, name='Kafka').exists()


def test_import_text_does_not_clobber_user_edits(auth_client, user):
    profile = StructuredProfile.objects.create(user=user, full_name='Priya S.')
    r = auth_client.post('/api/v1/resumes/import-text/', {'text': FIX.read_text()}, format='json')
    assert r.status_code == 201
    profile.refresh_from_db()
    assert profile.full_name == 'Priya S.'  # kept
    assert profile.headline == 'Senior Backend Engineer'  # filled


def test_import_text_rejects_tiny_input(auth_client):
    r = auth_client.post('/api/v1/resumes/import-text/', {'text': 'hi'}, format='json')
    assert r.status_code == 400


def test_make_master_with_overwrite(auth_client, user):
    StructuredProfile.objects.create(user=user, full_name='Old Name')
    r = auth_client.post('/api/v1/resumes/import-text/', {'text': FIX.read_text()}, format='json')
    rid = r.data['id']
    r = auth_client.post(f'/api/v1/resumes/{rid}/make-master/', {'overwrite_profile': True}, format='json')
    assert r.status_code == 200
    assert StructuredProfile.objects.get(user=user).full_name == 'Priya Sharma'
