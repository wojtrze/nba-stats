"""Run with: python -m pytest dashboard"""
import numpy as np
import pandas as pd
import pytest

import i18n
from metrics import count_over
from mispricing import (ADMITTED, REJECTED, UNTESTED, combo_over_from_parts, combo_signals, hypothesis_status,
                        league_rates, league_spreads, market_mean, offer_signals, pooled_correlations,
                        role_signals, role_uplift, shooting_signals, spread_signals)
from reasons import MISPRICING, prop_reasons
from test_reasons import _bet, _games


def _player(n=30, seed=1):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({'PTS': rng.poisson(22, n).astype(float), 'REB': rng.poisson(7, n).astype(float),
                         'AST': rng.poisson(5, n).astype(float), 'player_id_ESPN': 1})


def _odds(p_over, margin=1.07):
    return margin / p_over, margin / (1 - p_over)


def _lines(arp_over=None, arp_line=33.5):
    """PTS, REB, AST at even money and PRA priced fair to them unless arp_over says otherwise."""
    parts = {'PTS': 21.5, 'REB': 6.5, 'AST': 4.5}
    rows = [{'bet_type': s, 'line': l, 'over_odds': 1.87, 'under_odds': 1.87} for s, l in parts.items()]
    if arp_over is None:
        arp_over = combo_over_from_parts({s: {'line': l, 'p_over': 0.5} for s, l in parts.items()}, arp_line,
                                         _player(), pooled_correlations(_player()))
    over, under = _odds(arp_over)
    return pd.DataFrame(rows + [{'bet_type': 'ARP', 'line': arp_line, 'over_odds': over, 'under_odds': under}])


def test_market_mean_reproduces_the_price():
    m = market_mean(21.5, 0.55, 22.0, 30.0)
    assert abs(count_over(m, 30.0 / 22.0 * m, 21.5) - 0.55) < 1e-4


def test_pooled_correlations_are_within_players():
    # two players far apart in level: across them PTS and REB look correlated, within each they aren't related
    logs = pd.DataFrame({'player_id_ESPN': [1] * 4 + [2] * 4, 'PTS': [10, 12, 10, 12, 30, 32, 30, 32],
                         'REB': [2, 2, 4, 4, 9, 9, 11, 11], 'AST': [1, 2, 3, 4, 1, 2, 3, 4]})
    assert abs(pooled_correlations(logs).loc['PTS', 'REB']) < 1e-9


def test_a_combo_priced_from_its_parts_has_no_gap():
    signals = combo_signals(_lines(), _player(), pooled_correlations(_player()), status={})
    assert [s['bet_type'] for s in signals] == ['ARP']
    assert signals[0]['gap_pp'] < 0.1 and signals[0]['status'] == UNTESTED


def test_a_combo_out_of_line_with_its_parts_is_a_gap_for_the_side_the_parts_favour():
    fair = _lines().set_index('bet_type').loc['ARP']
    p_fair = (1 / fair['over_odds']) / (1 / fair['over_odds'] + 1 / fair['under_odds'])
    s = combo_signals(_lines(arp_over=p_fair - 0.12), _player(), pooled_correlations(_player()), status={})[0]
    assert s['side'] == 'Over' and abs(s['gap_pp'] - 12) < 0.5
    assert s['parts'] == [('PTS', 21.5), ('REB', 6.5), ('AST', 4.5)]
    # the side's odds need its break-even after the 12% tax: above the margin-free price
    assert s['needed_pp'] > 0 and s['clears'] == (s['gap_pp'] >= s['needed_pp'])


def test_no_signal_without_every_part_enough_games_or_on_a_whole_line():
    prior = pooled_correlations(_player())
    assert combo_signals(_lines()[_lines()['bet_type'] != 'AST'], _player(), prior, status={}) == []
    assert combo_signals(_lines(), _player(n=5), prior, status={}) == []
    assert combo_signals(_lines(arp_line=33.0), _player(), prior, status={}) == []


def test_status_comes_from_the_file_and_defaults_to_untested(tmp_path):
    path = tmp_path / 'status.json'
    assert hypothesis_status(str(path)) == {}
    path.write_text('{"hypotheses": {"H1": {"status": "admitted"}}}', encoding='utf-8')
    assert hypothesis_status(str(path))['H1']['status'] == ADMITTED


