from datetime import timedelta

from django.utils import timezone

from jobs.ghost import (
    HIGH_BAND, assess_ghost_risk, band_for, content_fingerprint,
)


def _assess(**overrides):
    base = dict(
        title='Backend Engineer',
        description='Build resilient services.',
        salary_min=120000,
        salary_max=160000,
        first_seen_at=timezone.now(),
        repost_count=0,
    )
    base.update(overrides)
    return assess_ghost_risk(**base)


def test_fresh_salaried_posting_is_low_risk():
    result = _assess()
    assert result['score'] == 0
    assert result['band'] == 'low'
    assert result['reasons'] == []


def test_fingerprint_is_stable_across_html_and_whitespace_noise():
    a = content_fingerprint('Backend Engineer', '<p>Build   services.</p>', 100, 200)
    b = content_fingerprint('backend engineer', 'Build services.', 100, 200)
    assert a == b
    # changing the salary band changes the fingerprint
    assert content_fingerprint('Backend Engineer', 'Build services.', 100, 200) != \
        content_fingerprint('Backend Engineer', 'Build services.', 100, 300)


def test_missing_salary_adds_risk():
    result = _assess(salary_min=None, salary_max=None)
    assert result['score'] == 20
    assert any('salary' in r.lower() for r in result['reasons'])


def test_stale_then_very_stale_copy_escalates():
    now = timezone.now()
    stale = _assess(first_seen_at=now - timedelta(days=50), now=now)
    very_stale = _assess(first_seen_at=now - timedelta(days=70), now=now)
    assert stale['score'] == 25
    assert very_stale['score'] == 40
    assert any('over 60' in r for r in very_stale['reasons'])


def test_repost_cycle_adds_risk():
    result = _assess(repost_count=2)
    assert result['score'] == 30
    assert any('reposted 2x' in r.lower() for r in result['reasons'])


def test_evergreen_language_flagged():
    result = _assess(description='Join our talent pool for future opportunities!')
    assert result['score'] >= 25
    assert any('evergreen' in r.lower() for r in result['reasons'])


def test_red_flag_language_flagged():
    result = _assess(description='We need a rockstar ninja who thrives under pressure.')
    assert any('red-flag' in r.lower() for r in result['reasons'])


def test_score_caps_at_100_and_band_is_high():
    now = timezone.now()
    result = _assess(
        first_seen_at=now - timedelta(days=90),
        now=now,
        salary_min=None,
        salary_max=None,
        repost_count=3,
        description='Evergreen talent pool, always hiring rockstar ninjas, work hard play hard.',
    )
    assert result['score'] == 100
    assert result['band'] == 'high'


def test_band_thresholds():
    assert band_for(0) == 'low'
    assert band_for(MEDIUM := 30) == 'medium' and MEDIUM
    assert band_for(HIGH_BAND) == 'high'
    assert band_for(HIGH_BAND - 1) == 'medium'
