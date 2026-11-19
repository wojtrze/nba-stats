import numpy as np
import pandas as pd
import pytest

import backtest  # noqa: F401  (puts dashboard/ on the path)
from backtest.projection_eval import core, game_features, logs_source, score


def logs(n=14):
    """One player: 2025 bench games of 20 min (10 pts), then 2026 starts of 36 min (18 pts), plus a preseason game
    and a DNP that must be ignored."""
    rows = []
    for i in range(n):
        season, start = (2025, False) if i < 6 else (2026, True)
        minutes, pts = (20, 10) if not start else (36, 18)
        rows.append({'player_id_ESPN': 7, 'Date': pd.Timestamp('2025-11-01') + pd.Timedelta(days=60 * (i >= 6) + i),
                     'game_id': f'g{i}', 'season_id': season, 'season_type': 'regular', 'starter': start,
                     'MIN': minutes, 'PTS': pts, 'REB': 4, 'AST': 2, '3PM': 1})
    rows.append({**rows[-1], 'Date': rows[-1]['Date'] + pd.Timedelta(days=1), 'game_id': 'pre',
                 'season_type': 'pre', 'MIN': 40, 'PTS': 99})
    rows.append({**rows[-2], 'Date': rows[-2]['Date'] + pd.Timedelta(days=2), 'game_id': 'dnp', 'MIN': 0, 'PTS': 0})
    df = pd.DataFrame(rows)
    return df.assign(ARP=df['PTS'] + df['REB'] + df['AST'])


def test_features_use_only_earlier_real_games():
    f = game_features(logs())
    assert len(f) == 14 and f['game_id'].tolist()[-1] == 'g13'     # no preseason, no DNP
    assert np.isnan(f.loc[0, 'rate PTS'])                             # nothing before the first game
    # the 7th game (first of 2026, first start): no minutes of the season yet; across seasons no start, bench EWMA 20;
    # the rate is last season's 0.5 pts/min (nothing of the season to weigh against it)
    first_start = f[f['game_id'] == 'g6'].iloc[0]
    assert np.isnan(first_start['min all']) and np.isnan(first_start['xmin st'])
    assert first_start['xmin bn'] == pytest.approx(20) and first_start['rate PTS'] == pytest.approx(0.5)
    # 3 starts into 2026 (36 min, 18 pts): the season's 0.5 pts/min again; minutes now the season's 36
    third = f[f['game_id'] == 'g9'].iloc[0]
    assert third['n season'] == 3 and third['min st'] == pytest.approx(36)
    # changing a later game's result never changes an earlier game's features
    later = logs()
    later.loc[later['game_id'] == 'g10', 'PTS'] = 50
    g = game_features(later.assign(ARP=later['PTS'] + later['REB'] + later['AST']))
    cols = ['rate PTS', 'mean PTS', 'min st']
    pd.testing.assert_frame_equal(f.loc[f['history'] <= 10, cols], g.loc[g['history'] <= 10, cols])


def test_season_mean_tops_up_with_earlier_games_below_ten():
    f = game_features(logs())
    # 8th game: one 2026 game before it → the latest 10 games (6 bench at 10 pts + ... only 7 exist) are averaged
    assert f[f['game_id'] == 'g7'].iloc[0]['mean PTS'] == pytest.approx((6 * 10 + 18) / 7)


def test_core_uses_the_role_minutes_and_falls_back_to_all_games():
    f = game_features(logs())
    row = f[f['game_id'] == 'g6']
    as_starter = core(row, pd.Series(True, index=row.index))
    assert as_starter['PTS'].iloc[0] == pytest.approx(row['xmin all'].iloc[0] * 0.5)   # no starts yet: all games
    as_bench = core(row, pd.Series(False, index=row.index))
    assert as_bench['PTS'].iloc[0] == pytest.approx(20 * 0.5)
    assert as_bench['ARP'].iloc[0] == pytest.approx(sum(as_bench[s].iloc[0] for s in ('PTS', 'REB', 'AST')))


def test_rate_weighs_the_season_against_last_seasons_prior():
    df = logs()
    df.loc[df['season_id'] == 2026, 'PTS'] = 36           # 1 pt/min in 2026 against 0.5 in 2025
    f = game_features(df.assign(ARP=df['PTS'] + df['REB'] + df['AST']), prior_games=5, prior_minutes=25)
    row = f[f['game_id'] == 'g8'].iloc[0]                 # 2 games of 36 min before it
    assert row['rate PTS'] == pytest.approx((72 + 125 * 0.5) / (72 + 125))
    # 2 games of the season: minutes still taken across seasons
    projected = core(f.loc[[row.name]], pd.Series(True, index=[row.name]))['PTS'].iloc[0]
    assert projected == pytest.approx(row['xmin st'] * row['rate PTS'])


def test_logs_source_and_score():
    a = logs_source(game_features(logs()), min_history=10)
    assert set(a['stat']) == {'PTS', 'REB', 'AST', '3PM', 'ARP'} and len(a) == 4 * 5
    s = score(a, ['season mean', 'core: minutes in role × rate'], 'season mean', False)
    pts = s[(s['stat'] == 'PTS')].set_index('candidate')
    # a settled starter: the role core is spot on, the season mean still carries bench games
    assert pts.loc['core: minutes in role × rate', 'MAE'] < pts.loc['season mean', 'MAE']
    assert pts.loc['core: minutes in role × rate', 'vs'] < 0


def test_the_live_model_computes_the_harness_core():
    """metrics.minutes_rate (what price_props uses) gives the same number as the harness scored, game by game."""
    from metrics import minutes_rate
    df = logs()
    df.loc[df['game_id'].isin(['g8', 'g11']), 'starter'] = False        # role changes inside the season
    late = df['season_id'] == 2026
    df.loc[late, 'PTS'] = [18, 30, 9, 22, 26, 14, 20, 33, 99, 0][:late.sum()]
    df = df.assign(ARP=df['PTS'] + df['REB'] + df['AST'])
    f = game_features(df)
    for _, row in f[f['history'] >= 1].iterrows():
        before = df[df['Date'] < row['Date']]
        for stat in ('PTS', 'ARP'):
            for starter in (True, False):
                harness = core(f.loc[[row.name]], pd.Series(starter, index=[row.name]))[stat].iloc[0]
                live = minutes_rate(before, row['season_id'], starter, stat)['base']
                assert live == pytest.approx(harness), (row['game_id'], stat, starter)
