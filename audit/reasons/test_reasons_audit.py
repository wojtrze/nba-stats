"""Audit tests of the reasons (audit/reasons/RAPORT.md). Run: python -m pytest audit/reasons -q

SYNTHETIC FIXTURES: every DataFrame below is made up to check the maths and the logic only. None of it is an NBA
result or a Superbet price.

Convention:
- plain tests check a property independently (own formulas, scipy) and pass when the production code is right;
- xfail(strict=True) tests state what the audit expects where it found a confirmed defect (F-xx in the report):
  they fail today, and when the defect is fixed they pass, so pytest reports XPASS(strict) → remove the marker;
- 'documents' tests pin down current behaviour the report calls a communication issue (no xfail: the behaviour
  is intended, the wording is in question).
"""
import inspect
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path[:0] = [os.path.join(ROOT, 'dashboard'), os.path.join(ROOT, 'dashboard_v2'), ROOT]

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402
from scipy import stats as ss  # noqa: E402

import decisions  # noqa: E402
import i18n  # noqa: E402
import mispricing  # noqa: E402
from metrics import (break_even, calibrate, count_over, expected_return_100, no_vig,  # noqa: E402
                     prop_probability)
from reasons import driver_impacts, mispricing_reasons, prop_reasons  # noqa: E402

FITTED = {'a': 1.13929175107068, 'b': 0.17037486025776427, 'c': 0.0, 'd': 0.0}   # calibration.json of 2026-11-10
NOW = pd.Timestamp('2026-10-30T22:00:00Z')
FETCHED = '2026-10-30T21:23:24Z'


# ---------- independent re-implementation (audit's own code) ----------

def _logit(p):
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


def _sf(mean, var, line):
    k = math.floor(line)
    if var > mean * 1.0001:
        return float(ss.nbinom.sf(k, mean ** 2 / (var - mean), mean / var))
    return float(ss.poisson.sf(k, mean))


def _indep_raw(values, line, side, market, mean, prior=10):
    v = np.asarray(values, float)
    n = len(v)
    hits = (v > line).sum() if side == 'Over' else (v < line).sum()
    hit = (hits + prior * market) / (n + prior)
    var = v.var(ddof=1) * mean / v.mean()
    whole = float(line).is_integer()
    cut = line + 0.5 if whole and side == 'Over' else line - 0.5 if whole else line
    over = _sf(mean, var, cut)
    w = n / (n + prior)
    dist = w * (over if side == 'Over' else 1 - over) + (1 - w) * market
    return (hit + dist) / 2


def _indep_cal(p, m, side, c=FITTED):
    z = c['a'] * _logit(m) + c['b'] * (_logit(p) - _logit(m)) + c['c'] * (side == 'Over') + c['d']
    return 1 / (1 + math.exp(-z))


VALUES = [18, 25, 31, 22, 27, 19, 24, 30, 21, 26, 23, 28]     # synthetic


# ---------- A. economics ----------

@pytest.mark.parametrize('side', ['Over', 'Under'])
@pytest.mark.parametrize('line', [23.5, 24.0])
def test_A1_chance_and_calibration_match_an_independent_recomputation(side, line):
    over, under = 1.85, 1.95
    m_over = (1 / over) / (1 / over + 1 / under)
    m = m_over if side == 'Over' else 1 - m_over
    raw = prop_probability(pd.Series(VALUES, dtype=float), line, side, m, mean=24.8)['p']
    assert raw == pytest.approx(_indep_raw(VALUES, line, side, m, 24.8), abs=1e-9)
    assert calibrate(raw, m, side, FITTED) == pytest.approx(_indep_cal(raw, m, side), abs=1e-12)


