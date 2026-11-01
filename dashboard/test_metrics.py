"""Run with: python -m pytest dashboard"""
import math

import numpy as np
import pandas as pd
import pytest

from metrics import (absence_adjustments, absence_impact, add_combined_stats, allowed_by_position, blended_ratings,
                     count_over, game_projection, hit_rates, line_percentile, lineup_scenario, market_edges,
                     model_probability, no_vig, percentile_band, prop_probability, roi, rotowire_team, rule_stats,
                     starting_lineup, stint_games, team_rotation,
                     vote_pattern, wilson_interval, with_without, with_without_matrix)


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
    assert (df['PA'][0], df['PR'][0], df['RA'][0], df['ARP'][0]) == (27, 25, 12, 32)


def test_roi_and_wilson():
    assert roi(pd.Series([True, False]), pd.Series([2.0, 2.0])) == 0.0
    assert roi(pd.Series([True, True]), pd.Series([1.5, 1.5])) == pytest.approx(0.5)
    low, high = wilson_interval(50, 100)
    assert low < 0.5 < high and high - low == pytest.approx(0.19, abs=0.01)


def test_no_vig_removes_the_margin():
    assert no_vig(1.9, 1.9) == pytest.approx((0.5, 0.5))
    over, under = no_vig(1.5, 2.5)
    assert over + under == pytest.approx(1) and over == pytest.approx(0.625)
    over, under = no_vig(2.0, np.nan)
    assert over == 0.5 and math.isnan(under)


def test_prop_probability_without_games_is_the_market():
    chance = prop_probability(pd.Series([], dtype=float), 20.5, 'Over', 0.55)
    assert chance['p'] == pytest.approx(0.55)
    # the range is the prior's alone: about ±0.29 for 10 games' worth
    assert chance['low'] == pytest.approx(0.55 - 1.96 * math.sqrt(0.55 * 0.45 / 11))


def test_prop_probability_range_narrows_with_games():
    few = prop_probability(pd.Series([30.0, 10, 30, 10]), 20.5, 'Over', 0.5)
    many = prop_probability(pd.Series([30.0, 10] * 30), 20.5, 'Over', 0.5)
    assert many['high'] - many['low'] < few['high'] - few['low']


def test_prop_probability_shrinks_small_samples():
    values = pd.Series([30.0] * 10)
    chance = prop_probability(values, 20.5, 'Over', 0.5, prior_games=10)
    assert chance['hit'] == pytest.approx(0.75)        # (10 + 10 * 0.5) / 20, not 100%
    # every game far above the line: a Poisson around 30 is above 20.5 almost always, shrunk like the hit rate
    assert chance['dist'] == pytest.approx(0.5 * count_over(30, 0, 20.5) + 0.25) and chance['dist'] < 0.75
    assert chance['low'] < chance['p'] < chance['high']
    under = prop_probability(values, 20.5, 'Under', 0.5, prior_games=10)
    assert under['hit'] == pytest.approx(0.25)


def test_prop_probability_moves_with_the_adjusted_mean():
    values = pd.Series([18.0, 22, 19, 21, 20, 23, 17])
    usual = prop_probability(values, 20.5, 'Over', 0.5)
    boosted = prop_probability(values, 20.5, 'Over', 0.5, mean=24)
    assert boosted['p'] > usual['p'] and boosted['hit'] == usual['hit']


def test_prop_probability_whole_line_pushes():
    values = pd.Series([19.0, 20, 21, 20, 20])
    over = prop_probability(values, 20, 'Over', 0.5)
    under = prop_probability(values, 20, 'Under', 0.5)
    # before the market prior: P(over) + P(under) + P(push) = 1, the push being exactly 20
    weight = 5 / 15
    raw_over, raw_under = ((over['dist'] - 0.5 * (1 - weight)) / weight, (under['dist'] - 0.5 * (1 - weight)) / weight)
    push = count_over(20, 0.5, 19.5) - count_over(20, 0.5, 20)
    assert raw_over + raw_under + push == pytest.approx(1)
    assert push > 0.05


def test_count_over():
    stats = pytest.importorskip('scipy.stats')
    assert count_over(1.8, 1.2, 2.5) == pytest.approx(1 - stats.poisson.cdf(2, 1.8))            # var < mean
    r = 1.8 ** 2 / (3.0 - 1.8)
    assert count_over(1.8, 3.0, 1.5) == pytest.approx(1 - stats.nbinom.cdf(1, r, r / (r + 1.8)))
    assert count_over(25.0, 40.0, 24.5) == pytest.approx(1 - stats.nbinom.cdf(24, 25 ** 2 / 15, 25 / 40))
    assert count_over(0.4, 0.2, -0.5) == 1.0


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


