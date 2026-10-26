"""Run with: python -m pytest dashboard"""
import numpy as np
import pandas as pd

import models
from models import DEFAULT_SEASON_TYPES, price_props, top_up_logs


def _log(pid, day, season, kind='regular', pts=20.0, team='bos', opp='NY', game=None):
    return {'player_id_ESPN': pid, 'Date': pd.Timestamp(day), 'season_id': season, 'season_type': kind, 'PTS': pts,
            'MIN': 30.0, 'team': team, 'OPP': opp, 'position': 'G', 'position_group': 'G',
            'game_id': game or f"{pid}-{day}"}


def _logs():
    last_season = [_log(1, f'2026-03-{d:02d}', 2025, pts=float(d)) for d in range(1, 13)]   # 12 regular games
    last_season += [_log(1, '2026-04-20', 2025, kind='post', pts=99.0)]                     # playoffs count too
    preseason = [_log(1, '2026-10-05', 2026, kind='pre', pts=5.0)]
    current = [_log(1, f'2026-10-{d}', 2026) for d in (21, 23, 25)]
    veteran = [_log(2, f'2026-10-{d:02d}', 2026) for d in range(10, 22)] + [_log(2, '2026-03-01', 2025)]
    rookie = [_log(3, '2026-10-21', 2026)]
    return pd.DataFrame(last_season + preseason + current + veteran + rookie).sort_values('Date', kind='stable')


def _scoped(logs, seasons=(2026,)):
    return logs[logs['season_id'].isin(seasons) & logs['season_type'].isin(DEFAULT_SEASON_TYPES)]


def test_preseason_is_left_out_by_default():
    assert 'pre' not in DEFAULT_SEASON_TYPES


def test_top_up_fills_to_ten_with_the_latest_real_games_of_last_season():
    logs = _logs()
    out = top_up_logs(_scoped(logs), logs, 2026, [1, 2, 3])
    p1 = out[out['player_id_ESPN'] == 1]
    assert len(p1) == 10 and p1['top_up'].sum() == 7
    assert (p1['season_type'] != 'pre').all()
    assert p1.loc[p1['top_up'], 'PTS'].tolist() == [7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 99.0]   # the latest, oldest first
    assert p1['Date'].is_monotonic_increasing
    assert not out.loc[out['player_id_ESPN'] == 2, 'top_up'].any()                         # already has 12 games
    assert out.loc[out['player_id_ESPN'] == 3, 'top_up'].sum() == 0                         # no last season


def test_top_up_covers_a_player_without_games_this_season():
    logs = _logs()
    scoped = _scoped(logs)
    out = top_up_logs(scoped[scoped['player_id_ESPN'] != 1], logs, 2026, [1])
    assert out.loc[out['player_id_ESPN'] == 1, 'top_up'].tolist() == [True] * 10


def test_top_up_only_for_players_asked_and_not_when_last_season_is_chosen():
    logs = _logs()
    assert not top_up_logs(_scoped(logs), logs, 2026, [2])['top_up'].any()
    both = top_up_logs(_scoped(logs, (2025, 2026)), logs, 2026, [1])
    assert not both['top_up'].any() and len(both) == len(_scoped(logs, (2025, 2026)))


def test_price_props_keeps_topped_up_games_out_of_matchups_and_absences(monkeypatch):
    logs = _logs()
    scoped = top_up_logs(_scoped(logs), logs, 2026, [1])
    seen = {}
    real_allowed = models.allowed_by_position

    def allowed(part, stat):
        seen['allowed'] = part
        return real_allowed(part, stat)

    monkeypatch.setattr(models, 'allowed_by_position', allowed)

    def adjust(part, players, out, stats):
        seen['adjust'] = part
        return pd.DataFrame()

    props = pd.DataFrame([{'name': 'A', 'name_ESPN': 'A', 'home': 'bos', 'away': 'ny', 'bet_type': 'PTS',
                           'line': 15.5, 'event_id': 9, 'start_time': '2026-10-27T23:30:00Z', 'over_odds': 1.9,
                           'under_odds': 1.9, 'player_id_ESPN': 1}])
    lineups = pd.DataFrame([{'team': 'bos', 'player_id_ESPN': 3, 'role': 'may_not_play', 'play_pct': 0,
                             'lineup_status': 'expected', 'injury': 'Out'}])
    table = price_props(props, scoped, lineups, pd.DataFrame(), pd.DataFrame(columns=['home', 'away']),
                        adjust=adjust, calibration=models.IDENTITY_CALIBRATION)
    assert table.loc[0, 'games'] == 10                      # the player's own numbers use the topped-up games
    assert not seen['allowed']['top_up'].any() and not seen['adjust']['top_up'].any()