def _signal(**kw):
    s = {'hypothesis': 'H1', 'mechanism': 'B', 'status': UNTESTED, 'bet_type': 'ARP', 'line': 33.5,
         'parts': [('PTS', 21.5), ('REB', 6.5), ('AST', 4.5)], 'side': 'Over', 'p_ours': 0.58, 'p_book': 0.51,
         'gap_pp': 7.0, 'needed_pp': 11.0, 'clears': False, 'odds': 1.75, 'n': 30,
         'as_of': '2026-11-01T20:00:00Z', 'expires_when': 'line_or_odds_change'}
    return s | kw


def _mispricing(signals, **bet):
    games = _games([25.0] * 12).assign(REB=7.0, AST=5.0, ARP=37.0, **{'3PM': 2.0})
    return [r for r in prop_reasons(_bet(**bet), games, _games([]), 'pl', validation={}, signals=signals)
            if r['kind'] == MISPRICING]


def test_an_untested_signal_says_how_tested_it_is_before_what_it_claims():
    """Package B order: the offer, the status, the exploration record, beside the main model, the break-even,
    how it's computed, its assumptions and limits, how long it holds."""
    [r] = _mispricing([_signal()], stat='ARP', line=33.5)
    lines = r['text'].split("  \n")
    assert r['supports'] is None and r['validation'] == UNTESTED and r['this_offer']
    assert lines[0] == 'H1, kombinacja a jej składowe: „Powyżej PRA 33.5”, ta oferta'
    assert lines[1].startswith('🧪') and 'nie wskazówka do gry' in lines[1]
    assert lines[2].startswith('Brak zapisu z rozpoznania')
    assert lines[3].startswith('Po 1.75 ten model alternatywny szacuje 58%') and 'sama cena 51%' in lines[3]
    assert lines[4].startswith('Przy założeniach tego modelu alternatywnego jest 4.0 pp pod progiem')
    assert '(62.0%;' in lines[4] and 'dokładają 11.0 pp' in lines[4]
    assert lines[5].startswith('Jak:') and 'PTS 21.5' in lines[5]
    assert lines[6].startswith('Założenia i ograniczenia') and 'się spóźnia' in lines[6]
    assert 'znika' in lines[7] and len(lines) == 8
    for banned in ('pokrywa', 'zakładają', 'nie nadąża'):
        assert banned not in r['text']


def test_signals_shown_only_when_they_concern_the_line_and_matter():
    assert _mispricing([_signal()], stat='REB', line=6.5)           # a part of the combo
    assert not _mispricing([_signal()], stat='3PM', line=2.5)      # another stat
    assert not _mispricing([_signal(gap_pp=2.9)], stat='ARP', line=33.5)
    assert not _mispricing([_signal(status=REJECTED)], stat='ARP', line=33.5)


def test_only_an_admitted_hypothesis_argues_for_or_against():
    assert _mispricing([_signal(status=ADMITTED)], stat='ARP', side='Over')[0]['supports'] is True
    assert _mispricing([_signal(status=ADMITTED)], stat='ARP', side='Under')[0]['supports'] is False
    clears = _mispricing([_signal(status=ADMITTED, clears=True, gap_pp=12.0)], stat='ARP')[0]['text']
    assert '1.0 pp nad progiem opłacalności' in clears and clears.split("  \n")[1].startswith('✅')


def test_the_signal_texts_are_in_both_languages():
    keys = [f'mispricing.{h}.what' for h in ('h1', 'h2', 'h5', 'h6')] + \
        ['mispricing.h1.why', 'mispricing.h2.why', 'mispricing.h5.why', 'mispricing.h6.why_under',
         'mispricing.h6.why_over', 'mispricing.h2.ft_limit'] + [f'mispricing.name.H{h}' for h in (1, 2, 5, 6)]
    for key in keys + ['mispricing.expiry.line_or_odds_change', 'mispricing.status.untested',
                       'mispricing.status.admitted', 'mispricing.exploration', 'mispricing.no_exploration',
                       'mispricing.compare', 'mispricing.compare_this', 'mispricing.compare_other',
                       'mispricing.above', 'mispricing.below', 'panel.mispricing', 'panel.mispricing_note',
                       'panel.research', 'panel.research_note', 'panel.research_shared']:
        assert set(i18n.TEXTS[key]) == set(i18n.LANGS)


