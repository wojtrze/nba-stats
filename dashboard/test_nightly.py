"""Run with: python -m pytest dashboard"""
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from nightly import (lineups_before_tip, night_games, night_props, night_summary, nights, recompute_projection)

TIP = '2026-10-21T23:30:00Z'          # Oct 21 in New York


def _prop(fetched, line=20.5, pick='Over', start=TIP, **kw):
    row = {'fetched_at': fetched, 'name': 'A Player', 'name_ESPN': 'APlayer', 'home': 'bos', 'away': 'ny',
           'bet_type': 'PTS', 'line': line, 'event_id': 1, 'start_time': start, 'over_odds': 1.9, 'under_odds': 1.9,
           'player_id_ESPN': 7, 'pick': pick, 'model_pct': 55.0, 'edge_pp': 2.4, 'edge_low': -3.0, 'proj_avg': 22.0}
    return row | kw


LOGS = pd.DataFrame({'player_id_ESPN': [7], 'player_name_ESPN': ['APlayer'], 'Date': pd.to_datetime(['2026-10-21']),
                     'PTS': [25.0], 'team': ['ny'], 'position_group': ['G']})
GAMES = pd.DataFrame({'date': pd.to_datetime(['2026-10-21']), 'home': ['bos'], 'away': ['ny'], 'home_score': [110],
                      'away_score': [101], 'season_id': [2026]})


def test_nights_newest_first_started_only():
    snaps = pd.DataFrame([_prop('2026-10-21T10:00:00Z'), _prop('2026-10-22T10:00:00Z', start='2026-10-22T23:30:00Z')])
    out = nights(snaps, GAMES, datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc))
    assert [str(n.date()) for n in out['night']] == ['2026-10-21']          # Oct 22 hasn't tipped off
    assert out['settled'].tolist() == [True] and out['lines'].tolist() == [1]


def test_night_props_judges_the_last_fetch_before_tip_off():
    snaps = pd.DataFrame([_prop('2026-10-21T10:00:00Z', line=19.5, pick='Under'),
                          _prop('2026-10-21T22:00:00Z', line=20.5, pick='Over', proj_avg=22.0),
                          _prop('2026-10-21T23:45:00Z', line=30.5, pick='Under')])     # after tip-off: ignored
    out = night_props(snaps, LOGS, GAMES, '2026-10-21')
    r = out.iloc[0]
    assert (r['line'], r['pick'], r['open line'], r['pick at open'], r['fetches']) == (20.5, 'Over', 19.5, 'Under', 2)
    assert r['pick changed'] and r['result'] == 'win' and r['actual'] == 25
    assert r['proj error'] == pytest.approx(3.0) and r['line error'] == pytest.approx(4.5)
    assert r['closer than line']                                              # 3.0 off vs the line's 4.5
    assert r['signal'] == '🟡'                                                 # not saved: from the edges
    assert (r['position'], r['team'], r['venue'], r['recomputed']) == ('G', 'NY', 'away', False)


def test_night_props_keeps_a_saved_red_signal_and_pending_lines():
    snaps = pd.DataFrame([_prop('2026-10-21T22:00:00Z', signal='🔴', red_flag='Only 3 games')])
    out = night_props(snaps, LOGS.iloc[0:0], GAMES.iloc[0:0], '2026-10-21')   # stats not updated yet
    assert out['signal'].iloc[0] == '🔴' and out['red_flag'].iloc[0] == 'Only 3 games'
    assert out['status'].iloc[0] == 'pending' and pd.isna(out['proj error'].iloc[0])


def _odds(fetched, saved=True):
    rows = [{'fetched_at': fetched, 'market': 'ML', 'side': side, 'line': np.nan, 'odds': odds, 'team': team,
             'home': 'bos', 'away': 'ny', 'event_id': 1, 'start_time': TIP, 'model_pct': pct, 'edge_pp': edge}
            for side, odds, team, pct, edge in (('home', 1.5, 'bos', 70.0, 3.3), ('away', 2.6, 'ny', 30.0, -8.5))]
    if saved:
        rows = [r | {'proj_home_pts': 112.0, 'proj_away_pts': 104.0} for r in rows]
    return rows


def test_night_games_uses_the_saved_projection_else_recomputes():
    out = night_games(pd.DataFrame(_odds('2026-10-21T22:00:00Z')), GAMES, '2026-10-21',
                      recompute=lambda ev: pytest.fail("the projection was saved"))
    g = out['games'].iloc[0]
    assert (g['proj home'], g['proj away'], g['recomputed']) == (112.0, 104.0, False)
    assert g['winner called'] and g['margin error'] == pytest.approx(1.0) and g['total error'] == pytest.approx(-5.0)
    assert g['best bet'] == 'ML BOS' and g['best result'] == 'win'
    old = night_games(pd.DataFrame(_odds('2026-10-21T22:00:00Z', saved=False)), GAMES, '2026-10-21',
                      recompute=lambda ev: {'home_pts': 100.0, 'away_pts': 108.0})
    assert old['games'].iloc[0]['recomputed'] and not old['games'].iloc[0]['winner called']


