"""Run with: python -m pytest dashboard"""
import numpy as np
import pandas as pd
import pytest

from metrics import context_factor, game_lines, matchup, matchup_verdict
from reasons import game_reasons, prop_reasons, verdict


def _games(pts, minutes=None, season_type='regular'):
    n = len(pts)
    return pd.DataFrame({'PTS': pts, 'MIN': minutes or [32.0] * n, 'type': ['home', 'away'] * (n // 2) + ['home'] * (n % 2),
                         'season_type': season_type, 'rest_days': [2.0] * n, 'starter': True,
                         'game_label': [f"g{i}" for i in range(n)]})


def _bet(**kw):
    bet = {'name': 'A Player', 'stat': 'PTS', 'side': 'Over', 'line': 20.5, 'odds': 1.9, 'model %': 60.0,
           'break-even %': 52.6, 'edge pp': 7.4, 'edge low': 1.0, 'avg': 24.0, 'proj avg': 24.0, 'opp': 'bos',
           'team': 'nyk'}
    return bet | kw


def texts(reasons, supports=None, flag=None):
    return [r['text'] for r in reasons if (supports is None or r['supports'] is supports)
            and (flag is None or r['flag'] is flag)]


def test_supports_are_plain_bools():
    reasons = prop_reasons(_bet(), _games([25.0] * 12), _games([]))
    assert all(r['supports'] in (True, False, None) and not isinstance(r['supports'], np.bool_) for r in reasons)


def test_strong_over_is_a_bet():
    reasons = prop_reasons(_bet(), _games([22.0, 25, 27, 24, 21, 26, 23, 28, 25, 24, 22, 26]), _games([]))
    assert any('in 12 of all 12 games' in t for t in texts(reasons, True))
    assert not texts(reasons, flag=True)
    assert verdict(reasons, 7.4, 1.0)[0] == 'Bet'


def test_same_numbers_read_the_other_way_for_an_under():
    reasons = prop_reasons(_bet(side='Under'), _games([22.0, 25, 27, 24, 21, 26, 23, 28, 25, 24, 22, 26]), _games([]))
    assert any('Expected 24.0' in t for t in texts(reasons, False))


def test_flags_mean_pass():
    reasons = prop_reasons(_bet(play_pct=50, status='Ques 50%'), _games([25.0] * 4, season_type='pre'), _games([]))
    flagged = texts(reasons, flag=True)
    assert any('Only 4 games' in t for t in flagged)
    assert any('preseason' in t for t in flagged)
    assert any('Ques 50%' in t for t in flagged)
    assert verdict(reasons, 20, 10)[0] == 'Pass'


def test_unstable_minutes_and_line_moving_against_are_flags():
    minutes = [10.0, 35, 12, 34, 8, 36, 30, 9]
    reasons = prop_reasons(_bet(line_move=-2.0), _games([25.0] * 8, minutes), _games([]))
    flagged = texts(reasons, flag=True)
    assert any('Minutes swing' in t for t in flagged)
    assert any('against the pick' in t for t in flagged)


def test_context_reasons():
    m = {'value': 60.0, 'average': 54.0, 'diff': 6.0, 'ratio': 60 / 54, 'rank': 2, 'teams': 30, 'word': 'soft',
         'colour': 'green'}
    reasons = prop_reasons(_bet(matchup=m, position='G', implied=120, team_pts=110, spread=-12.5, starter=True,
                                lineup_adj=0), _games([25.0] * 12), _games([24.0, 26.0]))
    assert any('soft matchup' in t for t in texts(reasons, True))
    assert any('higher-scoring' in t for t in texts(reasons, True))
    assert any('blowout' in t for t in texts(reasons, False))
    assert any('Against BOS' in t for t in texts(reasons, True))


def test_verdict_levels():
    pro = {'supports': True, 'text': '', 'flag': False}
    con = {'supports': False, 'text': '', 'flag': False}
    assert verdict([pro, pro, con], 5, 1)[0] == 'Bet'
    assert verdict([pro, pro, con], 5, -3)[0] == 'Lean'
    assert verdict([pro, con, con], 5, 1)[0] == 'Pass'
    assert verdict([pro, pro], -1, -5)[0] == 'Pass'
    assert verdict([pro, pro], 6)[0] == 'Bet'          # no range: needs 5+ pp


def test_game_reasons_for_a_total():
    ratings = pd.DataFrame({'off_rtg': [118.0, 110.0], 'def_rtg': [112.0, 116.0], 'pace': [104.0, 100.0],
                            'games': [20, 20]}, index=['a', 'b'])
    projection = {'home_pts': 120.0, 'away_pts': 112.0, 'margin': 8.0, 'total': 232.0, 'pace': 103.0}
    outcome = {'market': 'TOTAL', 'side': 'over', 'line': 225.5, 'odds': 1.9, 'model %': 64.0, 'implied %': 52.6,
               'edge pp': 11.4}
    ctx = {'projection': projection, 'ratings': ratings, 'home': 'a', 'away': 'b', 'home_court': 1.5,
           'absences': {'a': [], 'b': []}, 'games_played': {'a': 20, 'b': 20}, 'rotowire': True}
    reasons = game_reasons(outcome, ctx)
    assert any('Projected 232.0' in t for t in texts(reasons, True))
    assert not texts(reasons, flag=True)
    assert verdict(reasons, 11.4)[0] == 'Bet'
    spread = game_reasons({**outcome, 'market': 'SPREAD', 'side': 'away', 'line': 5.5}, ctx)
    assert any('missing +5.5 by 2.5' in t for t in texts(spread, False))


def test_matchup_and_context_factor():
    allowed = pd.DataFrame({'G': [60.0, 50.0, 55.0], 'F': [40.0, 40.0, 40.0], 'C': [20.0, 20.0, 20.0]},
                           index=['a', 'b', 'c'])
    m = matchup(allowed, 'a', 'G')
    assert m['rank'] == 1 and m['word'] == 'soft' and m['ratio'] == pytest.approx(60 / 55)
    assert matchup(allowed, 'zzz', 'G') == {} and matchup(allowed, 'a', None) == {}
    assert matchup_verdict(0, 50)[0] == 'average'
    assert context_factor(1.1) == pytest.approx(1.05)
    assert context_factor(2.0) == pytest.approx(1.08)    # capped
    assert context_factor(np.nan) == 1.0


def test_game_lines_implied_totals():
    main = pd.DataFrame([
        {'event_id': 1, 'market': 'SPREAD', 'side': 'home', 'line': -6.0, 'odds': 1.9},
        {'event_id': 1, 'market': 'SPREAD', 'side': 'away', 'line': 6.0, 'odds': 1.9},
        {'event_id': 1, 'market': 'TOTAL', 'side': 'over', 'line': 220.0, 'odds': 1.9},
        {'event_id': 1, 'market': 'TOTAL', 'side': 'under', 'line': 220.0, 'odds': 1.9},
    ])
    lines = game_lines(main)
    assert lines.loc[1, 'home_implied'] == 113 and lines.loc[1, 'away_implied'] == 107