@pytest.mark.parametrize('profile,alpha', [('superbet_standard', 0.88), ('superbet_no_tax', 1.0), ('legacy', 1.0)])
@pytest.mark.parametrize('push', [0.0, 0.12])
def test_A1_break_even_and_ev_definitions_agree(profile, alpha, push):
    """EV = p_win·α·odds + p_push − 1 and break-even = (1 − p_push)/(α·odds): EV is 0 exactly at break-even, and
    p_win is the unconditional chance (pushes are neither win nor loss)."""
    odds = 1.87
    be = float(break_even(odds, profile, push))
    assert be == pytest.approx((1 - push) / (alpha * odds))
    assert float(expected_return_100(be, odds, profile, push)) == pytest.approx(0.0, abs=1e-9)
    assert float(expected_return_100(0.6, odds, profile, push)) == pytest.approx(100 * (0.6 * alpha * odds + push - 1))


def test_A1_reason_model_text_carries_the_numbers_it_claims():
    bet = {'name': 'P', 'stat': 'PTS', 'side': 'Under', 'line': 23.5, 'odds': 1.95, 'model %': 51.2,
           'break-even %': 100 / (0.88 * 1.95), 'edge pp': 51.2 - 100 / (0.88 * 1.95),
           'ev': 100 * (0.512 * 0.88 * 1.95 - 1), 'tax': 12.0, 'avg': 24.0, 'proj avg': 24.0, 'opp': 'bos',
           'team': 'nyk', 'odds_at': FETCHED, 'stats_through': pd.Timestamp('2026-10-29')}
    games = pd.DataFrame({'PTS': VALUES, 'MIN': [32.0] * 12,
                          'Date': pd.date_range('2026-10-01', periods=12, freq='2D')})
    text = [r for r in prop_reasons(bet, games, games.iloc[0:0]) if r['kind'] == 'economics'][0]['text']
    assert 'Under wins 51.2%' in text and 'need 58.3%' in text and 'edge -7.1 pp' in text and '-12.1 per 100' in text
    nt = prop_reasons(bet | {'tax': 0.0, 'break-even %': 100 / 1.95, 'edge pp': 51.2 - 100 / 1.95,
                             'ev': 100 * (0.512 * 1.95 - 1)}, games, games.iloc[0:0])
    assert any('without the stake tax' in r['text'] for r in nt if r['kind'] == 'economics')


@pytest.mark.xfail(strict=True, reason="F-12 (latent: Superbet has had no whole-number line): the push chance "
                                       "is 1 − calibrated Over − calibrated Under, and both are pulled toward a "
                                       "margin-free price that excludes the push, so it collapses toward 0")
def test_A1_whole_line_push_chance_is_not_collapsed_by_the_calibration():
    values = pd.Series([2, 2, 2, 2, 1, 2, 3, 2, 2, 0, 2, 4], dtype=float)       # synthetic: 8 of 12 exactly 2
    m_over, m_under = no_vig(1.9, 1.9)
    p = {s: calibrate(prop_probability(values, 2.0, s, m, mean=values.mean())['p'], m, s, FITTED)
         for s, m in (('Over', m_over), ('Under', m_under))}
    push = max(0.0, 1 - p['Over'] - p['Under'])
    empirical = (values == 2).mean()
    assert push >= 0.5 * empirical, (push, empirical)


