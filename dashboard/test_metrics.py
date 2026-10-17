"""Run with: python -m pytest dashboard"""
import math

import numpy as np
import pandas as pd
import pytest

from metrics import (add_combined_stats, allowed_by_position, hit_rates, line_percentile, lineup_scenario,
                     percentile_band, roi, rule_stats, starting_lineup, stint_games, team_rotation, vote_pattern,
                     wilson_interval, with_without, with_without_matrix)


def test_hit_rates_counts_pushes_for_neither_side():
    rates = hit_rates(pd.Series([10, 20, 20, 30]), 20)
    assert rates == {'over': 0.25, 'under': 0.25, 'games': 4}
    assert math.isnan(hit_rates(pd.Series([], dtype=float), 20)['over'])


def test_line_percentile():
    values = pd.Series([10, 20, 30, 40])
    assert line_percentile(values, 25) == 50
    assert line_percentile(values, 5) == 0
    assert line_percentile(values, 20) == 37.5   # one below, one tie counted half


def test_percentile_band_matches_check_bet():
    values = pd.Series(range(11))
    assert percentile_band(values) == (3.0, 7.0)


def test_combined_stats():
    df = add_combined_stats(pd.DataFrame({'PTS': [20], 'REB': [5], 'AST': [7]}))
    assert (df['PA'][0], df['PR'][0], df['ARP'][0]) == (27, 25, 32)


def test_roi_and_wilson():
    assert roi(pd.Series([True, False]), pd.Series([2.0, 2.0])) == 0.0
    assert roi(pd.Series([True, True]), pd.Series([1.5, 1.5])) == pytest.approx(0.5)
    low, high = wilson_interval(50, 100)
    assert low < 0.5 < high and high - low == pytest.approx(0.19, abs=0.01)


def _logs():
    # player 1 plays 4 games for team a; teammate 2 misses game 3; game 5 is after the teammate left
    rows = []
    for game, (date, mate_played) in enumerate([('2025-01-01', True), ('2025-01-02', True), ('2025-01-03', False),
                                                ('2025-01-04', True), ('2025-01-05', False)], start=1):
        rows.append({'player_id_ESPN': 1, 'game_id': str(game), 'team': 'a', 'season_id': 2024, 'Date': date,
                     'PTS': 10 * game, 'MIN': 30, 'FGA': 10, 'OPP': 'B', 'position': 'G'})
        if mate_played:
            rows.append({'player_id_ESPN': 2, 'game_id': str(game), 'team': 'a', 'season_id': 2024, 'Date': date,
                         'PTS': 5, 'MIN': 20, 'FGA': 5, 'OPP': 'B', 'position': 'C'})
    return pd.DataFrame(rows)


def test_with_without_only_counts_teammates_stint():
    ww = with_without(_logs(), 1, 2, 'PTS')
    assert ww.loc['Teammate played', 'games'] == 3
    assert ww.loc['Teammate played', 'avg'] == pytest.approx((10 + 20 + 40) / 3)
    assert ww.loc['Teammate out', 'games'] == 1          # game 5 is after the teammate's last game
    assert ww.loc['Teammate out', 'avg'] == 30


def test_allowed_by_position():
    table = allowed_by_position(_logs(), 'PTS')
    assert table.loc['b', 'games'] == 5
    assert table.loc['b', 'G'] == pytest.approx(30)        # mean of 10..50
    assert table.loc['b', 'C'] == pytest.approx(3)         # 5 points in 3 of 5 games


def test_rule_stats_and_vote_pattern():
    bets = pd.DataFrame({'over_under': ['Over', 'Over', 'Under'], 'is_hit': [True, False, True],
                         'odds': [2.0, 2.0, 2.0], 'quantiles': ['Over', 'Under', None], 'median': [None, None, 'Under'],
                         'last_games': None, 'averages': None, 'bets_hits': None, 'low_odds': None})
    stats = rule_stats(bets).set_index(['rule', 'vote'])
    assert stats.loc[('quantiles', 'agrees'), 'bets'] == 1
    assert stats.loc[('quantiles', 'disagrees'), 'hit %'] == 0
    patterns = vote_pattern(bets)
    assert patterns['pattern'].tolist() == ['+quantiles', '-quantiles', '+median']
    assert patterns['net'].tolist() == [1, -1, 1]


