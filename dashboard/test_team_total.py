import numpy as np
import pandas as pd
import pytest

import team_total as tt

NIGHT = pd.Timestamp('2026-11-21')


def ladder(market, mid, step=1.0):
    """A ladder whose margin-free Over chance is 50% at `mid` (over and under odds of each rung, no margin)."""
    rows = []
    for line in (mid - 1.5, mid - 0.5, mid + 0.5, mid + 1.5):
        p = 0.5 - 0.04 * (line - mid) / step
        rows += [{'market': market, 'side': 'over', 'line': line, 'odds': 1 / p},
                 {'market': market, 'side': 'under', 'line': line, 'odds': 1 / (1 - p)}]
    return rows


def test_ladder_median_interpolates_and_extrapolates():
    assert tt.ladder_median([110.5, 111.5], [0.54, 0.46]) == pytest.approx(111.0)
    assert tt.ladder_median([110.5, 111.5], [0.60, 0.55]) == pytest.approx(112.5)
    assert np.isnan(tt.ladder_median([110.5], [0.5]))


def test_team_points_from_team_totals_or_total_and_spread():
    odds = pd.DataFrame(ladder('HOME_TOTAL', 115.0) + ladder('AWAY_TOTAL', 108.0))
    assert tt.team_points(odds) == {'home': pytest.approx(115.0), 'away': pytest.approx(108.0)}
    # no team totals: total 220, home by 6 (home -6 is a coin flip) -> 113 / 107
    spread = [{'market': 'SPREAD', 'side': 'home', 'line': h, 'odds': 1 / (0.5 + 0.04 * (h + 6))}
              for h in (-7.5, -6.5, -5.5, -4.5)]
    spread += [{'market': 'SPREAD', 'side': 'away', 'line': -h, 'odds': 1 / (0.5 - 0.04 * (h + 6))}
               for h in (-7.5, -6.5, -5.5, -4.5)]
    got = tt.team_points(pd.DataFrame(ladder('TOTAL', 220.0) + spread))
    assert got['home'] == pytest.approx(113.0) and got['away'] == pytest.approx(107.0)


def test_pts_median_moves_with_the_price():
    assert tt.pts_median([20.5], [1.9], [1.9])[0] == pytest.approx(20.5)
    assert tt.pts_median([20.5], [1.6], [2.4])[0] > 20.5


def logs():
    """bos's last 12 games: lined players 1, 2; others 3 (12 pts, every game), 4 (6 pts, every other game)."""
    rows = []
    for day in range(1, 13):
        date = pd.Timestamp(f'2026-11-{day:02d}')
        for pid, pts in ((1, 25), (2, 20), (3, 12)) + (((4, 6),) if day % 2 else ()):
            rows.append({'player_id_ESPN': pid, 'team': 'bos', 'Date': date, 'PTS': pts})
    return pd.DataFrame(rows)


def test_others_points_counts_missed_games_as_zero_and_skips_the_excluded():
    team_of = {1: 'bos', 2: 'bos', 3: 'bos', 4: 'bos'}
    assert tt.others_points(logs(), 'bos', {1, 2}, team_of) == pytest.approx(12 + 3)
    assert tt.others_points(logs(), 'bos', {1, 2, 4}, team_of) == pytest.approx(12)


def test_team_gaps_and_line_shifts():
    team_of = {1: 'bos', 2: 'bos', 3: 'bos', 4: 'bos', 9: 'nyk'}
    lines = pd.DataFrame([{'event_id': 7, 'bet_type': 'PTS', 'line': 24.5, 'over_odds': 1.9, 'under_odds': 1.9,
                           'player_id_ESPN': 1},
                          {'event_id': 7, 'bet_type': 'PTS', 'line': 19.5, 'over_odds': 1.9, 'under_odds': 1.9,
                           'player_id_ESPN': 2},
                          {'event_id': 7, 'bet_type': 'REB', 'line': 7.5, 'over_odds': 1.9, 'under_odds': 1.9,
                           'player_id_ESPN': 2}])
    odds = pd.DataFrame(ladder('HOME_TOTAL', 70.0) + ladder('AWAY_TOTAL', 100.0))
    gaps = tt.team_gaps(lines, odds, logs(), team_of, out={4}, home='bos', away='nyk')
    assert list(gaps['team']) == ['bos']             # nyk has no PTS line
    g = gaps.iloc[0]
    assert g['S'] == pytest.approx(44.0) and g['others'] == pytest.approx(12.0)
    assert g['gap'] == pytest.approx(70 - 44 - 12 - tt.OFFSET)
    shifts = tt.line_shifts(lines, gaps, team_of)
    assert shifts.iloc[0] == pytest.approx(g['gap'] * 24.5 / 44) and shifts.iloc[2] == 0.0


def test_out_ids():
    v = pd.DataFrame({'player_id_ESPN': [1, 2, 3, np.nan], 'play_pct': [0, 25, 75, 0]})
    assert tt.out_ids(v) == {1, 2}
    assert tt.out_ids(None) == set()