def test_A2_driver_impact_is_reset_one_input_through_the_calibration():
    """'moves the model's chance X pp' = final − final with that one input reset, both calibrated. Recomputed with
    the audit's own functions; the inputs overlap, so the parts don't add up to the total."""
    v = pd.Series(VALUES, dtype=float)
    m = 0.48
    args = dict(values=v, line=23.5, side='Over', market=m, adj_avg=24.0 + 2.0, lineup_adj=2.0, pace_factor=1.05,
                matchup_factor=1.04, coef=FITTED)
    imp = driver_impacts(**args)

    def fin(mean):
        return 100 * _indep_cal(_indep_raw(VALUES, 23.5, 'Over', m, mean), m, 'Over')
    full = fin(26.0 * 1.05 * 1.04)
    assert imp['final'] == pytest.approx(full, abs=1e-9)
    assert imp['availability'] == pytest.approx(full - fin(24.0 * 1.05 * 1.04), abs=1e-9)
    assert imp['environment'] == pytest.approx(full - fin(26.0 * 1.04), abs=1e-9)
    assert imp['opponent'] == pytest.approx(full - fin(26.0 * 1.05), abs=1e-9)
    all_reset = full - fin(24.0)
    assert abs(imp['availability'] + imp['environment'] + imp['opponent'] - all_reset) > 1e-6   # not additive
    # the calibration's b (0.17) shrinks every impact: with no calibration the same input moves it ~5x more
    ident = driver_impacts(**(args | {'coef': {'a': 1, 'b': 1, 'c': 0, 'd': 0}}))
    assert abs(ident['availability']) > 3 * abs(imp['availability'])


def test_A2_documents_that_the_calibration_alone_moves_a_favourite_above_its_price():
    """F-03: with a = 1.14 the calibrated chance of the price alone is above the margin-free price for the
    favourite: part of 'Model: X wins p%' is the calibration's correction of the price, not the player's numbers."""
    assert 100 * calibrate(0.62, 0.62, 'Under', FITTED) > 62.0 + 0.8


# ---------- A. mispricing ----------

def _quotes(rows):
    return pd.DataFrame(rows, columns=['bet_type', 'line', 'over_odds', 'under_odds'])


def test_A_H1_depends_on_the_players_correlations_not_only_on_the_prices():
    """F-08: H1's 'our' chance comes from the parts' prices plus the player's variances and correlations; the
    same prices give a different combo chance under another correlation (scenario, not an estimate)."""
    # overdispersed on purpose: when the summed variance is below the mean count_over falls back to a Poisson and
    # the correlation is ignored altogether (see the report, F-08)
    g = pd.DataFrame({'PTS': [8, 35, 14, 40, 12, 31, 10, 37, 29, 16], 'REB': [3, 12, 4, 13, 2, 10, 5, 11, 9, 4]})
    parts = {'PTS': {'line': 23.5, 'p_over': 0.5}, 'REB': {'line': 6.5, 'p_over': 0.55}}
    ind = mispricing.combo_over_from_parts(parts, 30.5, g, pd.DataFrame(np.eye(2), ['PTS', 'REB'], ['PTS', 'REB']))
    neg = mispricing.combo_over_from_parts(parts, 30.5, g.assign(REB=g['REB'].values[::-1]),
                                           pd.DataFrame(np.eye(2), ['PTS', 'REB'], ['PTS', 'REB']))
    pos = ind if neg is None else neg
    assert ind is not None and pos is not None and abs(ind - pos) > 0.005


def test_A_H2_implied_rate_is_a_model_quantity_not_read_from_the_offers():
    """F-07: 'the lines together assume he makes X%' is market_mean(makes)/market_mean(attempts), each solved with
    the player's own variance: the same two quotes give another 'assumed' rate for a player whose games vary
    differently."""
    q = _quotes([('3PM', 2.5, 1.9, 1.9), ('3PA', 7.5, 1.9, 1.9)])
    a = pd.DataFrame({'3PM': [2, 3, 2, 3, 2, 3, 2, 3, 2, 3], '3PA': [7, 8, 7, 8, 7, 8, 7, 8, 7, 8]})
    b = pd.DataFrame({'3PM': [0, 6, 1, 5, 0, 6, 1, 4, 2, 0], '3PA': [2, 14, 3, 13, 2, 12, 4, 11, 6, 3]})
    ra = mispricing.shooting_signals(q, a, {'3PM': 0.36}, status={})[0]['implied_rate']
    rb = mispricing.shooting_signals(q, b, {'3PM': 0.36}, status={})[0]['implied_rate']
    assert abs(ra - rb) > 0.01