def _shooter(rate=0.37, n=30, seed=2):
    rng = np.random.default_rng(seed)
    attempts = rng.poisson(8, n)
    return pd.DataFrame({'3PA': attempts.astype(float), '3PM': rng.binomial(attempts, rate).astype(float),
                         'player_id_ESPN': 1})


def _shot_lines(made_over):
    over, under = _odds(made_over)
    return pd.DataFrame([{'bet_type': '3PA', 'line': 7.5, 'over_odds': 1.87, 'under_odds': 1.87},
                         {'bet_type': '3PM', 'line': 2.5, 'over_odds': over, 'under_odds': under}])


def test_makes_priced_for_better_shooting_than_the_players_favour_under():
    games = _shooter()
    rates = league_rates(games)
    s = shooting_signals(_shot_lines(0.75), games, rates, status={})[0]
    assert s['hypothesis'] == 'H2' and s['bet_type'] == '3PM' and s['parts'] == [('3PA', 7.5)]
    assert s['side'] == 'Under' and s['implied_rate'] > s['player_rate'] and s['gap_pp'] > 5
    assert s['made'] == int(games['3PM'].sum()) and s['attempted'] == int(games['3PA'].sum())
    assert shooting_signals(_shot_lines(0.15), games, rates, status={})[0]['side'] == 'Over'


def test_a_short_shooting_record_is_pulled_toward_the_league():
    games = _shooter(rate=0.6, n=8)
    s = shooting_signals(_shot_lines(0.5), games, {'3PM': 0.36}, status={})[0]
    own = games['3PM'].sum() / games['3PA'].sum()
    assert 0.36 < s['player_rate'] < own


def test_no_shooting_signal_without_the_attempts_line():
    lines = _shot_lines(0.5)
    assert shooting_signals(lines[lines['bet_type'] != '3PA'], _shooter(), {'3PM': 0.36}, status={}) == []


def _blocks(values):
    return pd.DataFrame({'BLK': [float(v) for v in values], 'FTM': [float(v) for v in values], 'player_id_ESPN': 1})


def _small_lines(stat='BLK', line=0.5):
    return pd.DataFrame([{'bet_type': stat, 'line': line, 'over_odds': 1.87, 'under_odds': 1.87}])


def test_a_player_whose_small_counts_spread_more_ends_under_more_often():
    swingy = _blocks([0, 0, 0, 0, 3, 0, 0, 4, 0, 0, 0, 3] * 2)
    s = spread_signals(_small_lines(), swingy, {'BLK': 1.05}, status={})[0]
    assert s['hypothesis'] == 'H6' and s['side'] == 'Under' and s['gap_pp'] > 0 and s['parts'] == []
    assert s['spread'] > 1 and abs(s['below'] - swingy['BLK'].lt(0.5).mean()) < 1e-9


def test_no_spread_signal_for_even_results_free_throws_or_big_lines():
    even = _blocks([1, 0, 1, 2, 1, 0, 1, 1, 2, 1, 0, 1])
    assert spread_signals(_small_lines(), even, {'BLK': 0.5}, status={}) == []
    swingy = _blocks([0, 0, 0, 0, 3, 0, 0, 4, 0, 0, 0, 3] * 2)
    assert spread_signals(_small_lines('FTM'), swingy, {'FTM': 2.0}, status={}) == []
    assert spread_signals(_small_lines(line=3.5), swingy, {'BLK': 1.05}, status={}) == []


def test_offer_signals_runs_every_detector():
    games = _player().assign(**{'3PA': _shooter()['3PA'], '3PM': _shooter()['3PM']})
    lines = pd.concat([_lines(), _shot_lines(0.75)], ignore_index=True)
    assert {s['hypothesis'] for s in offer_signals(lines, games, games, status={})} == {'H1', 'H2'}


