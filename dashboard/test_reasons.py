"""Run with: python -m pytest dashboard"""
import numpy as np
import pandas as pd
import pytest

from metrics import context_factor, game_lines, matchup, matchup_verdict
from reasons import complete, game_reasons, prop_reasons


def _games(pts, minutes=None, season_type='regular'):
    n = len(pts)
    return pd.DataFrame({'PTS': pts, 'MIN': minutes or [32.0] * n, 'type': ['home', 'away'] * (n // 2) + ['home'] * (n % 2),
                         'season_type': season_type, 'rest_days': [2.0] * n, 'starter': True,
                         'game_label': [f"g{i}" for i in range(n)],
                         'Date': pd.date_range('2026-10-01', periods=n, freq='2D')})


def _bet(**kw):
    bet = {'name': 'A Player', 'stat': 'PTS', 'side': 'Over', 'line': 20.5, 'odds': 1.9, 'model %': 60.0,
           'break-even %': 52.6, 'edge pp': 7.4, 'edge low': 1.0, 'avg': 24.0, 'proj avg': 24.0, 'opp': 'bos',
           'team': 'nyk', 'odds_at': '2026-10-30T21:23:24Z', 'stats_through': pd.Timestamp('2026-10-29')}
    return bet | kw


def texts(reasons, supports=None, flag=None):
    return [r['text'] for r in reasons if (supports is None or r['supports'] is supports)
            and (flag is None or r['flag'] is flag)]


def test_supports_are_plain_bools():
    reasons = prop_reasons(_bet(), _games([25.0] * 12), _games([]))
    assert all(r['supports'] in (True, False, None) and not isinstance(r['supports'], np.bool_) for r in reasons)


def test_every_reason_says_its_value_reference_observations_time_and_source():
    reasons = prop_reasons(_bet(), _games([22.0, 25, 27, 24, 21, 26, 23, 28, 25, 24, 22, 26]), _games([]))
    history = [r for r in reasons if r['group'] == 'history']
    assert len(history) == 1 and 'Over in 10 of the last 10 games' in history[0]['text']
    assert '12 of all 12' in history[0]['text'] and history[0]['supports'] is None
    assert not texts(reasons, flag=True)
    for r in reasons:
        assert r['direction'] in ('for', 'against', None)
        assert r['kind'] in ('economics', 'driver', 'context', 'warning', 'blocker')
        assert all(r[k] is not None for k in ('value', 'reference', 'as_of', 'source')), r['text']
        if r['kind'] != 'economics' and r['group'] != 'market':
            assert r['n'] >= 1, r['text']


def test_no_data_means_no_reason():
    games = _games([25.0] * 12)
    # tonight's rest is known but not the opponent's: nothing to compare it with
    assert not any('Rest days' in t for t in texts(prop_reasons(_bet(rest_days=1), games, _games([]))))
    rested = prop_reasons(_bet(rest_days=1, opp_rest=3), games, _games([]))
    assert any('Rest days: NYK 1, BOS 3+' in t for t in texts(rested, None))
    # odds without a fetch time: the model's reason isn't made
    assert not any(t.startswith('Model:') for t in texts(prop_reasons(_bet(odds_at=None), games, _games([]))))
    # teammates out without the games behind the change: no reason
    out = _bet(**{'lineup adj': 2.0, 'out_names': ['B'], 'lineup_at': '2026-10-30T20:00:00Z'})
    assert not any('B out' in t for t in texts(prop_reasons(out, games, _games([]))))
    assert any('B out' in t for t in texts(prop_reasons(out | {'out_n': 4}, games, _games([]))))
    assert not complete({'flag': False, 'kind': 'context', 'group': None, 'value': 1.0, 'reference': 2.0, 'n': 0,
                         'as_of': 'x', 'source': 'ESPN'})
    # the price needs no game count
    assert complete({'flag': False, 'kind': 'economics', 'group': 'price', 'value': 1.0, 'reference': 2.0,
                     'n': None, 'as_of': 'x', 'source': 'model'})


def test_a_line_move_is_context_not_a_reason_for_the_offer():
    reasons = prop_reasons(_bet(open_line=19.5, snapshots=3), _games([25.0] * 12), _games([]))
    moved = [r for r in reasons if 'moved' in r['text'] and not r['flag']]
    assert len(moved) == 1 and moved[0]['supports'] is None and moved[0]['group'] == 'market'
    # the same line with other odds: the margin-free chance's move
    same = prop_reasons(_bet(open_line=20.5, open_over=2.0, open_under=1.8, over_odds=1.9, under_odds=1.9),
                        _games([25.0] * 12), _games([]))
    assert any('odds 2.00 → 1.90' in t and '47% → 50%' in t for t in texts(same, None))


def test_only_the_price_and_the_drivers_have_a_direction():
    games = _games([22.0, 25, 27, 24, 21, 26, 23, 28, 25, 24, 22, 26])
    m = {'value': 60.0, 'average': 54.0, 'diff': 6.0, 'ratio': 60 / 54, 'rank': 2, 'teams': 30, 'word': 'soft',
         'colour': 'green', 'games': 6}
    for side, impact, edge in (('Over', 0.4, 7.4), ('Under', -0.4, -3.0)):
        reasons = prop_reasons(_bet(side=side, matchup=m, position='G', home=True, **{'edge pp': edge},
                                    impacts={'opponent': impact}), games, _games([]))
        price = [r for r in reasons if r['kind'] == 'economics']
        assert price[0]['supports'] is (edge > 0)
        matchup_ = [r for r in reasons if r['group'] == 'opponent']
        assert matchup_[0]['kind'] == 'driver' and matchup_[0]['supports'] is (impact > 0)
        assert f"{impact:+.1f} pp" in matchup_[0]['text']
        assert all(r['supports'] is None for r in reasons if r['kind'] == 'context')
    # a driver that barely moves the chance has no direction
    tiny = prop_reasons(_bet(matchup=m, position='G', impacts={'opponent': 0.05}), games, _games([]))
    assert [r for r in tiny if r['group'] == 'opponent'][0]['supports'] is None
    assert 'less than 0.1 pp' in [r for r in tiny if r['group'] == 'opponent'][0]['text']


def test_the_price_alone_is_the_evaluated_sides():
    impacts = {'final': 51.9, 'price': 51.2, 'beyond_price': 0.7}
    under = prop_reasons(_bet(side='Under', impacts=impacts, **{'market over %': 52.1}), _games([25.0] * 12),
                         _games([]))
    assert any('Under 47.9% (margin-free), 51.2% after the calibration' in t and '+0.7 pp' in t
               for t in texts(under, None))


def test_context_is_for_or_against_only_when_it_predicted_results():
    games = _games([30.0, 20.0] * 6)          # 30 at home, 20 away
    lift = {'venue': {'status': 'lift', 'over_sign': 1}}
    venue = lambda reasons: [r for r in reasons if 'At home' in r['text']][0]
    assert venue(prop_reasons(_bet(home=True), games, _games([]), validation={}))['supports'] is None
    assert venue(prop_reasons(_bet(home=True), games, _games([]), validation={}))['validation'] == 'untested'
    assert venue(prop_reasons(_bet(home=True), games, _games([]), validation=lift))['supports'] is True
    assert venue(prop_reasons(_bet(home=True, side='Under'), games, _games([]), validation=lift))['supports'] is False
    no_lift = {'venue': {'status': 'no_lift', 'over_sign': 1}}
    assert venue(prop_reasons(_bet(home=True), games, _games([]), validation=no_lift))['supports'] is None
    # history against the opponent is shown only when it predicted results
    vs = _games([24.0, 26.0])
    assert not any('Against BOS' in t for t in texts(prop_reasons(_bet(), _games([25.0] * 12), vs, validation={})))
    assert any('Against BOS' in t for t in texts(prop_reasons(_bet(), _games([25.0] * 12), vs,
                                                             validation={'vs_opp': {'status': 'lift'}})))


def test_faithfulness_unused_inputs_have_no_impact():
    m = {'value': 60.0, 'average': 54.0, 'diff': 6.0, 'ratio': 60 / 54, 'rank': 2, 'teams': 30, 'word': 'soft',
         'colour': 'green', 'games': 6}
    reasons = prop_reasons(_bet(matchup=m, home=True, rest_days=2, opp_rest=1, impacts={'opponent': 0.3}),
                           _games([25.0] * 12), _games([]))
    for r in reasons:
        if not r['used_by_model']:
            assert r['impact_pp'] is None, r['text']


def test_driver_impacts():
    from reasons import driver_impacts
    coef = {'a': 1.224, 'b': 0.092, 'c': 0.0, 'd': 0.0}
    values = pd.Series([22.0, 25, 27, 24, 21, 26, 23, 28, 25, 24, 22, 26])
    over = driver_impacts(values, 24.5, 'Over', 0.5, 26.0, 2.0, 1.04, 1.06, coef)
    assert over['availability'] > 0 and over['environment'] > 0 and over['opponent'] > 0
    assert over['beyond_price'] == pytest.approx(over['final'] - over['price'])
    under = driver_impacts(values, 24.5, 'Under', 0.5, 26.0, 2.0, 1.04, 1.06, coef)
    assert under['opponent'] < 0
    assert over['final'] + under['final'] == pytest.approx(100)          # a half line: the sides are complements
    # an input left at its neutral value moves nothing
    flat = driver_impacts(values, 24.5, 'Over', 0.5, 24.0, 0.0, 1.0, np.nan, coef)
    assert flat['availability'] == flat['environment'] == flat['opponent'] == 0


def test_calibrated_sides_are_complements_on_a_half_line():
    from metrics import calibrate, prop_probability
    coef = {'a': 1.224, 'b': 0.092, 'c': 0.0, 'd': 0.0}
    values = pd.Series([3.0, 0, 2, 5, 1, 2, 4, 3, 0, 2])
    p = {side: calibrate(prop_probability(values, 2.5, side, m, mean=2.4)['p'], m, side, coef)
         for side, m in (('Over', 0.45), ('Under', 0.55))}
    assert p['Over'] + p['Under'] == pytest.approx(1)


def test_role_stint_and_lineup_warnings_dont_block():
    games = _games([25.0] * 12).assign(starter=False, team=['bkn'] * 6 + ['nyk'] * 6)
    reasons = prop_reasons(_bet(status='starter', lineup_status='expected'), games, _games([]))
    warned = [r['text'] for r in reasons if r['kind'] == 'warning']
    assert any('Started 0 of the last 10' in t for t in warned)
    assert any('Only 6 of the 12 games are with NYK' in t for t in warned)
    assert any('expected, not confirmed' in t for t in warned)
    assert all(not r['flag'] for r in reasons if r['kind'] == 'warning')
    assert any('Role: started 0 of the last 10' in t for t in texts(reasons, None))


def test_minutes_are_compared_within_the_current_team():
    minutes = [20.0] * 8 + [30.0] * 5
    games = _games([25.0] * 13, minutes).assign(team='nyk', PF=[2] * 13, Result=['W110-100'] * 13)
    reasons = prop_reasons(_bet(), games, _games([]))
    text = [t for t in texts(reasons) if t.startswith('Minutes:')][0]
    assert '30.0 per game in the last 5' in text and '20.0 in his 8 earlier games with NYK' in text
    traded = games.assign(team=['bkn'] * 4 + ['nyk'] * 9)
    text = [t for t in texts(prop_reasons(_bet(), traded, _games([]))) if t.startswith('Minutes:')][0]
    assert 'in his 4 earlier games with NYK' in text


def test_volume_only_for_shot_stats():
    games = _games([25.0] * 12).assign(team='nyk', FGA=[15] * 7 + [20] * 5, FGM=7, **{'3PA': 5, '3PM': 2,
                                                                                     'FTA': 4, 'FTM': 3})
    assert any(t.startswith('Shots per 36 min') for t in texts(prop_reasons(_bet(), games, _games([]))))
    reb = games.assign(REB=8.0)
    assert not any(t.startswith('Shots per 36 min') for t in
                   texts(prop_reasons(_bet(stat='REB', line=7.5), reb, _games([]))))


def test_blowout_is_context_with_the_players_own_minutes():
    games = _games([25.0] * 12).assign(Result=['W130-100', 'L100-104'] * 6, MIN=[28.0, 36.0] * 6)
    reasons = prop_reasons(_bet(spread=-12.5, starter=True), games, _games([]))
    blowout = [r for r in reasons if 'favoured by 12.5' in r['text']][0]
    assert blowout['supports'] is None and '28.0 min (6)' in blowout['text'] and '36.0 (6)' in blowout['text']


def test_offer_context_builds_what_the_reasons_need():
    from reasons import offer_context
    games = _games([25.0] * 12).assign(player_id_ESPN=1, team='nyk', position_group='G', OPP='BOS',
                                       game_id=range(12))
    opp = games.assign(player_id_ESPN=2, team='bos', Date=games['Date'] - pd.Timedelta(days=1),
                       game_id=range(100, 112))
    logs = pd.concat([games, opp], ignore_index=True)
    lineups = pd.DataFrame({'player_id_ESPN': [1, 3], 'team': ['nyk', 'nyk'], 'role': ['starter', 'may_not_play'],
                            'play_pct': [100, 0], 'lineup_status': ['expected', 'expected']})
    row = {'player_id': 1, 'name': 'A Player', 'team': 'nyk', 'opp': 'bos', 'bet_type': 'PTS', 'line': 24.5,
           'side': 'Over', 'side odds': 1.9, 'p win %': 51.0, 'break-even net %': 59.8, 'edge net pp': -8.8,
           'ev net 100': -14.7, 'cost profile': 'superbet_standard', 'market over %': 50.0, 'avg': 25.0,
           'adj avg': 25.0, 'lineup adj': 0.0, 'pace factor': 1.02, 'matchup factor': 1.0, 'proj avg': 25.5,
           'RotoWire': 'starter', 'is_home': True, 'start_time': '2026-10-25T23:30:00Z'}
    bet = offer_context(row, games, logs, lineups, {3: 'C Mate'}, '2026-10-25T20:00:00Z', '2026-10-25T21:00:00Z',
                        coef={'a': 1.224, 'b': 0.092, 'c': 0.0, 'd': 0.0})
    assert bet['out_names'] == ['C Mate'] and bet['lineup_status'] == 'expected' and bet['tax'] == pytest.approx(12)
    assert bet['rest_days'] == 2 and bet['opp_rest'] == 3 and bet['position'] == 'G' and bet['starter']
    assert bet['impacts']['environment'] > 0 and bet['impacts']['opponent'] == 0
    reasons = prop_reasons(bet, games, _games([]))
    assert reasons[0]['kind'] == 'economics' and 'after the 12% stake tax' in reasons[0]['text']


def test_flags_are_blockers():
    reasons = prop_reasons(_bet(play_pct=50, status='Ques 50%'), _games([25.0] * 4, season_type='pre'), _games([]))
    flagged = texts(reasons, flag=True)
    assert any('Only 4 games' in t for t in flagged)
    assert any('preseason' in t for t in flagged)
    assert any('Ques 50%' in t for t in flagged)


def test_unstable_minutes_and_line_moving_against_are_flags():
    minutes = [10.0, 35, 12, 34, 8, 36, 30, 9]
    reasons = prop_reasons(_bet(line_move=-2.0), _games([25.0] * 8, minutes), _games([]))
    flagged = texts(reasons, flag=True)
    assert any('Minutes swing' in t for t in flagged)
    assert any('against the pick' in t for t in flagged)


def test_game_reasons_for_a_total():
    ratings = pd.DataFrame({'off_rtg': [118.0, 110.0], 'def_rtg': [112.0, 116.0], 'pace': [104.0, 100.0],
                            'games': [20, 20]}, index=['a', 'b'])
    projection = {'home_pts': 120.0, 'away_pts': 112.0, 'margin': 8.0, 'total': 232.0, 'pace': 103.0}
    outcome = {'market': 'TOTAL', 'side': 'over', 'line': 225.5, 'odds': 1.9, 'model %': 64.0, 'implied %': 52.6,
               'edge pp': 11.4}
    ctx = {'projection': projection, 'ratings': ratings, 'home': 'a', 'away': 'b', 'home_court': 1.5,
           'absences': {'a': [], 'b': []}, 'games_played': {'a': 20, 'b': 20}, 'rotowire': True,
           'odds_at': '2026-10-30T21:23:24Z', 'stats_through': pd.Timestamp('2026-10-29')}
    reasons = game_reasons(outcome, ctx)
    assert any('Projected 232.0' in t for t in texts(reasons, True))
    assert not texts(reasons, flag=True)
    assert all(complete(r) for r in reasons)
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


# --- 🔴: red flags on whole tables ---

def test_prop_flags_each_rule():
    from reasons import prop_flags
    steady = pd.Series([32.0] * 12)
    assert prop_flags(12, False, np.nan, '', steady, np.nan, 'Over') == []
    assert prop_flags(5, False, np.nan, '', steady[:5], np.nan, 'Over')[0].startswith("Only 5 games")
    assert "preseason" in prop_flags(12, True, np.nan, '', steady, np.nan, 'Over')[0]
    assert prop_flags(12, False, 0, 'Out 0%', steady, np.nan, 'Over') == \
        ["RotoWire: Out 0%: won't play (the line is refunded)"]
    assert prop_flags(12, False, 50, 'Ques 50%', steady, np.nan, 'Over') == \
        ["RotoWire: Ques 50%: may sit or play limited minutes"]
    assert "Minutes swing" in prop_flags(12, False, np.nan, '', pd.Series([10.0, 35.0] * 6), np.nan, 'Over')[0]
    assert "against the pick" in prop_flags(12, False, np.nan, '', steady, -1.5, 'Over')[0]   # down hurts an Over
    assert prop_flags(12, False, np.nan, '', steady, -1.5, 'Under') == []                     # ...and helps an Under


def test_flag_props_turns_flagged_lines_red():
    from reasons import flag_props
    logs = pd.DataFrame({'player_id_ESPN': [1] * 10 + [2] * 3, 'MIN': 30.0, 'season_type': 'regular'})
    table = pd.DataFrame({'player_id': [1, 2, 1], 'best side': ['Over', 'Over', 'Under'], 'signal': ['🟢', '🟢', '🟡'],
                          'RotoWire': ['starter', 'bench', 'Ques 50%'], 'line move': [np.nan, np.nan, np.nan]})
    lineups = pd.DataFrame({'player_id_ESPN': [1], 'play_pct': [50]})
    lineups_none = pd.DataFrame(columns=['player_id_ESPN', 'play_pct'])
    out = flag_props(table.iloc[:2], logs, lineups_none)
    assert out['signal'].tolist() == ['🟢', '🔴'] and out['red flag'].iloc[1].startswith("Only 3 games")
    out = flag_props(table, logs, lineups)
    assert out['signal'].tolist() == ['🔴', '🔴', '🔴']                 # player 1 is questionable on RotoWire
    assert out['red flag'].iloc[2] == "RotoWire: Ques 50%: may sit or play limited minutes"


def test_game_outcomes_red_only_for_flags():
    from reasons import flag_game_outcomes
    edges = pd.DataFrame({'edge pp': [6.0, -8.0, 18.0]})
    settled = flag_game_outcomes(edges, games_played=20, rotowire=True)
    assert settled['signal'].tolist() == ['', '', '🔴']        # no 🟢 for an uncalibrated model; red for flags
    assert "Edge over 15 pp" in settled['red flag'].iloc[2]
    early = flag_game_outcomes(edges, games_played=2, rotowire=False)
    assert early['signal'].tolist() == ['🔴'] * 3 and "Early season" in early['red flag'].iloc[0]