def test_A_H2_player_rate_is_mostly_the_league_prior_with_few_attempts():
    """F-07: 'he makes R%' is (made + 200·league)/(attempts + 200); with 57 attempts 78% of the weight is the
    league's. The message quotes it as his rate."""
    rate = (17 + 200 * 0.35) / (57 + 200)
    assert 200 / 257 > 0.75 and round(100 * rate) == 34 and round(100 * 17 / 57) == 30


def _h6_games(values):
    return pd.DataFrame({'BLK': values})


def test_A_H6_why_text_matches_the_side_the_signal_favours():
    """F-05 (fixed in package B): the 'why' text now depends on the side the signal favours."""
    # synthetic and extreme on purpose: an Over-side H6 gap reaches the 4 pp display minimum only with a price of
    # ~7% and a spread ~5 (the audit's grid search: max Over gap 5.8 pp), so this is a rare but reachable case
    q = _quotes([('BLK', 2.5, 14.0, 1.02)])
    sig = mispricing.spread_signals(q, _h6_games([0] * 9 + [9]), {'BLK': 3.0}, status={})
    assert sig and sig[0]['side'] == 'Over'                                   # the effect reverses here
    text = mispricing_reasons(sig, 'BLK', 'Over', 'en')[0]['text']
    assert 'below the line more often' not in text


def test_A_H6_more_than_usual_only_when_above_the_league():
    """F-06 (fixed in package B): the comparison with the league's typical spread follows the numbers."""
    q = _quotes([('BLK', 0.5, 1.50, 2.60)])
    sig = mispricing.spread_signals(q, _h6_games([0, 1, 2, 0, 3, 1, 0, 2, 1, 0]), {'BLK': 1.6}, status={})
    assert sig and 1 < sig[0]['spread'] < sig[0]['league_spread']
    text = mispricing_reasons(sig, 'BLK', sig[0]['side'], 'en')[0]['text']
    assert 'more than usual' not in text


def test_A_H6_one_x_means_poisson_not_evenly_scattered():
    """F-06 (fixed in package B): variance/mean = 1 is a Poisson count; 'evenly' (variance 0) is gone."""
    for lang, word in (('en', 'evenly'), ('pl', 'równomiernie')):
        assert word not in i18n.TEXTS['mispricing.h6.what'][lang]
    assert 'variance equal to the mean' in i18n.TEXTS['mispricing.h6.what']['en']


def test_A_H5_is_not_emitted_by_the_props_page():
    """Inventory: dashboard_v2/views/props.py calls offer_signals without role, so role_signals returns nothing;
    the H5 templates are only reachable with a role (the harness's second pass)."""
    src = inspect.getsource(sys.modules.get('mispricing'))
    assert "if role not in ('starter', 'bench')" in src
    page = open(os.path.join(ROOT, 'dashboard_v2', 'views', 'props.py'), encoding='utf-8').read()
    call = re.search(r'offer_signals\(([^)]*)\)', page).group(1)
    assert 'role' not in call


def test_A_H5_scales_the_price_by_minutes_without_evidence_the_price_lags():
    """F-09: H5's chance = the price's mean × (new-role minutes / last-5 minutes): it assumes the price ignores
    tonight's role. Nothing in the signal checks when the price was set relative to the RotoWire news."""
    src = inspect.getsource(mispricing.role_signals)
    assert '* minutes / usual' in src and 'fetched_at' not in src and 'first seen' not in src


def test_A_mispricing_uses_the_pages_cost_profile():
    """F-10 (fixed in package A): the props page passes the sidebar's profile to offer_signals."""
    page = open(os.path.join(ROOT, 'dashboard_v2', 'views', 'props.py'), encoding='utf-8').read()
    call = re.search(r'offer_signals\(([^)]*)\)', page).group(1)
    assert 'profile' in call