def test_shooting_and_spread_messages_say_the_numbers_they_rest_on():
    games = _games([25.0] * 12).assign(**{'3PM': 2.0, '3PA': 7.0, 'BLK': 0.0})
    h2 = _signal(hypothesis='H2', bet_type='3PM', line=2.5, parts=[('3PA', 7.5)], side='Under', gap_pp=6.5,
                 implied_rate=0.44, player_rate=0.35, league_rate=0.36, made=60, attempted=170, games_all=25)
    [r] = [r for r in prop_reasons(_bet(stat='3PA', line=7.5), games, _games([]), 'pl', validation={},
                                   signals=[h2]) if r['kind'] == MISPRICING]
    assert 'skuteczność obserwowana: 60 z 170 (35%) w 25 meczach' in r['text']
    assert 'ligową 36% (jak gdyby warta 200 prób, tu 54% wagi) daje 35%' in r['text']
    assert 'stosunek 44%: to liczba tego modelu, nie skuteczność podawana przez Superbet' in r['text']
    assert 'inna oferta' in r['text'] and 'nie jest porównywany' in r['text']           # the 3PM line, shown on 3PA
    assert not [r for r in prop_reasons(_bet(stat='3PM', line=2.5), games, _games([]), 'pl', validation={},
                                        signals=[h2 | {'gap_pp': 5.9}]) if r['kind'] == MISPRICING]
    h6 = _signal(hypothesis='H6', bet_type='BLK', line=0.5, parts=[], side='Under', gap_pp=4.5, spread=1.8,
                 own_spread=2.1, league_spread=1.07, below=0.48)
    [r] = [r for r in prop_reasons(_bet(stat='BLK', line=0.5, side='Under'), games, _games([]), 'pl',
                                   validation={}, signals=[h6]) if r['kind'] == MISPRICING]
    assert 'w 48% z nich' in r['text'] and '1.8×, więcej niż typowo w lidze' in r['text']
    assert r['text'].startswith('H6, rozrzut małej liczby') and 'wariancja równa średniej' in r['text']
    assert 'równomiernie' not in r['text'] and 'Poniżej staje się bardziej prawdopodobne' in r['text']


def test_the_exploration_record_comes_before_the_hypothetical_gain():
    """Whether or not this signal reaches the break-even, how such signals did is said first (audit F-04)."""
    explored = {'nights': 12, 'through': '2026-10-31', 'signals': 130, 'won': 54.6, 'roi': -9.8}
    for signal in (_signal(clears=True, gap_pp=12.0, exploration=explored), _signal(exploration=explored)):
        lines = _mispricing([signal], stat='ARP')[0]['text'].split("  \n")
        assert lines[2] == ("Dotąd: na nocach rozpoznania (12 nocy do 2026-10-31) sygnałów tej hipotezy, które "
                            "sięgały progu opłacalności po standardowym podatku 12%, było 130; wygrało 55% z nich, "
                            "wynik -9.8 zł na 100 zł stawki po tym podatku.")
        assert 'progiem opłacalności' in lines[4]


def test_the_status_file_feeds_the_signal():
    status = {'H1': {'status': ADMITTED, 'exploration': {'signals': 1}}}
    s = combo_signals(_lines(), _player(), pooled_correlations(_player()), status=status)[0]
    assert s['status'] == ADMITTED and s['exploration'] == {'signals': 1}


def _bench_player(starts, n=20, bench_min=18.0, start_min=30.0):
    """n games off the bench at bench_min, the last `starts` of them starts at start_min; PTS one per minute."""
    starter = [False] * (n - starts) + [True] * starts
    minutes = [start_min if s else bench_min for s in starter]
    return pd.DataFrame({'starter': starter, 'MIN': minutes, 'PTS': minutes, 'player_id_ESPN': 1,
                         'Date': pd.date_range('2026-10-01', periods=n)})


def test_a_bench_player_starting_tonight_favours_over_his_price():
    lines = pd.DataFrame([{'bet_type': 'PTS', 'line': 17.5, 'over_odds': 1.87, 'under_odds': 1.87}])
    [s] = role_signals(lines, _bench_player(0), 'starter', 10.0, {}, status={})
    assert s['hypothesis'] == 'H5' and s['side'] == 'Over' and s['gap_pp'] > 0 and s['minutes'] > s['usual_minutes']
    starter = _bench_player(5)
    [d] = role_signals(lines, starter, 'bench', 10.0, {}, status={})
    assert d['side'] == 'Under' and d['minutes'] < d['usual_minutes']


def test_no_role_signal_when_tonight_matches_his_last_games_or_the_role_is_unknown():
    lines = pd.DataFrame([{'bet_type': 'PTS', 'line': 17.5, 'over_odds': 1.87, 'under_odds': 1.87}])
    assert role_signals(lines, _bench_player(0), 'bench', 10.0, {}, status={}) == []
    assert role_signals(lines, _bench_player(2), 'starter', 10.0, {}, status={}) == []     # 2 of 5: no change
    assert role_signals(lines, _bench_player(0), None, 10.0, {}, status={}) == []
    assert role_signals(lines, _bench_player(0), 'Ques 50%', 10.0, {}, status={}) == []