def test_absence_adjustments_match_shrunk_matrix():
    logs = _team_logs()
    adj = absence_adjustments(logs, [1, 2], [3], ['PTS'], shrink=2)
    assert adj.loc[1, 'PTS'] == pytest.approx(10 * 2 / (2 + 2))
    assert adj.loc[2, 'PTS'] == 0


def test_rotowire_team_splits_starters_out_and_questionable():
    lineups = pd.DataFrame({'team': ['a'] * 8 + ['b'],
                            'role': ['starter'] * 5 + ['may_not_play'] * 3 + ['starter'],
                            'play_pct': [100] * 5 + [0, 50, 25] + [100],
                            'player_id_ESPN': [1, 2, 3, 4, None, 6, 7, 8, 9]})
    rw = rotowire_team(lineups, 'a')
    assert rw == {'starters': [1, 2, 3, 4], 'out': [6, 8], 'questionable': [7]}


def _games(rows):
    cols = ['game_id', 'date', 'season_id', 'season_type', 'home', 'away', 'home_score', 'away_score']
    df = pd.DataFrame(rows, columns=cols)
    for side in ('home', 'away'):   # identical box-score totals -> 100 possessions per team
        df[f'{side}_FGA'], df[f'{side}_FTA'], df[f'{side}_TO'], df[f'{side}_OREB'] = 90, 0, 20, 10
    df['date'] = pd.to_datetime(df['date'])
    return df


def test_game_projection_and_probabilities():
    games = _games([('1', '2025-01-01', 2025, 'regular', 'a', 'b', 120, 100),
                    ('2', '2025-01-02', 2025, 'regular', 'b', 'a', 100, 120)])
    ratings = blended_ratings(games.iloc[0:0], games, regress=0)
    assert ratings.loc['a', 'off_rtg'] == 120 and ratings.loc['b', 'def_rtg'] == 120
    p = game_projection(ratings, 'a', 'b', home_court=2)
    # league average rating 110, pace 100: a scores 120 + 120 - 110 = 130 (+1 home), b 100 + 100 - 110 = 90 (-1)
    assert (p['home_pts'], p['away_pts']) == (pytest.approx(131), pytest.approx(89))
    assert model_probability(p, 'ML', 'home', None) + model_probability(p, 'ML', 'away', None) == pytest.approx(1)
    assert model_probability(p, 'SPREAD', 'home', -42) == pytest.approx(0.5)
    assert model_probability(p, 'TOTAL', 'over', 220) == pytest.approx(0.5)
    edges = market_edges(p, pd.DataFrame({'market': ['TOTAL'], 'side': ['under'], 'line': [220.0], 'odds': [2.5]}))
    assert edges['edge pp'].iloc[0] == pytest.approx(50 - 40)


def test_blended_ratings_weights_current_season_by_games():
    prior = _games([('1', '2025-01-01', 2025, 'regular', 'a', 'b', 120, 100)])
    current = _games([('2', '2026-01-01', 2026, 'regular', 'a', 'b', 100, 100)])
    r = blended_ratings(current, prior, prior_games=1, regress=0)   # 1 current game -> weight 1/2
    assert r.loc['a', 'off_rtg'] == pytest.approx(110) and r.loc['a', 'games'] == 1


def test_absence_impact_uses_games_inside_stint():
    logs = _team_logs()
    logs['Date'] = pd.to_datetime(logs['Date'])
    games = _games([(str(g), f'2025-01-0{g}', 2025, 'regular', 'a', 'x', 100 + (10 if g in (4, 5) else 0), 100)
                    for g in range(1, 7)])
    imp = absence_impact(games, logs, 'a', 3, shrink=2)        # 3 missed games 4-5, team scored 10 more
    assert (imp['n_without'], imp['n_with']) == (2, 4)
    assert imp['pts_for'] == pytest.approx(10 * 2 / 4) and imp['pts_against'] == 0


# --- the cost contract (phase 1) ---

def test_break_even_in_both_profiles():
    from metrics import LEGACY, SUPERBET_STANDARD, break_even
    assert 100 * break_even(1.84, LEGACY) == pytest.approx(54.35, abs=0.01)
    assert 100 * break_even(1.84, SUPERBET_STANDARD) == pytest.approx(61.76, abs=0.01)
    # with a push in play, the win chance needed shrinks by the push chance
    assert break_even(2.0, LEGACY, p_push=0.1) == pytest.approx(0.45)