def test_A_mispricing_needed_pp_includes_margin_and_tax():
    """needed_pp = break-even (tax) − margin-free price: the margin and the tax, no extra threshold."""
    q = _quotes([('BLK', 0.5, 1.50, 2.60)])
    sig = mispricing.spread_signals(q, _h6_games([0, 0, 3, 0, 2, 0, 0, 4, 0, 1]), {'BLK': 1.2}, status={})[0]
    odds = sig['odds']
    m = (1 / 1.5) / (1 / 1.5 + 1 / 2.6)
    p_side = m if sig['side'] == 'Over' else 1 - m
    assert sig['needed_pp'] == pytest.approx(100 * (1 / (0.88 * odds) - p_side))
    assert sig['clears'] == (sig['p_ours'] >= 1 / (0.88 * odds))


def test_A_admitted_signal_about_another_line_has_no_direction_on_this_one():
    """F-11 (fixed in package C): a signal about another offer gets no direction on this one."""
    sig = {'hypothesis': 'H1', 'mechanism': 'B', 'status': 'admitted', 'exploration': None, 'bet_type': 'PR',
           'line': 30.5, 'parts': [('PTS', 23.5), ('REB', 6.5)], 'side': 'Over', 'p_ours': 0.62, 'p_book': 0.5,
           'gap_pp': 12.0, 'needed_pp': 7.0, 'clears': True, 'odds': 1.9, 'n': 20, 'as_of': FETCHED,
           'expires_when': 'line_or_odds_change'}
    r = mispricing_reasons([sig], 'PTS', 'Over', 'en')[0]
    assert r['supports'] is None


def test_A_negative_exploration_comes_before_the_hypothetical_gain():
    """F-04, F-07 (fixed in package B): the exploration record comes before the gap, the gap is the alternative
    model's distance from the break-even after costs, and the offers aren't said to 'assume' a shooting rate."""
    sig = {'hypothesis': 'H2', 'mechanism': 'B', 'status': 'untested', 'bet_type': '3PM', 'line': 1.5,
           'parts': [('3PA', 5.5)], 'side': 'Under', 'p_ours': 0.54, 'p_book': 0.41, 'gap_pp': 13.1,
           'needed_pp': 9.1, 'clears': True, 'odds': 2.25, 'n': 10, 'as_of': FETCHED,
           'expires_when': 'line_or_odds_change', 'implied_rate': 0.46, 'player_rate': 0.34, 'league_rate': 0.35,
           'made': 17, 'attempted': 57, 'games_all': 10,
           'exploration': {'nights': 12, 'through': '2026-10-31', 'signals': 130, 'won': 54.6, 'roi': -9.8}}
    lines = mispricing_reasons([sig], '3PM', 'Under', 'en')[0]['text'].split("  \n")
    assert '-9.8 per 100 staked' in lines[2]
    assert lines[4].startswith("Under this alternative model's assumptions it is 4.0 pp above the break-even after "
                               "costs")
    text = "  ".join(lines)
    assert 'covers it' not in text and 'together assume' not in text
    assert 'observed rate: 17 of 57 (30%)' in text and '78% of the weight' in text


# ---------- C. evidence dependence ----------

def test_C_hit_rate_text_names_the_rate_the_model_uses():
    """F-13 (fixed in package A): the panel shows the last-10 hit rate first; prop_probability uses the rate over
    ALL the player's games, and the note now says so, with the Wilson range named as the past rate's."""
    src = inspect.getsource(prop_probability)
    assert 'values.tail' not in src
    note = i18n.TEXTS['reason.history_note']['en']
    assert 'The model uses this rate' not in note and 'over all {n} games' in note
    assert 'range of this past rate' in i18n.TEXTS['reason.history_last']['en']


