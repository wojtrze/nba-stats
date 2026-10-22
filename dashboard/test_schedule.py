"""Run with: python -m pytest dashboard"""
from datetime import date, datetime, timezone

import pandas as pd

from schedule import nights_text, no_offers_text, offers_status, starts_soon, tip_label, upcoming

NOW = datetime(2026, 10, 21, 22, 0, tzinfo=timezone.utc)   # Thu 00:00 in Poland, Wed 18:00 in New York


def _lines(starts, event_ids=None):
    return pd.DataFrame({'event_id': event_ids or list(range(len(starts))), 'start_time': starts,
                         'name': [f"p{i}" for i in range(len(starts))]})


def test_upcoming_drops_started_games_and_sorts_by_tip_off():
    df = _lines(['2026-10-22T02:00:00Z', '2026-10-21T21:00:00Z', '2026-10-21T22:00:00Z', '2026-10-21T23:30:00Z'])
    out = upcoming(df, NOW)
    assert out['name'].tolist() == ['p3', 'p0']        # started (21:00) and starting exactly now (22:00) are out


def test_offers_status_states():
    props = _lines(['2026-10-21T23:00:00Z', '2026-10-22T02:00:00Z'], [1, 2])
    odds = _lines(['2026-10-21T23:00:00Z'], [1])
    fetched = datetime(2026, 10, 21, 11, 0, tzinfo=timezone.utc)
    s = offers_status(props, odds, fetched, NOW)
    assert s['state'] == 'available' and s['games'] == 2 and s['lines'] == 2
    assert s['nights'] == [date(2026, 10, 21)]        # 02:00 UTC on the 22nd is still the 21st in New York
    later = datetime(2026, 10, 22, 3, 0, tzinfo=timezone.utc)
    assert offers_status(props, odds, fetched, later)['state'] == 'all_started'
    empty = pd.DataFrame(columns=['event_id', 'start_time'])
    assert offers_status(empty, empty, None, NOW)['state'] == 'none_saved'
    # game odds only (preseason: no props) still count
    assert offers_status(empty, odds, fetched, NOW)['state'] == 'available'


def test_tip_label_and_starts_soon():
    assert tip_label('2026-10-21T22:59:00Z', NOW) == "⏰ in 59 min (00:59)"
    assert tip_label('2026-10-21T23:01:00Z', NOW) == "Thu 01:01"            # 61 minutes: no mark
    assert starts_soon('2026-10-21T22:30:00Z', NOW) and not starts_soon('2026-10-21T21:30:00Z', NOW)
    # winter time: Polish time is UTC+1 after the last Sunday of October
    assert tip_label('2026-11-02T00:30:00Z', NOW) == "Mon 01:30"


def test_nights_text():
    assert nights_text([date(2026, 10, 21)]) == "Oct 21"
    assert nights_text([date(2026, 10, 21), date(2026, 10, 22)]) == "Oct 21 – Oct 22"
    assert nights_text([]) == ''


def test_no_offers_text():
    status = {'state': 'all_started', 'fetched_at': datetime(2026, 10, 21, 11, 11, tzinfo=timezone.utc),
              'nights': [date(2026, 10, 21)], 'games': 12, 'lines': 2178}
    text = no_offers_text(status, results_stored=False)
    assert "Wed 21 Oct 13:11" in text and "2,178 player lines on 12 games" in text and "night of Oct 21" in text
    assert "pending" in text and "pending" not in no_offers_text(status, results_stored=True)
    assert "Nothing has been fetched" in no_offers_text({'state': 'none_saved'}, False)
