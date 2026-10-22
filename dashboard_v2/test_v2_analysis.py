"""Run with: python -m pytest dashboard_v2"""
import numpy as np
import pandas as pd
import pytest

from core.analysis import gap_bucket, pregame_average, side_profit, side_rates, team_game_log, teammate_impact, toward


def _logs(rows):
    """rows: (player_id, date, PTS, game_id[, team, MIN])."""
    df = pd.DataFrame([r + (('nyk', 30.0) if len(r) == 4 else ()) for r in rows],
                      columns=['player_id_ESPN', 'Date', 'PTS', 'game_id', 'team', 'MIN'])
    df['Date'] = pd.to_datetime(df['Date'])
    df['player_display_name'] = 'P' + df['player_id_ESPN'].astype(str)
    df['season_id'] = 2026
    df['position'] = 'G'
    df['starter'] = True
    return df


def test_pregame_average_uses_only_earlier_games():
    logs = _logs([(1, '2026-10-01', 10, 'a'), (1, '2026-10-03', 20, 'b'), (1, '2026-10-05', 90, 'c')])
    rows = pd.DataFrame({'player_id': [1, 1, 1], 'bet_type': 'PTS',
                         'game_date': pd.to_datetime(['2026-10-01', '2026-10-05', '2026-10-06'])})
    out = pregame_average(logs, rows)
    assert np.isnan(out['pre avg'].iloc[0]) and out['pre games'].iloc[0] == 0     # nothing before the first game
    assert out['pre avg'].iloc[1] == 15 and out['pre games'].iloc[1] == 2          # the game itself doesn't count
    assert out['pre avg'].iloc[2] == 40 and out['pre games'].iloc[2] == 3


def test_pregame_average_last_10_and_players_apart():
    logs = _logs([(1, f'2026-10-{d:02d}', d, f'g{d}') for d in range(1, 13)] + [(2, '2026-10-01', 100, 'x')])
    rows = pd.DataFrame({'player_id': [1, 2, 3], 'bet_type': 'PTS',
                         'game_date': pd.to_datetime(['2026-10-20', '2026-10-20', '2026-10-20'])})
    out = pregame_average(logs, rows)
    assert out['pre avg'].iloc[0] == pytest.approx(6.5)
    assert out['pre avg L10'].iloc[0] == pytest.approx(np.mean(range(3, 13)))
    assert out['pre avg'].iloc[1] == 100
    assert np.isnan(out['pre avg'].iloc[2]) and out['pre games'].iloc[2] == 0       # unknown player


def _settled(**cols):
    base = {'line': [20.5, 20.5, 20.5, 20.0, 20.5], 'actual': [25, 15, 25, 20, np.nan],
            'status': ['settled'] * 4 + ['pending'], 'ref': [22.0, 22.0, 18.0, 21.0, 22.0],
            'over_odds': 1.9, 'under_odds': 1.8}
    return pd.DataFrame(base | cols)


def test_toward_side_and_result():
    out = toward(_settled(), 'ref')
    assert out['ref side'].tolist()[:4] == ['Over', 'Over', 'Under', 'Over']
    assert out['ref result'].tolist()[:4] == ['win', 'loss', 'loss', 'push']
    assert pd.isna(out['ref result'].iloc[4])                                       # not settled yet


def test_toward_no_side_when_reference_equals_line_or_missing():
    out = toward(_settled(ref=[20.5, np.nan, 18.0, 21.0, 22.0]), 'ref')
    assert pd.isna(out['ref side'].iloc[0]) and pd.isna(out['ref side'].iloc[1])
    assert pd.isna(out['ref result'].iloc[0])


def test_side_profit_uses_that_sides_odds():
    out = toward(_settled(), 'ref')
    profit = side_profit(out, 'ref')
    assert profit.iloc[0] == pytest.approx(0.9)       # Over won at 1.9
    assert profit.iloc[2] == -1.0                     # Under lost
    assert profit.iloc[3] == 0.0                      # push
    rates = side_rates(out.assign(**{'ref profit': profit}, group='all'), 'group', 'ref')
    assert rates['lines'].iloc[0] == 3 and rates['hit %'].iloc[0] == pytest.approx(100 / 3)


def test_gap_bucket():
    buckets = gap_bucket(pd.Series([10.0, 19.0, 20.0, 22.0, 30.0, 5.0]), pd.Series([20.0] * 5 + [0.0]))
    assert buckets.tolist()[:5] == ['line 15%+ under avg', '5–15% under', 'within 5%', '5–15% over',
                                    'line 15%+ over avg']
    assert pd.isna(buckets.iloc[5])


def test_teammate_impact_row():
    # player 1 scores 10 with player 2, 20 in the two games 2 missed (inside 2's stint: games 1-4)
    rows = []
    for i, (p2_plays, pts) in enumerate([(True, 10), (False, 20), (False, 20), (True, 10)]):
        rows.append((1, f'2026-10-0{i + 1}', pts, f'g{i}'))
        if p2_plays:
            rows.append((2, f'2026-10-0{i + 1}', 5, f'g{i}'))
    out = teammate_impact(_logs(rows), 1, 'nyk', 'PTS', out_ids=[2], min_games=1)
    assert out['teammate_id'].tolist() == [2]
    r = out.iloc[0]
    assert (r['with'], r['without'], r['n_with'], r['n_without'], r['change']) == (10, 20, 2, 2, 10)
    assert bool(r['out tonight'])


def test_team_game_log():
    games = pd.DataFrame({'game_id': ['a', 'b'], 'date': pd.to_datetime(['2026-10-01', '2026-10-03']),
                          'season_id': 2026, 'season_type': 'regular', 'home': ['nyk', 'bos'], 'away': ['bos', 'nyk'],
                          'home_score': [110, 100], 'away_score': [100, 105],
                          **{f'{s}_{c}': v for s in ('home', 'away')
                             for c, v in (('FGA', 90), ('FTA', 25), ('TO', 12), ('OREB', 10))}})
    log = team_game_log(games, 'nyk')
    assert log['opp'].tolist() == ['bos', 'bos'] and log['location'].tolist() == ['home', 'away']
    assert log['margin'].tolist() == [10, 5] and log['win'].all()
    assert log['off_rtg'].iloc[0] == pytest.approx(100 * 110 / (90 + 0.44 * 25 + 12 - 10))