def test_role_uplift_is_the_starter_minus_bench_minutes():
    logs = pd.concat([_bench_player(5).assign(player_id_ESPN=1), _bench_player(10).assign(player_id_ESPN=2)])
    assert role_uplift(logs) == 12.0


def test_the_role_message_says_the_role_and_the_minutes():
    games = _games([25.0] * 12)
    h5 = _signal(hypothesis='H5', bet_type='PTS', line=17.5, parts=[], side='Over', gap_pp=8.0, role='starter',
                 starts=0, last_games=5, usual_minutes=18.0, minutes=27.6, role_games=0)
    [r] = [r for r in prop_reasons(_bet(stat='PTS', line=17.5), games, _games([]), 'pl', validation={},
                                   signals=[h5]) if r['kind'] == MISPRICING]
    assert 'według RotoWire dziś pierwsza piątka. W ostatnich 5 meczach zaczynał 0 razy i grał w nich 18 min' in r['text']
    assert 'około 28 min' in r['text']


# --- the cost profile the page prices with (audit F-10). Synthetic quotes and games: maths and logic only ---

def test_signals_use_the_cost_profile_they_are_given_and_never_call_needed_the_tax():
    from metrics import break_even, no_vig
    from mispricing import spread_signals
    from reasons import mispricing_reasons
    q = pd.DataFrame([('BLK', 0.5, 1.50, 2.60)], columns=['bet_type', 'line', 'over_odds', 'under_odds'])
    games = pd.DataFrame({'BLK': [0, 0, 3, 0, 2, 0, 0, 4, 0, 1]})
    std = spread_signals(q, games, {'BLK': 1.2}, status={}, profile='superbet_standard')[0]
    free = spread_signals(q, games, {'BLK': 1.2}, status={}, profile='superbet_no_tax')[0]
    p_side = no_vig(1.5, 2.6)[0 if std['side'] == 'Over' else 1]
    for s, profile in ((std, 'superbet_standard'), (free, 'superbet_no_tax')):
        assert s['needed_pp'] == pytest.approx(100 * (float(break_even(s['odds'], profile)) - p_side))
    assert free['needed_pp'] < std['needed_pp']
    for lang in ('en', 'pl'):
        threshold = mispricing_reasons([free], 'BLK', free['side'], lang)[0]['text'].split("  \n")[4]
        assert 'tax' not in threshold and 'podat' not in threshold
        assert ('break-even after costs' if lang == 'en' else 'progiem opłacalności po kosztach') in threshold


def test_the_props_page_passes_its_cost_profile_to_the_signals():
    import os
    import re
    page = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dashboard_v2', 'views',
                        'props.py')
    call = re.search(r'signals = offer_signals\((.*)\)', open(page, encoding='utf-8').read()).group(1)
    assert 'profile=cost_profile()' in call


# --- package B: research hypotheses beside the main model, grouped, worded as an alternative model ---

def test_a_hypothesis_is_set_beside_the_main_model_on_the_same_offer_only():
    sides = {'Over': {'p': 47.0, 'ev': -18.1}, 'Under': {'p': 53.0, 'ev': -10.2}}
    games = _games([25.0] * 12).assign(REB=7.0, AST=5.0, ARP=37.0)
    reasons = prop_reasons(_bet(stat='ARP', line=33.5) | {'sides': sides}, games, _games([]), 'en',
                           validation={}, signals=[_signal()])
    [r] = [r for r in reasons if r['kind'] == MISPRICING]
    compare = r['text'].split("  \n")[3]
    assert compare.startswith("The same offer at 1.75: the main model estimates 47% (EV -18.1 per 100); this "
                              "alternative model 58% (EV -10.7)")
    # the same signal shown on a part's line: another offer, no comparison with this line's evaluation
    reasons = prop_reasons(_bet(stat='REB', line=6.5) | {'sides': sides}, games, _games([]), 'en',
                           validation={}, signals=[_signal()])
    [r] = [r for r in reasons if r['kind'] == MISPRICING]
    assert not r['this_offer'] and "another offer (not the one evaluated above)" in r['text']
    assert "isn't compared with the evaluation above" in r['text'] and 'main model' not in r['text']


