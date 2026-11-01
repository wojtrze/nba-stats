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
    assert pts['line'] == 20.5 and pts['last line'] == 21.5 and pts['signal'] == '🟢'       # edge 7.4 ≥ 5
    # fetched 08:00 and 22:00 UTC for a 23:30 UTC tip-off
    assert pts['h before tip'] == 15.5 and pts['last h before tip'] == 1.5
    assert settled.loc['REB', 'signal'] == '🟡'                                              # edge 2.4
    assert pts['actual'] == 25 and pts['result'] == 'win' and pts['profit'] == pytest.approx(0.9)
    assert pts['line vs last'] == 1.0 and np.isnan(pts['odds vs last %'])
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
    assert over['odds vs last %'] == pytest.approx(100 * (1.9 / 1.8 - 1))
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
                            'odds vs last %': [2.0, -1.0, np.nan, 0, 0]})
    table = results_table(settled, 'signal').set_index('signal')
    assert table.loc['🟢', 'bets'] == 2 and table.loc['🟢', 'ROI %'] == 0 and table.loc['🟢', 'avg odds vs last %'] == 0.5
    cal = calibration(settled).set_index('bin')
    assert cal.loc[60, 'bets'] == 2 and cal.loc[60, 'actual %'] == 50 and cal.loc[50, 'actual %'] == 100


# --- settlement edge cases ---

def test_side_result_and_profit():
    from metrics import side_profit, side_result
    margin = pd.Series([0.5, -0.5, 0.0, np.nan, 2.0])
    result = side_result(margin, pd.Series([True, True, True, True, False]))
    assert result.tolist()[:3] == ['win', 'loss', 'push'] and result.iloc[3:].isna().all()   # unknown / not decided
    profit = side_profit(pd.Series(['win', 'loss', 'push', 'void', np.nan]), [1.9] * 5)
    assert profit.tolist()[:4] == pytest.approx([0.9, -1.0, 0.0, 0.0]) and np.isnan(profit.iloc[4])


def _box(pid, name, team, venue, game_id, pts, reb=0, ast=0, day='2026-10-22'):
    return {'player_id_ESPN': pid, 'player_name_ESPN': name, 'Date': pd.Timestamp(day), 'team': team, 'type': venue,
            'game_id': game_id, 'PTS': pts, 'REB': reb, 'AST': ast}


def _line(name, home, away, bet_type, line, pick, pid=None, start=START, event_id=1):
    return {'fetched_at': '2026-10-22T08:00:00Z', 'name': name, 'name_ESPN': name, 'home': home, 'away': away,
            'event_id': event_id, 'start_time': start, 'bet_type': bet_type, 'line': line, 'over_odds': 1.9,
            'under_odds': 1.9, 'pick': pick, 'model_pct': 55.0, 'edge_pp': 2.4, 'edge_low': -3.0, 'player_id_ESPN': pid}


def test_settle_props_statuses():
    from metrics import add_combined_stats
    late = '2026-10-23T02:00:00Z'                                      # 22:00 ET on Oct 22
    logs = add_combined_stats(pd.DataFrame([
        _box(7, 'APlayer', 'bos', 'home', 1, 110, reb=6, ast=3),       # bos 110 – nyk 104: complete
        _box(9, 'JWilliams', 'nyk', 'away', 1, 54), _box(10, 'JWilliams', 'nyk', 'away', 1, 50),
        _box(11, 'CStar', 'lal', 'home', 2, 100),                       # lal scored 110: a line is missing
        _box(12, 'DGuard', 'gs', 'away', 2, 95)]))
    games = pd.DataFrame([
        {'game_id': 1, 'date': pd.Timestamp('2026-10-22'), 'home': 'bos', 'away': 'nyk', 'home_score': 110,
         'away_score': 104},
        {'game_id': 2, 'date': pd.Timestamp('2026-10-22'), 'home': 'lal', 'away': 'gs', 'home_score': 110,
         'away_score': 95}])
    bets = pd.DataFrame([
        _line('APlayer', 'bos', 'nyk', 'ARP', 118.5, 'Over', pid=7),                 # PTS + REB + AST = 119
        _line('APlayer', 'bos', 'nyk', 'REB', 6.0, 'Under', pid=7),                  # whole-number line: push
        _line('BBench', 'bos', 'nyk', 'PTS', 8.5, 'Over', pid=8),                    # complete game, no row
        _line('JWilliams', 'bos', 'nyk', 'PTS', 50.5, 'Over'),                       # two players by that name
        _line('Nobody', 'bos', 'nyk', 'PTS', 10.5, 'Over'),                          # a name no player has
        _line('EBench', 'lal', 'gs', 'PTS', 8.5, 'Over', pid=13, start=late, event_id=2),   # incomplete game
        _line('FPlayer', 'chi', 'mia', 'PTS', 20.5, 'Over', pid=14, start='2026-10-21T23:30:00Z', event_id=3),
        _line('GPlayer', 'den', 'okc', 'PTS', 20.5, 'Over', pid=15, start='2026-10-23T23:30:00Z', event_id=4)])
    out = settle_props(bets, logs, games, bets=bets)
    rows = dict(zip(out['bet_type'] + ' ' + bets['name'].values, out.to_dict('records')))
    assert rows['ARP APlayer']['actual'] == 119 and rows['ARP APlayer']['result'] == 'win'
    assert rows['REB APlayer']['result'] == 'push' and rows['REB APlayer']['profit'] == 0
    assert rows['PTS BBench']['status'] == 'void' and rows['PTS BBench']['result'] == 'void'
    for name, why in (('JWilliams', 'ambiguous name'), ('Nobody', 'unknown name'),
                      ('EBench', 'incomplete box score'), ('FPlayer', 'postponed: later games are stored')):
        row = rows[f'PTS {name}']
        assert row['status'] == 'unresolved', why
        assert pd.isna(row['result']) and pd.isna(row['profit']), why
    assert rows['PTS GPlayer']['status'] == 'pending'                   # not played yet


