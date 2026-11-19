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
    assert not any('RotoWire: B' in t for t in texts(prop_reasons(out, games, _games([]))))
    assert any('RotoWire: B' in t for t in texts(prop_reasons(out | {'out_n': 4}, games, _games([]))))
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
    built = [t for t in texts(under, None) if t.startswith('How the estimate is built for Under')]
    assert len(built) == 1
    assert 'the price alone 47.9% (margin-free) → the calibration applied to the price alone 51.2% (+3.3 pp) → ' \
           'with the player\'s games and tonight\'s adjustments 51.9% (+0.7 pp)' in built[0]


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


# --- tonight's absences, teammate by teammate (audit F-02, F-14). Synthetic games: maths and logic only ---

PLAYER, B, C, D, E = 3100001, 3100002, 3100003, 3100004, 3100005


def _absence_logs():
    """Player PLAYER's 12 games. B misses games 4-6, C never misses one, D misses 6-8 and E misses game 2 (each
    inside his own stint, so they count as 'without him')."""
    pts = [20.0, 24, 18, 26, 30, 31, 28, 22, 27, 25, 19, 23]
    rows = [{'player_id_ESPN': PLAYER, 'game_id': g, 'PTS': p, 'MIN': 34.0} for g, p in enumerate(pts)]
    missed = {B: {4, 5, 6}, C: set(), D: {6, 7, 8}, E: {2}}
    rows += [{'player_id_ESPN': m, 'game_id': g, 'PTS': 10.0, 'MIN': 25.0}
             for m, out in missed.items() for g in range(12) if g not in out]
    logs = pd.DataFrame(rows).assign(team='nyk', season_id=2026, season_type='regular', OPP='BOS', type='home')
    return logs.assign(Date=pd.Timestamp('2026-10-01') + pd.to_timedelta(logs['game_id'] * 2, unit='D'))


def _absence_lineups(out):
    names = {B: 'B Mate', C: 'C Mate', D: 'D Rotowire', E: None}
    return pd.DataFrame({'player_id_ESPN': [PLAYER] + out, 'team': 'nyk',
                         'name': ['A Player'] + [names[o] for o in out],
                         'role': ['starter'] + ['may_not_play'] * len(out), 'play_pct': [100] + [0] * len(out),
                         'lineup_status': 'confirmed'})


def _absence_bet(out):
    from metrics import absence_adjustments
    from reasons import offer_context
    logs = _absence_logs()
    games = logs[logs['player_id_ESPN'] == PLAYER]
    adj = float(absence_adjustments(logs, [PLAYER], out, ['PTS']).loc[PLAYER, 'PTS'])
    avg = games['PTS'].mean()
    row = {'player_id': PLAYER, 'name': 'A Player', 'team': 'nyk', 'opp': 'bos', 'bet_type': 'PTS', 'line': 24.5,
           'side': 'Over', 'side odds': 1.9, 'p win %': 51.0, 'break-even net %': 59.8, 'edge net pp': -8.8,
           'ev net 100': -14.7, 'cost profile': 'superbet_standard', 'market over %': 50.0, 'avg': avg,
           'adj avg': avg + adj, 'lineup adj': adj, 'pace factor': 1.0, 'matchup factor': 1.0,
           'proj avg': avg + adj, 'RotoWire': 'starter', 'is_home': True, 'start_time': '2026-10-25T23:30:00Z'}
    names = {B: 'B Mate', C: 'C Mate'}                      # ESPN names: not D (RotoWire only), not E (nowhere)
    bet = offer_context(row, games, logs, _absence_lineups(out), names, '2026-10-25T20:00:00Z',
                        '2026-10-25T21:00:00Z', coef={'a': 1.0, 'b': 1.0, 'c': 0.0, 'd': 0.0})
    return bet, games, adj


def test_the_breakdown_adds_up_to_the_models_adjustment_and_matches_a_by_hand_count():
    from metrics import absence_breakdown
    logs = _absence_logs()
    rows = absence_breakdown(logs, PLAYER, [B, C, D, E], 'PTS')
    assert [r['estimated'] for r in rows] == [True, False, True, True] and np.isnan(rows[1]['change'])
    # by hand: (average without − average with) × n / (n + 5)
    pts = logs[logs['player_id_ESPN'] == PLAYER].set_index('game_id')['PTS']
    for r, out in zip([rows[0], rows[2], rows[3]], [{4, 5, 6}, {6, 7, 8}, {2}]):
        without, with_ = pts[list(out)].mean(), pts.drop(list(out)).mean()
        assert r['n_without'] == len(out)
        assert r['change'] == pytest.approx((without - with_) * len(out) / (len(out) + 5))
    _, _, adj = _absence_bet([B, C, D, E])
    assert sum(r['change'] for r in rows if r['estimated']) == pytest.approx(adj, abs=1e-12)


