"""Night curiosities and streaks against Superbet's lines (insights.py). Run with: python -m pytest dashboard"""
import numpy as np
import pandas as pd

import pytest

from insights import line_streaks, night_curiosities, spot_on_stats, tonight_streaks


def _lines(results, player=1, stat='REB', line=7.5, status=None):
    """Settled lines of one player and stat on consecutive nights; results: the actual values in date order."""
    n = len(results)
    return pd.DataFrame({'player_id': pd.array([player] * n, dtype='Int64'), 'name': ['Doe, John'] * n,
                         'bet_type': [stat] * n, 'game_date': pd.date_range('2026-10-21', periods=n),
                         'line': [line] * n, 'last line': [line] * n, 'actual': results,
                         'status': status or ['settled'] * n})


def test_streak_counts_the_current_run_against_the_last_line():
    s = line_streaks(_lines([9, 5, 6, 4, 7, 3]))                      # Over, then 5 Unders
    assert len(s) == 1 and s.loc[0, 'side'] == 'Under' and s.loc[0, 'n'] == 5
    assert s.loc[0, 'since'] == pd.Timestamp('2026-10-22') and s.loc[0, 'last line'] == 7.5
    moved = _lines([5, 6, 4, 7]).assign(**{'last line': [7.5, 7.5, 7.5, 6.5]})   # the line moved before tip-off
    assert line_streaks(moved).empty                                  # 7 > 6.5: the last one went Over


def test_streak_breaks_on_a_push_skips_voids_and_needs_the_minimum():
    assert line_streaks(_lines([5, 6, 4, 6], line=6)).empty           # the last one is a push
    assert line_streaks(_lines([5, 6, 6, 5, 4, 3], line=6)).empty     # 3 Unders since the last push
    void = _lines([3, 4, np.nan, 5, 6], status=['settled', 'settled', 'void', 'settled', 'settled'])
    assert line_streaks(void).loc[0, 'n'] == 4                        # the void night is skipped
    assert line_streaks(_lines([3, 4, 5])).empty                      # 3 in a row: below the minimum
    assert line_streaks(_lines([3, 4, 5]), min_len=3).loc[0, 'n'] == 3


def test_streaks_are_per_player_and_stat_and_only_main_stats():
    rows = pd.concat([_lines([9, 9, 9, 9]), _lines([1, 1, 1, 1], stat='AST', line=4.5),
                      _lines([9, 9, 9, 9], player=2), _lines([0, 0, 0, 0], stat='PF', line=2.5)])
    s = line_streaks(rows).set_index(['player_id', 'bet_type'])
    assert set(s.index) == {(1, 'REB'), (1, 'AST'), (2, 'REB')}       # no fouls
    assert s.loc[(1, 'AST'), 'side'] == 'Under' and s.loc[(2, 'REB'), 'side'] == 'Over'


def test_tonight_streaks_keep_only_players_with_that_line_tonight():
    streaks = line_streaks(pd.concat([_lines([3, 3, 3, 3]), _lines([9, 9, 9, 9], player=2)]))
    tonight = pd.DataFrame({'player_id': [1.0, 2.0], 'bet_type': ['REB', 'PTS'], 'line': [6.5, 20.5],
                            'name': ['John Doe', 'Jim Roe'], 'event_id': [10, 11], 'name_ESPN': ['John Doe', 'Jim Roe']})
    tonight['opp'], tonight['matchup_info'] = ['mia', 'bos'], [{'ratio': 1.12, 'group': 'F'}, {}]
    out = tonight_streaks(streaks, tonight)
    assert len(out) == 1 and out.loc[0, 'name'] == 'John Doe' and out.loc[0, 'tonight line'] == 6.5
    assert out.loc[0, 'opp'] == 'mia' and out.loc[0, 'matchup_info']['group'] == 'F'   # tonight's opponent
    assert tonight_streaks(streaks, tonight.iloc[0:0]).empty


def test_night_curiosities():
    props = pd.DataFrame({'name': ['A', 'B', 'C', 'D', 'E', 'F'],
                          'bet_type': ['PTS', 'PTS', 'REB', 'REB', 'FTA', 'AST'],
                          'status': ['settled'] * 5 + ['void'], 'line': [20.5, 15.5, 7.5, 5.5, 4.5, 6.5],
                          'proj_avg': [21.0, 14.0, 8.0, np.nan, 4.0, 6.0], 'actual': [35, 14, 8, 15, 12, np.nan]})
    games = pd.DataFrame({'game': ['X @ Y', 'Z @ W'], 'total error': [-12.0, 2.5], 'margin error': [1.0, -8.0]})
    c = night_curiosities(props, games, spot_on=2)
    assert c['surprises']['name'].tolist() == ['A', 'C']              # one per stat, biggest first; D has no projection
    assert c['spot_on']['name'].tolist() == ['B', 'C']                # both exact: ties by stat
    assert c['line_miss']['name'] == 'A'                              # 35 vs 20.5; FTA isn't a main stat
    assert c['best_total']['game'] == 'Z @ W' and c['best_margin']['game'] == 'X @ Y'
    empty = night_curiosities(props.iloc[0:0], games.iloc[0:0])
    assert empty['surprises'].empty and empty['line_miss'] is None and empty['best_total'] is None


def test_spot_on_stats():
    props = pd.DataFrame({'bet_type': ['PTS', 'PTS', 'REB', '3PM', 'AST', 'FTA', 'REB'],
                          'status': ['settled'] * 6 + ['void'],
                          'actual': [30, 10, 8, 0, 5, 3, np.nan], 'proj_avg': [28.0, 14.0, 8.0, 0.4, 7.0, 3.0, 5.0],
                          'line': [24.5, 10.5, 7.5, 0.5, 6.0, 2.5, 5.5]})
    s = spot_on_stats(props)
    assert s['lines'] == 5                                            # no FTA, no void
    # ours as half-point lines within 10%: 30 vs 28.5 (≤3), 8 vs 8.5 (≤0.8), 0 vs 0.5 (the floor); 10 vs 14.5 no
    # the line: 10 vs 10.5, 8 vs 7.5, 0 vs 0.5
    assert s['our spot %'] == pytest.approx(60) and s['line spot %'] == pytest.approx(60)
    # closer: we in PTS 30, REB and 3PM, the line in PTS 10 and AST; no tie
    assert s['closer %'] == pytest.approx(60) and s['line closer %'] == pytest.approx(40) and s['tie %'] == 0
    assert s['we closer'] == ['REB', '3PM'] and s['line closer'] == ['AST']   # PTS: one each
    assert s['bias'] == pytest.approx((2 - 4 + 0 - 0.4 - 2) / 5)     # < 0: we expected too much
    assert s['over %'] == pytest.approx(40)                           # 30 > 24.5, 8 > 7.5
    assert spot_on_stats(props.iloc[0:0]) == {} and spot_on_stats(props[props['bet_type'] == 'FTA']) == {}