def test_free_throws_carry_their_limit():
    games = _games([25.0] * 12).assign(FTM=1.0)
    ft = _signal(hypothesis='H2', bet_type='FTM', line=0.5, parts=[('FTA', 1.5)], side='Over', gap_pp=24.1,
                 implied_rate=0.39, player_rate=0.77, league_rate=0.78, made=14, attempted=21, games_all=10)
    [r] = [r for r in prop_reasons(_bet(stat='FTM', line=0.5), games, _games([]), 'en', validation={},
                                   signals=[ft]) if r['kind'] == MISPRICING]
    assert 'Limit for free throws: they come in pairs' in r['text'] and '(67%)' in r['text'] and '90% of the weight' in r['text']


@pytest.mark.parametrize('side,words', [('Under', 'the Under gets more likely'), ('Over', 'the Over gets more likely')])
def test_the_spread_message_matches_the_side_it_favours(side, words):
    games = _games([25.0] * 12).assign(BLK=1.0)
    h6 = _signal(hypothesis='H6', bet_type='BLK', line=2.5, parts=[], side=side, gap_pp=5.0, spread=1.4,
                 own_spread=2.0, league_spread=1.6, below=0.8)
    [r] = [r for r in prop_reasons(_bet(stat='BLK', line=2.5, side=side), games, _games([]), 'en', validation={},
                                   signals=[h6]) if r['kind'] == MISPRICING]
    assert words in r['text'] and 'less than the league\'s typical, though more than a Poisson\'s' in r['text']
    assert 'more than usual' not in r['text']


def test_the_panel_layout_keeps_research_apart_and_groups_it_by_offer():
    from reasons import panel_layout
    games = _games([25.0] * 12).assign(REB=7.0, AST=5.0, ARP=37.0, BLK=1.0)
    h6 = _signal(hypothesis='H6', bet_type='ARP', line=33.5, parts=[], side='Over', gap_pp=5.0, spread=1.4,
                 own_spread=2.0, league_spread=1.2, below=0.4)
    other = _signal(bet_type='PR', line=30.5, parts=[('PTS', 21.5), ('REB', 6.5)])
    reasons = prop_reasons(_bet(stat='PTS', line=21.5), games, _games([]), 'en', validation={},
                           signals=[other, _signal(bet_type='PTS', line=21.5, parts=[]), h6])
    layout = panel_layout(reasons)
    assert layout['mispricing'] == [] and not any(r['kind'] == MISPRICING for _, rs in layout['context'] for r in rs)
    offers = [about for about, _ in layout['research']]
    assert offers[0] == ('PTS', 21.5)                                    # this offer's first
    assert ('PR', 30.5) in offers and all(len(rs) >= 1 for _, rs in layout['research'])
    assert [g for g, _ in layout['context']] == [g for g in ('history', 'minutes_role', 'opportunity',
                                                             'environment', 'opponent', 'market')
                                                 if g in {g for g, _ in layout['context']}]
    admitted = panel_layout(prop_reasons(_bet(stat='ARP', line=33.5), games, _games([]), 'en', validation={},
                                         signals=[_signal(status=ADMITTED)]))
    assert len(admitted['mispricing']) == 1 and admitted['research'] == []


def test_the_main_models_sides_are_priced_like_price_props():
    from metrics import calibrate, expected_return_100, no_vig, prop_probability
    from reasons import main_sides
    values = pd.Series([18.0, 25, 31, 22, 27, 19, 24, 30, 21, 26, 23, 28])
    coef = {'a': 1.14, 'b': 0.17, 'c': 0.0, 'd': 0.0}
    sides = main_sides(values, 23.5, 1.85, 1.95, 25.2, coef, 'superbet_standard')
    m_over = no_vig(1.85, 1.95)[0]
    p = calibrate(prop_probability(values, 23.5, 'Over', m_over, mean=25.2)['p'], m_over, 'Over', coef)
    assert sides['Over']['p'] == pytest.approx(100 * p) and \
        sides['Over']['ev'] == pytest.approx(float(expected_return_100(p, 1.85, 'superbet_standard')))
    assert set(sides) == {'Over', 'Under'} and main_sides(values.iloc[0:0], 23.5, 1.85, 1.95, 25.2, coef,
                                                          'superbet_standard') == {}