def test_expected_return_counts_a_push_as_neither():
    from metrics import LEGACY, SUPERBET_STANDARD, expected_return_100
    # 45% win, 10% push, 45% loss at 2.0: plain odds break even exactly
    assert expected_return_100(0.45, 2.0, LEGACY, p_push=0.10) == pytest.approx(0.0)
    assert expected_return_100(0.45, 2.0, SUPERBET_STANDARD, p_push=0.10) == pytest.approx(100 * (0.45 * 1.76 + 0.1 - 1))
    assert expected_return_100(0.5, 1.84, SUPERBET_STANDARD) == pytest.approx(100 * (0.5 * 0.88 * 1.84 - 1))


def test_a_push_settles_the_same_in_both_profiles():
    from metrics import LEGACY, SUPERBET_STANDARD, side_profit
    result = pd.Series(['win', 'loss', 'push', 'void', np.nan])
    legacy, std = side_profit(result, [1.84] * 5, LEGACY), side_profit(result, [1.84] * 5, SUPERBET_STANDARD)
    assert legacy.tolist()[:4] == pytest.approx([0.84, -1.0, 0.0, 0.0])
    assert std.tolist()[:4] == pytest.approx([0.88 * 1.84 - 1, -1.0, 0.0, 0.0])
    assert np.isnan(legacy.iloc[4]) and np.isnan(std.iloc[4])
    assert side_profit(result, [1.84] * 5).tolist()[:4] == legacy.tolist()[:4]      # the default stays legacy


def test_the_higher_expected_return_wins_over_the_bigger_edge_in_pp():
    from metrics import LEGACY, best_by_ev, break_even, expected_return_100
    a = {'name': 'A', 'p_win': 0.23, 'odds': 5.0}       # edge +3 pp, expected return +15
    b = {'name': 'B', 'p_win': 0.72, 'odds': 1.5}       # edge +5.3 pp, expected return +8
    edge = lambda c: 100 * (c['p_win'] - break_even(c['odds'], LEGACY))
    assert edge(b) > edge(a)
    assert expected_return_100(a['p_win'], a['odds'], LEGACY) > expected_return_100(b['p_win'], b['odds'], LEGACY)
    assert best_by_ev([b, a], LEGACY)['name'] == 'A'
    assert best_by_ev([{'p_win': np.nan, 'odds': 2.0}]) is None


def test_game_markets_and_props_share_the_cost_contract():
    from metrics import ACTIVE_PROFILE, break_even, market_edges
    projection = {'home_pts': 112.0, 'away_pts': 108.0, 'margin': 4.0, 'total': 220.0, 'pace': 99.0}
    odds = pd.DataFrame([{'event_id': 1, 'market': 'TOTAL', 'side': 'over', 'line': 219.5, 'odds': 1.84},
                         {'event_id': 1, 'market': 'TOTAL', 'side': 'under', 'line': 219.5, 'odds': 1.84},
                         {'event_id': 1, 'market': 'SPREAD', 'side': 'home', 'line': -3.5, 'odds': 1.70},
                         {'event_id': 1, 'market': 'SPREAD', 'side': 'away', 'line': 3.5, 'odds': 2.10}])
    edges = market_edges(projection, odds)
    assert (edges['cost profile'] == ACTIVE_PROFILE).all()
    assert edges['break-even net %'].tolist() == pytest.approx((100 * break_even(odds['odds'])).tolist())
    # the legacy edge keeps the margin; market % takes it out pair by pair
    assert edges.loc[0, 'implied %'] == pytest.approx(100 / 1.84)
    assert edges.loc[0, 'market %'] == pytest.approx(50.0)
    assert edges.loc[2, 'market %'] == pytest.approx(100 * (1 / 1.7) / (1 / 1.7 + 1 / 2.1))
    assert edges['edge net pp'].tolist() == pytest.approx((edges['model %'] - edges['break-even net %']).tolist())


def test_reprice_net_under_the_no_tax_promotion():
    from metrics import SUPERBET_NO_TAX, SUPERBET_STANDARD, reprice_net
    table = pd.DataFrame({'p win %': [55.0], 'side odds': [1.9], 'p push %': [0.0], 'ev net 100': [-8.0],
                          'break-even net %': [59.8], 'edge net pp': [-4.8], 'cost profile': [SUPERBET_STANDARD]})
    out = reprice_net(table, SUPERBET_NO_TAX)
    assert out['ev net 100'].iloc[0] == pytest.approx(100 * (0.55 * 1.9 - 1))
    assert out['break-even net %'].iloc[0] == pytest.approx(100 / 1.9)
    assert out['cost profile'].iloc[0] == SUPERBET_NO_TAX
    back = reprice_net(out, SUPERBET_STANDARD)
    assert back['ev net 100'].iloc[0] == pytest.approx(100 * (0.55 * 0.88 * 1.9 - 1))