def test_settle_games_postponed_is_unresolved():
    odds = _game_odds()
    postponed = odds.assign(event_id=9, home='chi', away='mia', start_time='2026-10-23T01:00:00Z')  # Oct 22 ET
    next_day = pd.DataFrame([{'date': pd.Timestamp('2026-10-23'), 'home': 'den', 'away': 'okc', 'home_score': 100,
                              'away_score': 99}])
    settled = settle_games(pd.concat([odds, postponed], ignore_index=True), pd.concat([_games(), next_day]))
    assert set(settle_games(postponed, _games())['status']) == {'pending'}     # nothing later stored yet
    assert set(settled.loc[settled['game'] == 'MIA @ CHI', 'status']) == {'unresolved'}
    assert settled.loc[settled['game'] == 'MIA @ CHI', 'result'].isna().all()
    assert set(settled.loc[settled['game'] == 'NYK @ BOS', 'status']) == {'settled'}


def test_closing_line_and_clv(green_at_5):
    from tracking import CLOSE_MAX_AGE_MIN, closing_props
    quotes = pd.DataFrame([
        # PTS: 20.5 at 1.9/1.9 early, then the Over shortened at the same line (the bet beat the close)
        {'fetched_at': '2026-10-22T08:00:00Z', 'event_id': 1, 'name_ESPN': 'APlayer', 'bet_type': 'PTS',
         'line': 20.5, 'over_odds': 1.9, 'under_odds': 1.9},
        {'fetched_at': '2026-10-22T23:00:00Z', 'event_id': 1, 'name_ESPN': 'APlayer', 'bet_type': 'PTS',
         'line': 20.5, 'over_odds': 1.7, 'under_odds': 2.1},
        # REB withdrawn before tip-off: no close
        {'fetched_at': '2026-10-22T08:00:00Z', 'event_id': 1, 'name_ESPN': 'APlayer', 'bet_type': 'REB',
         'line': 6.0, 'over_odds': 1.9, 'under_odds': 1.9},
        {'fetched_at': '2026-10-22T23:00:00Z', 'event_id': 1, 'name_ESPN': 'APlayer', 'bet_type': 'REB',
         'line': None, 'over_odds': None, 'under_odds': None},
    ])
    reads = pd.DataFrame({'fetched_at': ['2026-10-22T08:00:00Z', '2026-10-22T23:00:00Z', '2026-10-22T23:25:00Z'],
                          'event_id': 1, 'start_time': START})
    closing = closing_props(quotes, reads)
    assert list(closing['bet_type']) == ['PTS'] and closing['close age min'].iloc[0] == 5.0
    first = _props().iloc[[0, 3]]                                       # the early PTS Over and REB Under
    settled = settle_props(_props(), _logs(), _games(), bets=first, closing=closing).set_index('bet_type')
    pts = settled.loc['PTS']
    p_close = (1 / 1.7) / (1 / 1.7 + 1 / 2.1)
    assert pts['close odds'] == 1.7 and pts['line vs close'] == 0
    assert pts['clv %'] == pytest.approx(100 * (1.9 * p_close - 1))      # positive: the bet beat the close
    assert pts['clv % std'] == pytest.approx(100 * (0.88 * 1.9 * p_close - 1))
    assert pts['clv pp'] == pytest.approx(100 * (p_close - 0.5))
    assert pd.isna(settled.loc['REB', 'clv %'])
    stale = closing.assign(**{'close age min': CLOSE_MAX_AGE_MIN + 1})  # last read too early: no CLV
    assert pd.isna(settle_props(_props(), _logs(), _games(), bets=first, closing=stale)['clv %']).all()
