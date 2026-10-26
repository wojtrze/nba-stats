"""Run with: python -m pytest dashboard"""
import numpy as np
import pandas as pd
import pytest

from tracking import (calibration, game_odds_movement, prop_movement, results_table, settle_games, settle_props)

START = '2026-10-22T23:30:00Z'   # 19:30 ET on Oct 22


def _props():
    base = {'name': 'A Player', 'name_ESPN': 'APlayer', 'home': 'bos', 'away': 'nyk', 'event_id': 1,
            'start_time': START, 'player_id_ESPN': 7}
    return pd.DataFrame([
        base | {'fetched_at': '2026-10-22T08:00:00Z', 'bet_type': 'PTS', 'line': 20.5, 'over_odds': 1.9,
                'under_odds': 1.9, 'pick': 'Over', 'model_pct': 60.0, 'edge_pp': 7.4, 'edge_low': 1.0},
        base | {'fetched_at': '2026-10-22T22:00:00Z', 'bet_type': 'PTS', 'line': 21.5, 'over_odds': 1.85,
                'under_odds': 1.95, 'pick': 'Over', 'model_pct': 55.0, 'edge_pp': 1.0, 'edge_low': -9.0},
        # fetched after tip-off: ignored
        base | {'fetched_at': '2026-10-23T00:00:00Z', 'bet_type': 'PTS', 'line': 30.5, 'over_odds': 1.9,
                'under_odds': 1.9, 'pick': 'Under', 'model_pct': 70.0, 'edge_pp': 10.0, 'edge_low': 2.0},
        base | {'fetched_at': '2026-10-22T08:00:00Z', 'bet_type': 'REB', 'line': 6.0, 'over_odds': 1.9,
                'under_odds': 1.9, 'pick': 'Under', 'model_pct': 55.0, 'edge_pp': 2.4, 'edge_low': -5.0},
        # an older snapshot row without the model columns, for a player who didn't play
        {'fetched_at': '2026-10-22T08:00:00Z', 'name': 'B Bench', 'name_ESPN': 'BBench', 'home': 'bos', 'away': 'nyk',
         'event_id': 1, 'start_time': START, 'bet_type': 'AST', 'line': 2.5, 'over_odds': 1.9, 'under_odds': 1.9},
        base | {'fetched_at': '2026-10-22T08:00:00Z', 'event_id': 2, 'home': 'lal', 'away': 'gs',
                'start_time': '2026-10-24T02:00:00Z', 'bet_type': 'PTS', 'line': 20.5, 'over_odds': 1.9,
                'under_odds': 1.9, 'pick': 'Over', 'model_pct': 60.0, 'edge_pp': 7.4, 'edge_low': 1.0},
    ])


def _logs():
    return pd.DataFrame([
        {'player_id_ESPN': 7, 'player_name_ESPN': 'APlayer', 'Date': pd.Timestamp('2026-10-22'), 'PTS': 25, 'REB': 6,
         'AST': 3},
        {'player_id_ESPN': 8, 'player_name_ESPN': 'BBench', 'Date': pd.Timestamp('2026-10-20'), 'PTS': 2, 'REB': 1,
         'AST': 1},
    ])


def _games():
    return pd.DataFrame([{'date': pd.Timestamp('2026-10-22'), 'home': 'bos', 'away': 'nyk', 'home_score': 110,
                          'away_score': 104}])


@pytest.fixture
def green_at_5(tmp_path, monkeypatch):
    """A calibration file whose 🟢 threshold is +5 pp."""
    import json
    import models
    path = tmp_path / 'calibration.json'
    path.write_text(json.dumps({'coefficients': models.IDENTITY_CALIBRATION, 'green_edge_pp': 5.0,
                                'model_version': models.MODEL_VERSION}))
    monkeypatch.setattr(models, 'CALIBRATION_FILE', str(path))


def test_settle_props(green_at_5):
    settled = settle_props(_props(), _logs(), _games()).set_index('bet_type', drop=False)
    pts = settled[(settled['bet_type'] == 'PTS') & (settled['game'] == 'NYK @ BOS')].iloc[0]
    # the first snapshot before tip-off is the bet; the last one before tip-off is the close
    assert pts['line'] == 20.5 and pts['close line'] == 21.5 and pts['signal'] == '🟢'      # edge 7.4 ≥ 5
    assert settled.loc['REB', 'signal'] == '🟡'                                              # edge 2.4
    assert pts['actual'] == 25 and pts['result'] == 'win' and pts['profit'] == pytest.approx(0.9)
    assert pts['clv line'] == 1.0 and np.isnan(pts['clv odds %'])
    reb = settled.loc['REB']
    assert reb['result'] == 'push' and reb['profit'] == 0
    ast = settled.loc['AST']
    assert ast['status'] == 'void' and pd.isna(ast['result'])      # no pick saved
    later = settled[settled['game'] == 'GS @ LAL'].iloc[0]
    assert later['status'] == 'pending' and pd.isna(later['result'])