@pytest.mark.parametrize('lang', ['en', 'pl'])
def test_an_applied_absence_adjustment_is_always_explained(lang):
    import re
    bet, games, adj = _absence_bet([B, C, D, E])
    assert adj != 0 and bet['out_n'] == 1                         # the fewest games without an ESTIMATED teammate
    assert bet['out_names'] == ['B Mate', 'C Mate', 'D Rotowire'] and bet['out_unmatched'] == 1
    reasons = prop_reasons(bet, games, games.iloc[0:0], lang)
    mates = [r for r in reasons if r['group'] == 'availability' and r['kind'] == 'driver']
    assert len(mates) == 1 and mates[0]['n'] == 1 and mates[0]['value'] == pytest.approx(bet['avg'] + adj)
    text = mates[0]['text']
    assert not re.search(r'\d{5,}', text), text                     # never a raw ESPN id
    if lang == 'en':
        assert text.startswith("Out per RotoWire: B Mate, C Mate, D Rotowire, 1 player without a matched name.")
        assert f"adds {adj:+.1f} PTS" in text and "one with/without difference per teammate" in text
        assert "(3 games without him)" in text and "a player without a matched name" in text
        assert "No games without C Mate: their effect is unknown" in text
        assert "games without them" not in text                     # no joint split is computed (F-14)
    else:
        assert text.startswith("Nie grają (RotoWire): B Mate, C Mate, D Rotowire, 1 zawodnik bez dopasowanego")
        assert "(3 mecze bez niego)" in text and "(1 mecz bez niego)" in text and "Brak meczów bez: C Mate" in text


@pytest.mark.parametrize('lang', ['en', 'pl'])
def test_absences_without_any_estimate_are_a_warning_not_a_zero_effect(lang):
    bet, games, adj = _absence_bet([C])
    assert adj == 0 and bet['out_n'] is None
    reasons = prop_reasons(bet, games, games.iloc[0:0], lang)
    assert not [r for r in reasons if r['group'] == 'availability' and r['kind'] == 'driver']
    warning = [r for r in reasons if r['kind'] == 'warning' and r['group'] == 'availability']
    assert len(warning) == 1
    assert ("effect is unknown, not zero" if lang == 'en' else "nieznany, a nie zerowy") in warning[0]['text']


@pytest.mark.parametrize('lang', ['en', 'pl'])
def test_the_hit_rate_says_which_rate_the_model_uses_and_what_the_range_is(lang):
    long = prop_reasons(_bet(), _games([22.0, 25, 27, 24, 21, 26, 23, 28, 25, 24, 22, 26]), _games([]), lang)
    text = [r for r in long if r['group'] == 'history'][0]['text']
    if lang == 'en':
        assert "Over in 10 of the last 10 games (100%; 95% range of this past rate" in text
        assert "12 of all 12" in text and "The model uses the rate over all 12 games" in text
        assert "The model uses this rate" not in text and "after costs" in text
    else:
        assert "95% przedział tej historycznej częstości" in text and "ze wszystkich 12 meczów" in text
    short = prop_reasons(_bet(), _games([22.0, 25, 27, 24, 21, 26, 23, 28]), _games([]), lang)
    text = [r for r in short if r['group'] == 'history'][0]['text']
    assert ("(the whole sample)" if lang == 'en' else "(to cała próba)") in text
    assert ("over all 8 games" if lang == 'en' else "ze wszystkich 8 meczów") in text


def test_a_mixed_sample_is_disclosed_with_the_projection_too():
    games = _games([25.0] * 12).assign(top_up=[True] * 3 + [False] * 9,
                                       season_type=['pre'] * 2 + ['regular'] * 10)
    reasons = prop_reasons(_bet(), games, _games([]))
    expected = [r for r in reasons if r['group'] == 'projection'][0]['text']
    assert "3 of the games are from last season" in expected and "2 are preseason" in expected



# --- audit package D: the estimate without false precision (F-03, F-17) ---

@pytest.mark.parametrize('lang', ['en', 'pl'])
def test_the_price_reasons_say_estimate_and_build_it_step_by_step(lang):
    impacts = {'final': 49.5, 'price': 46.4, 'beyond_price': 3.1}
    reasons = prop_reasons(_bet(side='Under', impacts=impacts, **{'market over %': 53.1}), _games([25.0] * 12),
                           _games([]), lang)
    econ = [r['text'] for r in reasons if r['kind'] == 'economics']
    assert econ[0].startswith('The model estimates Under' if lang == 'en' else 'Model szacuje Poniżej')
    assert ('estimated EV' if lang == 'en' else 'szacowane EV') in econ[0]
    assert '46.9%' in econ[1] and '46.4% (-0.5 pp)' in econ[1] and '49.5% (+3.1 pp)' in econ[1]
    for text in econ:
        assert 'wins' not in text and 'wygrywa' not in text and '1/6' not in text and 'independent' not in text


def test_the_validation_labels_tell_not_tested_from_no_added_value():
    import i18n
    assert i18n.t('panel.validation.untested', 'pl') == 'Nieprzetestowane'
    assert i18n.t('panel.validation.no_lift', 'pl') == 'W dotychczasowym teście nie wykazano dodatkowej wartości'
    assert i18n.t('panel.validation.no_lift', 'en') == 'In the test so far, no added value was shown'
    note = i18n.t('panel.economics_note', 'en')
    assert 'point estimate' in note and "covers only the sampling noise" in note


def test_the_estimates_steps_add_up_as_shown():
    impacts = {'final': 49.457, 'price': 46.431, 'beyond_price': 3.026}
    reasons = prop_reasons(_bet(side='Under', impacts=impacts, **{'market over %': 53.135}), _games([25.0] * 12),
                           _games([]))
    built = [r['text'] for r in reasons if r['kind'] == 'economics'][1]
    assert '46.9% (margin-free)' in built and '46.4% (-0.5 pp)' in built and '49.5% (+3.1 pp)' in built