def _box(date, home, away, hs, as_):
    side = {f'{s}_{c}': v for s in ('home', 'away') for c, v in (('FGA', 88), ('FTA', 22), ('TO', 13), ('OREB', 10))}
    return {'date': pd.Timestamp(date), 'season_id': 2026, 'season_type': 'regular', 'home': home, 'away': away,
            'home_score': hs, 'away_score': as_, 'game_id': f"{date}{home}", **side}


def test_recompute_uses_only_games_before_the_night():
    history = [_box(f'2026-10-{d:02d}', 'bos', 'ny', 110 + d % 3, 105) for d in range(1, 15)]
    night = _box('2026-10-21', 'bos', 'ny', 160, 60)                         # an extreme game that night
    odds = pd.DataFrame(_odds('2026-10-21T22:00:00Z'))
    logs = pd.DataFrame(columns=['player_id_ESPN', 'team', 'MIN', 'Date', 'season_id', 'season_type', 'game_id'])
    lineups = pd.DataFrame(columns=['team', 'role', 'play_pct', 'player_id_ESPN'])
    without = recompute_projection(odds, pd.DataFrame(history), logs, lineups, '2026-10-21')
    with_night = recompute_projection(odds, pd.DataFrame(history + [night]), logs, lineups, '2026-10-21')
    assert without['home_pts'] == pytest.approx(with_night['home_pts'])
    assert recompute_projection(odds, pd.DataFrame([night]), logs, lineups, '2026-10-21') is None


def test_lineups_before_tip():
    rw = pd.DataFrame({'fetched_at': ['2026-10-21T10:00:00Z', '2026-10-21T22:00:00Z', '2026-10-21T23:50:00Z'],
                       'game_date': '2026-10-21', 'name': ['morning', 'evening', 'after tip']})
    assert lineups_before_tip(rw, '2026-10-21', TIP)['name'].tolist() == ['evening']


def test_night_summary():
    props = pd.DataFrame({'status': ['settled'] * 3 + ['void'], 'pick': ['Over', 'Under', 'Over', 'Over'],
                          'signal': ['🟢', '', '🔴', ''], 'result': ['win', 'loss', 'win', 'void'],
                          'profit': [0.9, -1.0, 0.9, 0.0], 'proj error': [1.0, -3.0, 2.0, np.nan],
                          'line error': [2.0, -1.0, 4.0, np.nan], 'closer than line': [True, False, True, np.nan],
                          'actual': [22, 18, 30, np.nan], 'line': [20.5, 19.5, 26.5, 20.5]})
    s = night_summary(props, {})
    assert (s['settled'], s['void'], s['picks']['picks']) == (3, 1, 3)
    assert s['edge picks'] == {'picks': 1, 'hit %': 100.0, 'ROI %': pytest.approx(90.0)}
    assert s['red picks']['picks'] == 1 and s['plain picks']['hit %'] == 0
    assert s['median proj miss'] == 2.0 and s['median line miss'] == 2.0
    assert s['closer than line %'] == pytest.approx(200 / 3) and s['over %'] == pytest.approx(200 / 3)


def test_lines_saved_without_picks_are_recomputed():
    old = {k: np.nan for k in ('pick', 'model_pct', 'edge_pp', 'edge_low', 'proj_avg')}
    snaps = pd.DataFrame([_prop('2026-10-21T10:00:00Z', **old)])
    filled = lambda rows: pd.DataFrame({'pick': 'Over', 'model_pct': 54.0, 'edge_pp': 1.4, 'edge_low': -4.0,
                                        'proj_avg': 23.0, 'signal': '🟡', 'red_flag': ''}, index=rows.index)
    r = night_props(snaps, LOGS, GAMES, '2026-10-21', recompute=filled).iloc[0]
    assert (r['pick'], r['proj_avg'], r['signal'], r['result'], r['recomputed']) == ('Over', 23.0, '🟡', 'win', True)
    assert pd.isna(night_props(snaps, LOGS, GAMES, '2026-10-21').iloc[0]['pick'])   # without recompute: no pick


def test_group_outcomes_best_side_first():
    from nightly import group_outcomes
    lines = pd.DataFrame({'status': 'settled', 'bet_type': ['PTS'] * 4 + ['REB'] * 3,
                          'actual': [30, 10, 12, 20.5, 9, 10, 4], 'line': [20.5, 20.5, 20.5, 20.5, 6.5, 6.5, 6.5],
                          'over_odds': 2.0, 'under_odds': 2.0, 'result': ['loss', 'win', 'win', 'push', 'win', 'win', 'loss'],
                          'profit': [-1.0, 1.0, 1.0, 0.0, 1.0, 1.0, -1.0]})
    g = group_outcomes(lines, 'bet_type')
    assert g['bet_type'].tolist() == ['PTS', 'REB']              # both 2 of 3 (Unders / Overs): a tie keeps the order
    pts = g.set_index('bet_type').loc['PTS']
    assert (pts['lines'], pts['best side'], pts['best side %']) == (3, 'Under', pytest.approx(200 / 3))   # push out
    assert pts['under ROI %'] == pytest.approx(100 / 3) and pts['our picks'] == 3
    assert pts['ci low %'] < pts['best side %'] < pts['ci high %']
    assert group_outcomes(lines, ['bet_type'], min_lines=4).empty
