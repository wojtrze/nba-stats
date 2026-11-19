import numpy as np
import pandas as pd
import pytest

import backtest  # noqa: F401  (puts dashboard/ on the path)
from absence_window import signal_rows
from backtest.absence_shift import evaluate, scored

T = lambda day, h: pd.Timestamp(f'2026-11-{day:02d}', tz='UTC') + pd.Timedelta(hours=h)
STAR, MATE = 1, 2


def logs():
    """lal's games Nov 1–20: the star sits Nov 5–8; the mate grabs 14 boards without him, 10 with him."""
    rows = []
    for day in range(1, 21):
        sits = day in (5, 6, 7, 8, 18, 20)
        for pid, reb in ((STAR, 12), (MATE, 14 if sits else 10)):
            if pid == STAR and sits:
                continue
            rows.append({'player_id_ESPN': pid, 'team': 'lal', 'Date': pd.Timestamp(f'2026-11-{day:02d}'),
                         'game_id': f'g{day}', 'season_id': 2026, 'MIN': 30, 'REB': reb, 'PTS': 10, 'AST': 2})
    return pd.DataFrame(rows).astype({'player_id_ESPN': 'Int64'})


def offered(day):
    return pd.DataFrame([{'at': T(day, h), 'event_id': f'e{day}', 'tip': T(day, 23), 'name_ESPN': 'Mate',
                          'player_id_ESPN': MATE, 'bet_type': 'REB', 'line': 11.5, 'over_odds': 1.9,
                          'under_odds': 1.9, 'source': 'schedule'} for h in (10, 12)]).astype({'player_id_ESPN': 'Int64'})


def out(day):
    return pd.DataFrame([{'night': pd.Timestamp(f'2026-11-{day:02d}'), 'team': 'lal', 'player_id_ESPN': STAR,
                          'name': 'Star', 'since': T(day, 9), 'game_no': 1, 'now_ques': False}])


def test_the_rule_is_judged_on_the_nights_after_d_and_described_before():
    every = offered(18), offered(20)
    rows = pd.concat([signal_rows(pd.Timestamp(f'2026-11-{d}'), out(d), o, logs()[logs()['Date'] < f'2026-11-{d}'],
                                  {STAR: 'lal', MATE: 'lal'}) for d, o in zip((18, 20), every)], ignore_index=True)
    result = evaluate(rows, pd.concat(every, ignore_index=True), logs(), d='2026-11-19')
    for period in ('recognition', 'evaluation'):
        r = result[f'{period} · all']
        assert r['nights'] == 1 and r['signals'] == 1 and r['won %'] == 100       # Over 11.5, he had 14
        assert r['won − price pp'] == pytest.approx(50)
        assert result[f'{period} · first game']['signals'] == 1


def test_scored_reports_won_over_price_and_roi_after_tax():
    s = pd.DataFrame({'won': [1.0, 0.0], 'price': [0.5, 0.5], 'odds': [2.0, 2.0], 'night': ['a', 'b']})
    r = scored(s)
    assert r['won − price pp'] == pytest.approx(0) and r['ROI after tax %'] == pytest.approx(100 * (0.76 - 1) / 2)
    assert scored(s.iloc[0:0])["lines"] == 0 and r["low"] <= 0 <= r["high"]