def _team_logs():
    """Team 'a', 6 games. Players 1-5 start every game; 6 comes off the bench. Player 3 misses games 4-5,
    player 7 plays games 1-2 for 'a' and then is traded to 'b' (game 6 for 'b')."""
    rows = []

    def add(pid, game, team='a', starter=False, pts=10, minutes=30):
        rows.append({'player_id_ESPN': pid, 'player_display_name': f'P{pid}', 'position': 'G', 'game_id': str(game),
                     'team': team, 'season_id': 2025, 'Date': f'2025-01-0{game}', 'starter': starter,
                     'PTS': pts, 'MIN': minutes, 'FGA': 10, 'OPP': 'X'})
    for game in range(1, 7):
        for pid in (1, 2, 4, 5):
            add(pid, game, starter=True, pts=20 if pid == 1 and game in (4, 5) else 10)
        if game not in (4, 5):
            add(3, game, starter=True)
        else:
            add(8, game, starter=True)          # 8 starts in place of 3
        add(6, game, minutes=15 if game < 6 else 2)
        if game <= 2:
            add(7, game, minutes=12)
    add(7, 6, team='b', minutes=25)
    return pd.DataFrame(rows)


def test_stint_games_excludes_games_outside_stint():
    logs = _team_logs()
    games = stint_games(logs, 1, 7)          # 7 played games 1-2 for 'a', then left
    assert sorted(games['game_id']) == ['1', '2'] and games['teammate_played'].all()
    games = stint_games(logs, 1, 3)
    assert games.set_index('game_id')['teammate_played'].to_dict() == {'1': True, '2': True, '3': True, '4': False,
                                                                       '5': False, '6': True}


def test_team_rotation_thresholds_and_trades():
    rotation = team_rotation(_team_logs(), 'a', min_games=3, min_minutes=10)
    assert 7 not in rotation.index                    # traded to 'b'
    assert 8 not in rotation.index                    # only 2 games
    assert set(rotation.index) == {1, 2, 3, 4, 5, 6}
    assert rotation.loc[1, 'starts'] == 6


def test_starting_lineup():
    logs = _team_logs()
    assert sorted(starting_lineup(logs, 'a', 'last')) == [1, 2, 3, 4, 5]
    logs_last_without_3 = logs[logs['game_id'] != '6']
    assert sorted(starting_lineup(logs_last_without_3, 'a', 'last')) == [1, 2, 4, 5, 8]
    assert sorted(starting_lineup(logs_last_without_3, 'a', 'frequent')) == [1, 2, 3, 4, 5]


def test_with_without_matrix_matches_pairwise():
    logs = _team_logs()
    m = with_without_matrix(logs, [1, 2], [1, 3], 'PTS')
    assert np.isnan(m['delta'].loc[1, 1])
    assert m['delta'].loc[1, 3] == pytest.approx(10)          # 20 without 3, 10 with
    assert (m['n_with'].loc[1, 3], m['n_without'].loc[1, 3]) == (4, 2)
    ww = with_without(logs, 1, 3, 'PTS')
    assert m['delta'].loc[1, 3] == ww.loc['Teammate out', 'avg'] - ww.loc['Teammate played', 'avg']


def test_lineup_scenario_exact_and_shrunk_estimate():
    logs = _team_logs()
    s = lineup_scenario(logs, 'a', starters=[1, 2, 4, 5, 6], out=[3], available=[], stat='PTS', shrink=2).set_index('player_id_ESPN')
    # exact match: starters 1,2,4,5,6 all played and 3 missed -> games 4 and 5
    assert s.loc[1, 'exact games'] == 2 and s.loc[1, 'exact match'] == 20
    usual = (4 * 10 + 2 * 20) / 6
    assert s.loc[1, 'estimate'] == pytest.approx(usual + 10 * 2 / (2 + 2))
    assert s.loc[2, 'change'] == 0
    assert s.loc[1, 'role'] == 'Starter'