# --- signals, pick and lean ---

def test_prop_signal():
    from metrics import prop_signal
    edges = pd.Series([-1.0, 0.0, 0.5, 2.9, 3.0, 8.0, np.nan])
    assert prop_signal(edges, 3.0).tolist() == ['', '', '🟡', '🟡', '🟢', '🟢', '']
    assert prop_signal(edges, None).tolist() == ['', '', '🟡', '🟡', '🟡', '🟡', '']     # no threshold, no 🟢
    assert prop_signal(4.0, 3.0) == '🟢' and prop_signal(-2.0, 3.0) == ''


def test_load_green_edge(tmp_path):
    import json
    from models import load_green_edge
    assert load_green_edge(str(tmp_path / 'missing.json')) is None
    path = tmp_path / 'calibration.json'
    path.write_text(json.dumps({'coefficients': models.IDENTITY_CALIBRATION}))
    assert load_green_edge(str(path)) is None                       # an older file without a threshold
    path.write_text(json.dumps({'coefficients': models.IDENTITY_CALIBRATION, 'green_edge_pp': 2.0}))
    assert load_green_edge(str(path)) == 2.0


def test_bet_only_with_a_positive_edge_and_lean_from_the_projection():
    from models import bet_side, lean
    best = pd.Series(['Under', 'Over', 'Under', None])
    assert bet_side(best, pd.Series(['', '🟡', '🟢', ''])).tolist() == ['', 'Over', 'Under', '']
    assert bet_side(best, pd.Series(['🔴', '', '', ''])).tolist() == ['', '', '', '']
    proj, line = pd.Series([25.0, 21.0, 18.0, np.nan, 0.0]), pd.Series([20.5, 20.5, 20.5, 20.5, 0.5])
    assert lean(proj, line).tolist() == ['Over', '', 'Under', '', 'Under']   # 21 vs 20.5 is too close to call


def test_flag_props_takes_the_bet_away_from_a_red_line():
    from reasons import flag_props
    table = pd.DataFrame({'player_id': [1, 2], 'best side': ['Over', 'Under'], 'signal': ['🟡', '🟡'],
                          'bet': ['Over', 'Under'], 'RotoWire': ['', '']})
    logs = pd.DataFrame([_log(1, f'2026-10-{d:02d}', 2026) for d in range(1, 13)] + [_log(2, '2026-10-01', 2026)])
    out = flag_props(table, logs, pd.DataFrame(columns=['player_id_ESPN', 'play_pct']))
    assert out['signal'].tolist() == ['🟡', '🔴'] and out['bet'].tolist() == ['Over', '']   # player 2: 1 game


# --- signal efficiency ---

def test_rate_rows_show_what_the_model_expected():
    from metrics import grouped_rates
    bets = pd.DataFrame({'g': ['a', 'a', 'b'], 'is_hit': [True, False, True], 'odds': [1.9, 1.9, 2.0],
                         'model_pct': [60.0, 50.0, 55.0]})
    t = grouped_rates(bets, 'g').set_index('g')
    assert t.loc['a', 'expected %'] == 55.0 and t.loc['a', 'hit %'] == 50.0
    assert 'expected %' not in grouped_rates(bets.drop(columns='model_pct'), 'g')


def test_threshold_table_is_cumulative():
    from tracking import threshold_table
    settled = pd.DataFrame({'edge_pp': [-1.0, 0.5, 1.5, 3.0, 6.0, 2.0], 'result': ['win', 'loss', 'win', 'win', 'loss', 'push'],
                            'odds': 1.9, 'model_pct': [50.0, 53.0, 54.0, 56.0, 59.0, 55.0]})
    t = threshold_table(settled).set_index('edge ≥ pp')
    assert t['bets'].to_dict() == {0: 4, 1: 3, 2: 2, 3: 2, 5: 1}         # the push and the negative edge left out
    assert t.loc[3, 'hit %'] == 50.0 and t.loc[5, 'expected %'] == 59.0