def test_C_applied_absence_adjustment_is_always_explained():
    """F-02 (fixed in package A): a teammate the player never played without no longer drops the reason for the
    others' adjustment; he is named as unknown, and no raw id or made-up count appears."""
    games = pd.DataFrame({'PTS': VALUES, 'MIN': [32.0] * 12, 'Date': pd.date_range('2026-10-01', periods=12,
                                                                                   freq='2D')})
    absences = [{'id': 1, 'name': 'B', 'n_without': 3, 'n_with': 9, 'estimated': True, 'change': 2.0},
                {'id': 3102530, 'name': None, 'n_without': 0, 'n_with': 12, 'estimated': False, 'change': np.nan}]
    bet = {'name': 'P', 'stat': 'PTS', 'side': 'Over', 'line': 23.5, 'odds': 1.9, 'model %': 52.0,
           'break-even %': 59.8, 'edge pp': -7.8, 'tax': 12.0, 'avg': 24.0, 'proj avg': 26.0, 'lineup adj': 2.0,
           'absences': absences, 'out_names': ['B'], 'out_n': 3, 'lineup_at': FETCHED, 'opp': 'bos',
           'team': 'nyk', 'odds_at': FETCHED, 'stats_through': pd.Timestamp('2026-10-29'),
           'impacts': {'availability': 0.4, 'final': 52.0}}
    mates = [r for r in prop_reasons(bet, games, games.iloc[0:0]) if r.get('group') == 'availability']
    assert len(mates) == 1 and mates[0]['n'] == 3 and '3102530' not in mates[0]['text']
    assert 'their effect is unknown' in mates[0]['text']


def test_C_absence_text_describes_the_sum_it_computes():
    """F-14 (fixed in package A): absence_adjustments adds one shrunk with/without difference per absent teammate
    and never looks at games without all of them; the text now says that."""
    import metrics
    src = inspect.getsource(metrics.absence_adjustments)
    assert 'out.loc[p] +=' in src and 'for o in out_ids' in src
    for lang in ('en', 'pl'):
        text = i18n.TEXTS['reason.teammates'][lang]
        assert 'games without them' not in text and 'meczach bez nich' not in text
    assert 'one with/without difference per teammate' in i18n.TEXTS['reason.teammates']['en']


# ---------- 7. recommendation consistency ----------

def _line(name='A', ev=-8.0, edge=-4.0, role='starter', flag='', **kw):
    return {'event_id': 1, 'name': name, 'name_ESPN': name, 'bet_type': 'PTS', 'line': 20.5, 'home': 'bos',
            'away': 'nyk', 'side': 'Over', 'side odds': 1.9, 'p win %': 55.0, 'break-even net %': 59.8,
            'edge net pp': edge, 'ev net 100': ev, 'red flag': flag, 'RotoWire': role} | kw


def _decide(rows, threshold=None):
    lu = pd.DataFrame({'team': ['bos', 'nyk'], 'fetched_at': '2026-10-30T21:00:00Z'})
    return decisions.player_decision(pd.DataFrame(rows), 'fitted', lu, FETCHED, NOW, threshold)


def test_7_questionable_player_does_not_hide_a_clean_qualifying_offer():
    """F-01 (fixed in package C)."""
    rows = [_line('A', ev=10.0, edge=5.0, role='Ques 50%', flag='RotoWire: Ques 50%: may sit'),
            _line('B', ev=6.0, edge=3.0)]
    assert _decide(rows, threshold=1.0)['status'] == decisions.OBSTAW


def test_7_without_a_threshold_a_questionable_player_is_not_a_reason_to_wait():
    """F-01 (fixed in package C): the questionable player is a note beside 'no threshold'."""
    d = _decide([_line('A', ev=-2.0, role='Ques 50%', flag='x'), _line('B', ev=-6.0)])
    assert d['reason'] == 'decision.reason.no_threshold'


def test_7_blockers_are_applied_before_choosing_the_offer():
    d = _decide([_line('A', ev=9.0, edge=5.0, flag='few games'), _line('B', ev=4.0, edge=2.0)], threshold=1.0)
    assert d['status'] == decisions.OBSTAW and d['offer']['name'] == 'B'