def test_settle_props_keeps_the_saved_signal(green_at_5):
    props = _props()
    props['signal'] = ['🔴', '', '', '', np.nan, '']
    settled = settle_props(props, _logs(), _games()).set_index('bet_type', drop=False)
    assert settled.loc['REB', 'signal'] == '🟡'          # nothing saved: from the edge
    pts = settled[(settled['bet_type'] == 'PTS') & (settled['game'] == 'NYK @ BOS')].iloc[0]
    assert pts['signal'] == '🔴'                          # saved red flag kept


def _game_odds():
    base = {'event_id': 1, 'home': 'bos', 'away': 'nyk', 'start_time': START}
    rows = []
    for fetched, total_odds in (('2026-10-22T08:00:00Z', 1.9), ('2026-10-22T22:00:00Z', 1.8)):
        rows += [base | {'fetched_at': fetched, 'market': 'ML', 'side': 'home', 'line': np.nan, 'odds': 1.5,
                         'team': 'bos', 'model_pct': 70.0, 'edge_pp': 3.3},
                 base | {'fetched_at': fetched, 'market': 'ML', 'side': 'away', 'line': np.nan, 'odds': 2.6,
                         'team': 'nyk', 'model_pct': 30.0, 'edge_pp': -8.5},
                 base | {'fetched_at': fetched, 'market': 'SPREAD', 'side': 'away', 'line': 5.5, 'odds': 1.9,
                         'team': 'nyk', 'model_pct': 50.0, 'edge_pp': -2.6},
                 base | {'fetched_at': fetched, 'market': 'SPREAD', 'side': 'home', 'line': -5.5, 'odds': 1.9,
                         'team': 'bos', 'model_pct': 50.0, 'edge_pp': -2.6},
                 base | {'fetched_at': fetched, 'market': 'TOTAL', 'side': 'over', 'line': 210.5, 'odds': total_odds,
                         'team': None, 'model_pct': 60.0, 'edge_pp': 7.4},
                 base | {'fetched_at': fetched, 'market': 'TOTAL', 'side': 'under', 'line': 210.5, 'odds': 1.9,
                         'team': None, 'model_pct': 40.0, 'edge_pp': -12.6}]
    return pd.DataFrame(rows)


def test_settle_games():
    settled = settle_games(_game_odds(), _games())
    by = {(m, s): r for m, s, (_, r) in zip(settled['market'], settled['side'], settled.iterrows())}
    assert by[('ML', 'home')]['result'] == 'win' and by[('ML', 'away')]['result'] == 'loss'
    assert by[('SPREAD', 'home')]['result'] == 'win'     # won by 6, -5.5 covers
    assert by[('SPREAD', 'away')]['result'] == 'loss'
    over = by[('TOTAL', 'over')]
    assert over['result'] == 'win' and over['profit'] == pytest.approx(0.9)   # 110 + 104 = 214 > 210.5
    assert over['clv odds %'] == pytest.approx(100 * (1.9 / 1.8 - 1))
    assert over['score'] == '104 – 110' and over['main']


def test_movement():
    snaps = _props()
    current = snaps[snaps['fetched_at'] == '2026-10-22T22:00:00Z'].drop(columns='fetched_at')
    moved = prop_movement(snaps, current)
    assert moved['open line'].iloc[0] == 20.5 and moved['line move'].iloc[0] == 1.0
    odds = _game_odds()
    now = odds[odds['fetched_at'] == '2026-10-22T22:00:00Z'].drop(columns='fetched_at')
    moved = game_odds_movement(odds, now).set_index(['market', 'side'])
    assert moved.loc[('TOTAL', 'over'), 'odds move'] == pytest.approx(-0.1)
    assert moved.loc[('ML', 'home'), 'open odds'] == 1.5      # the moneyline's NaN line still matches


def test_results_table_and_calibration():
    settled = pd.DataFrame({'result': ['win', 'loss', 'win', 'push', 'void'], 'odds': [2.0, 2.0, 1.5, 1.9, 1.9],
                            'signal': ['🟢', '🟢', '🟡', '🟢', '🟢'], 'model_pct': [62.0, 64, 55, 60, 60],
                            'clv odds %': [2.0, -1.0, np.nan, 0, 0]})
    table = results_table(settled, 'signal').set_index('signal')
    assert table.loc['🟢', 'bets'] == 2 and table.loc['🟢', 'ROI %'] == 0 and table.loc['🟢', 'avg CLV %'] == 0.5
    cal = calibration(settled).set_index('bin')
    assert cal.loc[60, 'bets'] == 2 and cal.loc[60, 'actual %'] == 50 and cal.loc[50, 'actual %'] == 100
