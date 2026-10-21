from datetime import datetime, timedelta, timezone

from core.freshness import age_text, live_status, stats_status

# 2026-10-21 15:00 UTC = 11:00 US Eastern, so "yesterday" in ET is Oct 20
NOW = datetime(2026, 10, 21, 15, 0, tzinfo=timezone.utc)


def test_stats_ok_when_stored_through_yesterday_et():
    assert stats_status('2026-10-20', NOW)['level'] == 'ok'
    assert stats_status('2026-10-21', NOW)['level'] == 'ok'


def test_stats_stale_and_missing():
    stale = stats_status('2026-10-18', NOW)
    assert stale['level'] == 'stale' and '2 days' in stale['detail']
    assert stats_status(None, NOW)['level'] == 'missing'


def test_stats_yesterday_follows_eastern_time():
    # 03:00 UTC on Oct 21 is still Oct 20 in New York: yesterday = Oct 19
    early = datetime(2026, 10, 21, 3, 0, tzinfo=timezone.utc)
    assert stats_status('2026-10-19', early)['level'] == 'ok'


def test_live_status_levels():
    assert live_status(True, NOW - timedelta(minutes=5), 120, NOW, 'lines')['level'] == 'ok'
    assert live_status(True, NOW - timedelta(hours=4), 120, NOW, 'lines')['level'] == 'stale'   # an old fetch
    fallback = live_status(False, NOW - timedelta(hours=5), 120, NOW, 'lines')
    assert fallback['level'] == 'stale' and "couldn't be reached" in fallback['detail']
    assert live_status(None, NOW - timedelta(hours=1), None, NOW, 'lines')['level'] == 'ok'
    assert live_status(None, None, None, NOW, 'lines')['level'] == 'missing'


def test_age_text():
    assert age_text(timedelta(seconds=20)) == "just now"
    assert age_text(timedelta(minutes=42)) == "42 min ago"
    assert age_text(timedelta(hours=5)) == "5 h ago"
    assert age_text(timedelta(days=3)) == "3 days ago"
