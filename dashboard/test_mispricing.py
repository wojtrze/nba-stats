"""Run with: python -m pytest dashboard"""
import numpy as np
import pandas as pd

import i18n
from metrics import count_over
from mispricing import (ADMITTED, REJECTED, UNTESTED, combo_over_from_parts, combo_signals, hypothesis_status,
                        league_rates, league_spreads, market_mean, offer_signals, pooled_correlations,
                        shooting_signals, spread_signals)
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


def test_an_untested_signal_answers_the_five_questions_without_a_direction():
    [r] = _mispricing([_signal()], stat='ARP', line=33.5)
    lines = r['text'].split("  \n")
    assert r['supports'] is None and r['validation'] == UNTESTED
    assert lines[0].startswith('Za mało, by pokryć podatek') and '7.0 pp' in lines[0] and '11.0 pp' in lines[0]
    assert lines[1].startswith('Co się stało') and 'PTS 21.5' in lines[1] and '58%' in lines[1]
    assert lines[2].startswith('Dlaczego')
    assert 'znika' in lines[3]
    assert lines[4].startswith('🧪') and 'nie wskazówka do gry' in lines[4]


def test_signals_shown_only_when_they_concern_the_line_and_matter():
    assert _mispricing([_signal()], stat='REB', line=6.5)           # a part of the combo
    assert not _mispricing([_signal()], stat='3PM', line=2.5)      # another stat
    assert not _mispricing([_signal(gap_pp=2.9)], stat='ARP', line=33.5)
    assert not _mispricing([_signal(status=REJECTED)], stat='ARP', line=33.5)


def test_only_an_admitted_hypothesis_argues_for_or_against():
    assert _mispricing([_signal(status=ADMITTED)], stat='ARP', side='Over')[0]['supports'] is True
    assert _mispricing([_signal(status=ADMITTED)], stat='ARP', side='Under')[0]['supports'] is False
    clears = _mispricing([_signal(status=ADMITTED, clears=True, gap_pp=12.0)], stat='ARP')[0]['text']
    assert 'ta różnica to pokrywa' in clears and clears.split("  \n")[-1].startswith('✅')


def test_the_signal_texts_are_in_both_languages():
    keys = [f'mispricing.{h}.{part}' for h in ('h1', 'h2', 'h6') for part in ('short', 'clears', 'what', 'why')]
    for key in keys + ['mispricing.expiry.line_or_odds_change', 'mispricing.status.untested',
                       'mispricing.status.admitted', 'panel.mispricing', 'panel.mispricing_note']:
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
    assert 'zakładają, że trafi 44% rzutów; trafia 35% (60 z 170 w 25 meczach' in r['text']
    assert not [r for r in prop_reasons(_bet(stat='3PM', line=2.5), games, _games([]), 'pl', validation={},
                                        signals=[h2 | {'gap_pp': 5.9}]) if r['kind'] == MISPRICING]
    h6 = _signal(hypothesis='H6', bet_type='BLK', line=0.5, parts=[], side='Under', gap_pp=4.5, spread=1.8,
                 own_spread=2.1, league_spread=1.07, below=0.48)
    [r] = [r for r in prop_reasons(_bet(stat='BLK', line=0.5, side='Under'), games, _games([]), 'pl',
                                   validation={}, signals=[h6]) if r['kind'] == MISPRICING]
    assert 'w 48% meczów' in r['text'] and 'rozrzut 1.8×' in r['text'] and r['text'].startswith('Za mało')


def test_a_signal_that_clears_the_tax_says_how_such_signals_did_on_the_exploration_nights():
    explored = {'nights': 12, 'through': '2026-10-31', 'signals': 130, 'won': 54.6, 'roi': -9.8}
    [r] = _mispricing([_signal(clears=True, gap_pp=12.0, exploration=explored)], stat='ARP')
    assert r['text'].split("  \n")[-1] == ("Na nocach rozpoznania (12 nocy do 2026-10-31) takich sygnałów, które "
                                           "pokrywały podatek, było 130: wygrało 55%, wynik -9.8 zł na 100 zł stawki "
                                           "po podatku.")
    [short] = _mispricing([_signal(exploration=explored)], stat='ARP')
    assert 'rozpoznania' not in short['text']


def test_the_status_file_feeds_the_signal():
    status = {'H1': {'status': ADMITTED, 'exploration': {'signals': 1}}}
    s = combo_signals(_lines(), _player(), pooled_correlations(_player()), status=status)[0]
    assert s['status'] == ADMITTED and s['exploration'] == {'signals': 1}