def test_7_a_tie_is_its_own_status_not_wait():
    """F-15 (fixed in package C): two equal offers give REMIS ('No single choice'), not CZEKAJ ('Wait')."""
    d = _decide([_line('A', ev=6.0, edge=3.0), _line('B', ev=6.05, edge=3.1)], threshold=1.0)
    assert d['status'] == decisions.REMIS and d['reason'] == 'decision.reason.tie'
    assert decisions.TIE_EV == 0.1                                       # the tolerance itself is unchanged


def test_7_the_decision_never_reads_the_reasons():
    params = inspect.signature(decisions.player_decision).parameters
    assert not any('reason' in p for p in params)
    assert 'prop_reasons' not in inspect.getsource(decisions.player_decision)


def test_7_not_chosen_is_worded_apart_from_not_qualifying():
    """Package C4: a line that meets the condition but isn't chosen is told apart from one that doesn't meet it."""
    assert "Not chosen doesn't mean unprofitable" in i18n.TEXTS['decision.reason.not_chosen']['en']
    assert "doesn't meet the condition" in i18n.TEXTS['decision.reason.other_offer']['en']


# ---------- B. small samples, missing data, colliding warnings ----------

def test_B_small_sample_and_no_data():
    from reasons import prop_flag_items
    assert ('flag.few_games', {'n': 3}) in prop_flag_items(3, False, None, '', pd.Series([30.0] * 3), None, 'Over')
    bet = {'name': 'P', 'stat': 'PTS', 'side': 'Over', 'line': 23.5, 'odds': 1.9, 'model %': 52.0,
           'break-even %': 59.8, 'edge pp': -7.8, 'tax': 12.0, 'avg': np.nan, 'proj avg': np.nan, 'opp': 'bos',
           'team': 'nyk', 'odds_at': FETCHED}
    empty = pd.DataFrame({'PTS': [], 'Date': []})
    r = prop_reasons(bet, empty, empty)
    assert any(x['flag'] and 'Only 0' in x['text'] for x in r)
    assert not any(x.get('group') == 'history' for x in r)


def test_B_colliding_warning_and_blocker_are_both_shown():
    games = pd.DataFrame({'PTS': VALUES, 'MIN': [10, 38, 12, 36, 9, 35, 14, 37, 11, 39, 8, 36],
                          'starter': [False] * 12, 'Date': pd.date_range('2026-10-01', periods=12, freq='2D')})
    bet = {'name': 'P', 'stat': 'PTS', 'side': 'Over', 'line': 23.5, 'odds': 1.9, 'model %': 52.0,
           'break-even %': 59.8, 'edge pp': -7.8, 'tax': 12.0, 'avg': 24.0, 'proj avg': 24.0, 'opp': 'bos',
           'team': 'nyk', 'odds_at': FETCHED, 'status': 'starter', 'play_pct': 50, 'lineup_at': FETCHED}
    r = prop_reasons(bet, games, games.iloc[0:0])
    kinds = [(x['kind'], x['text'][:30]) for x in r]
    assert any(k == 'warning' and 'Started 0' in t for k, t in kinds)
    assert sum(k == 'blocker' for k, _ in kinds) >= 2           # may not play + minutes swing


def test_B_changed_quote_is_detected():
    out = decisions.offer_changed({'line': 23.5, 'odds': 1.9}, {'line': 24.5, 'odds': 1.9})
    assert out['changed'] and out['line'] == (23.5, 24.5) and out['odds'] is None


@pytest.mark.parametrize('odds,profile,sign', [(1.90, 'superbet_standard', -1), (1.90, 'superbet_no_tax', 1),
                                                (2.30, 'superbet_standard', 1)])
def test_B_ev_sign_near_the_boundary_depends_on_tax_and_odds(odds, profile, sign):
    """Scenario: a 55% chance is +EV at 1.90 only without the tax; at 2.30 also with it."""
    assert np.sign(float(expected_return_100(0.55, odds, profile))) == sign
