"""Run with: python -m pytest dashboard"""
import re

import numpy as np
import pandas as pd
import pytest

import decisions
import i18n
import models
from decisions import (CZEKAJ, NIE_OBSTAWIAJ, NIEDOSTEPNE, OBSTAW, MAX_ODDS_AGE, actionable, game_decisions,
                       offer_changed, offer_decision, offers_table, player_decision, team_decision)
from reasons import prop_reasons

NOW = pd.Timestamp('2026-10-30T22:00:00Z')
FETCHED = '2026-10-30T21:23:24Z'


def _line(name='A', ev=-8.0, edge=-4.0, odds=1.9, side='Over', role='starter', flag='', event=1, **kw):
    return {'event_id': event, 'name': name, 'name_ESPN': name, 'bet_type': 'PTS', 'line': 20.5, 'home': 'bos',
            'away': 'nyk', 'side': side, 'side odds': odds, 'p win %': 55.0, 'break-even net %': 59.8,
            'edge net pp': edge, 'ev net 100': ev, 'red flag': flag, 'RotoWire': role} | kw


def _lineups(*teams):
    return pd.DataFrame({'team': list(teams), 'fetched_at': '2026-10-30T21:00:00Z'})


def _decide(rows, lineups=None, threshold=decisions.ADMITTED_THRESHOLD, fetched=FETCHED, status=models.FITTED):
    lineups = _lineups('bos', 'nyk') if lineups is None else lineups
    return player_decision(pd.DataFrame(rows), status, lineups, fetched, NOW, threshold)


def test_no_offer_gets_obstaw_without_a_recorded_threshold():
    assert decisions.ADMITTED_THRESHOLD is None
    # even a line with a large positive expected return: the threshold, not the numbers, is missing
    d = _decide([_line(ev=30.0, edge=12.0), _line('B', ev=5.0, edge=2.0)])
    assert d['status'] == NIE_OBSTAWIAJ and d['offer'] is None
    assert d['reason'] == 'decision.reason.no_threshold'


def test_the_number_of_reasons_doesnt_change_the_decision():
    rows = [_line(ev=-3.0), _line('B', ev=-9.0)]
    before = _decide(rows)
    # the reasons are made after the decision and aren't an input to it: write many, then decide again
    games = pd.DataFrame({'PTS': [25.0] * 12, 'MIN': [34.0] * 12, 'type': ['home', 'away'] * 6,
                          'season_type': 'regular', 'Date': pd.date_range('2026-10-01', periods=12)})
    bet = {'name': 'A', 'stat': 'PTS', 'side': 'Over', 'line': 20.5, 'odds': 1.9, 'model %': 55.0,
           'break-even %': 59.8, 'edge pp': -4.8, 'avg': 25.0, 'proj avg': 25.0, 'odds_at': FETCHED, 'opp': 'bos'}
    many = prop_reasons(bet, games, games)
    few = prop_reasons(bet | {'odds_at': None}, games.head(2), games.iloc[0:0])
    assert len(many) > len(few)
    assert _decide(rows) == before
    assert 'reasons' not in player_decision.__code__.co_varnames[:player_decision.__code__.co_argcount]


def test_missing_odds_mean_wait():
    assert _decide([_line(odds=np.nan), _line('B', side='', odds=np.nan)])['status'] == CZEKAJ
    assert _decide([])['status'] == CZEKAJ
    assert _decide([_line()])['reason'] != 'decision.reason.no_odds'


def test_stale_odds_mean_wait():
    old = (NOW - MAX_ODDS_AGE - pd.Timedelta(minutes=1)).isoformat()
    d = _decide([_line()], fetched=old)
    assert d['status'] == CZEKAJ and d['reason'] == 'decision.reason.stale_odds'


def test_a_missing_lineup_or_a_questionable_player_means_wait():
    d = _decide([_line()], lineups=_lineups('bos'))
    assert d['status'] == CZEKAJ and d['values']['teams'] == 'NYK'
    d = _decide([_line(ev=-2.0, role='Ques 50%'), _line('B', ev=-6.0)])
    assert d['status'] == CZEKAJ and d['reason'] == 'decision.reason.questionable'
    # a player who's out won't play: his lines aren't offers, so they don't make the game wait
    assert _decide([_line(ev=-2.0, role='Out 0%'), _line('B', ev=-6.0)])['status'] == NIE_OBSTAWIAJ


def test_a_tie_isnt_broken_arbitrarily():
    rows = [_line('A', ev=6.0, edge=3.0), _line('B', ev=6.05, edge=3.1)]
    assert _decide(rows, threshold=1.0)['status'] == CZEKAJ
    one = _decide([_line('A', ev=6.0, edge=3.0), _line('B', ev=2.0, edge=1.5)], threshold=1.0)
    assert one['status'] == OBSTAW and one['offer']['name'] == 'A'
    # a warned line never qualifies
    assert _decide([_line('A', ev=6.0, edge=3.0, flag='few games')], threshold=1.0)['status'] == NIE_OBSTAWIAJ


def test_props_without_a_valid_calibration_are_unavailable():
    for status in (models.MISSING, models.VERSION_MISMATCH):
        assert _decide([_line(ev=20.0, edge=9.0)], threshold=1.0, status=status)['status'] == NIEDOSTEPNE


def test_every_game_market_is_unavailable():
    projection = {'home_pts': 130.0, 'away_pts': 100.0, 'margin': 30.0, 'total': 230.0, 'pace': 100.0}
    for market in ('ML', 'SPREAD', 'TOTAL', 'HOME_TOTAL', 'AWAY_TOTAL'):
        game = {'event_id': 1, 'projection': projection, 'edges': pd.DataFrame([{'market': market, 'edge pp': 40.0}])}
        assert team_decision(game)['status'] == NIEDOSTEPNE
    # nothing admits the game model automatically, however many outcomes settle
    assert team_decision(None)['status'] == NIEDOSTEPNE


def test_one_decision_per_game_and_one_offer_at_most():
    table = pd.DataFrame([_line('A', event=1), _line('B', event=1), _line('C', event=2)])
    decided = game_decisions(table, models.FITTED, _lineups('bos', 'nyk'), FETCHED, NOW)
    assert set(decided) == {1, 2}
    assert all(d['status'] in decisions.STATUSES for d in decided.values())
    # nothing qualifies: nothing to list, and no "least loss" ranking of the rest
    assert actionable(decided) == [] and offers_table(decided).empty


def test_under_obstaw_only_the_chosen_offer_is_named():
    rows = pd.DataFrame([_line('A', ev=6.0, edge=3.0), _line('B', ev=2.0, edge=1.5)])
    d = player_decision(rows, models.FITTED, _lineups('bos', 'nyk'), FETCHED, NOW, threshold=1.0)
    assert offer_decision(d, rows.iloc[0])['status'] == OBSTAW
    assert offer_decision(d, rows.iloc[1])['status'] == NIE_OBSTAWIAJ
    assert len(offers_table({1: d})) == 1


def test_a_changed_quote_is_reported():
    assert not offer_changed(None, {'line': 20.5, 'odds': 1.9})['changed']
    assert not offer_changed({'line': 20.5, 'odds': 1.9}, {'line': 20.5, 'odds': 1.9})['changed']
    odds = offer_changed({'line': 20.5, 'odds': 1.9}, {'line': 20.5, 'odds': 1.85})
    assert odds['changed'] and odds['odds'] == (1.9, 1.85) and odds['line'] is None
    line = offer_changed({'line': 20.5, 'odds': 1.9}, {'line': 21.5, 'odds': 1.9})
    assert line['changed'] and line['line'] == (20.5, 21.5)


def test_no_current_line_gets_obstaw_or_a_stake():
    """Priced with the calibration in use and the recorded threshold (none): no line of a real-looking table gets
    OBSTAW, and the slip's stake for every line is 0."""
    from bets import kelly_stake, staking_chance
    rows = [_line(chr(65 + i), ev=ev, edge=ev / 2) for i, ev in enumerate([25.0, 3.0, -1.0, -12.0])]
    d = _decide(rows)
    assert d['status'] != OBSTAW
    for r in rows:
        bet = {'kind': 'prop', 'model_pct': r['p win %'], 'decision': offer_decision(d, pd.Series(r))['status'],
               'edge_low': 5.0}
        assert kelly_stake(staking_chance(bet), r['side odds'], 1000) == 0


def test_no_page_text_encourages_betting_when_nothing_qualifies():
    # the old verdict's words as labels (capitalised), "sure thing", "recommendation" and the least-loss list
    banned = re.compile(r"\bGraj\b|\bRozważ\b|\bLean\b|pewniak|rekomendac|[Nn]ajmniejsza strata|[Ll]east loss")
    for key, words in i18n.TEXTS.items():
        for lang, text in words.items():
            assert not banned.search(text), (key, lang)
    for key in ('verdict.Bet', 'overview.least_loss', 'overview.game_edges', 'overview.best_price'):
        assert key not in i18n.TEXTS


def test_settling_a_night_isnt_described_as_the_users_profit():
    for key, words in i18n.TEXTS.items():
        if key.startswith(('results.', 'night.')):
            for text in words.values():
                assert not re.search(r"zysk|zarob|profit|you won|wygrałeś", text, re.I), key
    assert 'Rozliczenie ocen modelu' in i18n.t('results.title', 'pl')
    assert 'nie jest wynik' in i18n.t('results.purpose', 'pl') and 'ani dowód' in i18n.t('results.purpose', 'pl')
    for key in ('ROI %', 'our ROI %', 'best side ROI %'):
        assert 'zysk' not in i18n.label(key, 'pl') and 'profit' not in i18n.label(key, 'en')


def test_the_interface_says_what_the_range_and_the_factor_are():
    assert 'nie jest przedział pewności modelu' in i18n.tooltip('edge low', 'pl')
    assert "isn't a confidence range of the model" in i18n.tooltip('edge low', 'en')
    assert 'tempo' not in i18n.t('detail.kpi.game_help', 'pl', pace=1.0, matchup=1.0, word='x').lower()
    assert 'opis' in i18n.t('reason.teammates', 'pl', names='B', name='A', adj=1.0, stat='PTS', n=4)
    assert 'nie wpływ' in i18n.t('mates.col.change_help', 'pl', stat='PTS')


@pytest.mark.parametrize('status', decisions.STATUSES)
def test_every_status_has_words(status):
    assert i18n.t(f'decision.{status}', 'pl') and i18n.t(f'decision.{status}', 'en')


def test_the_evaluated_side_has_its_own_words_and_games_keep_theirs():
    assert i18n.label('side', 'pl') == "oceniana strona" and i18n.label('side', 'en') == "evaluated side"
    assert i18n.label('side', 'pl', 'games') == "strona"


# --- the shortlist: the night's best lines by expected return, never a bet signal ---

def _slate(n_games=8, per_game=3):
    rows = []
    for g in range(n_games):
        for k in range(per_game):
            rows.append(_line(f'P{g}-{k}', ev=-10.0 - g - 0.1 * k, event=g, **{'market over %': 50.0}))
    return pd.DataFrame(rows)


def _stars(rows, decided=None):
    return decisions.stars(pd.DataFrame(rows) if isinstance(rows, list) else rows, decided).set_index('name_ESPN')


def test_stars_follow_the_place_in_the_night():
    # 40 lines over 40 games, one per player: 4★ = best 5% (2), 3★ to 20% (6), 2★ to 50% (12), 1★ the rest
    rows = pd.DataFrame([_line(f'P{k}', ev=-10.0 - k, event=k) for k in range(40)])
    s = decisions.stars(rows)
    assert list(s['stars'].value_counts().sort_index()) == [20, 12, 6, 2]
    assert list(s['rank']) == list(range(1, 41)) and list(s['name_ESPN'][:2]) == ['P0', 'P1']
    assert (s['stars'] < decisions.MAX_STARS).all()


def test_four_stars_once_per_game_and_for_a_players_best_line():
    rows = [_line('A', ev=-1.0, event=1), _line('B', ev=-2.0, event=1),               # same game: B drops to 3★
            _line('C', ev=-3.0, event=2, bet_type='REB'), _line('C', ev=-3.5, event=2),  # C's second line: 3★
            *[_line(f'Z{k}', ev=-20.0 - k, event=10 + k) for k in range(56)]]   # 60 lines: 5% = 3
    s = decisions.stars(pd.DataFrame(rows))
    top = s[s['stars'] == 4]
    assert top['event_id'].is_unique and list(top['name_ESPN']) == ['A', 'C']
    by = s.set_index(['name_ESPN', 'bet_type'])['stars']
    assert by[('B', 'PTS')] == 3 and by[('C', 'PTS')] == 3


def test_red_flags_and_unsure_players_get_zero_and_unadmitted_games_no_rating():
    rows = [_line('A', ev=-5.0, flag='Too few games', event=1), _line('B', ev=-6.0, role='Ques 50%', event=2),
            _line('D', ev=-8.0, event=4), _line('E', ev=-9.0, event=5)]
    unadmitted = {5: {'status': NIEDOSTEPNE, 'reason': 'decision.reason.no_calibration'}}
    s = _stars(rows, unadmitted)
    assert s.loc['A', 'stars'] == 0 and s.loc['B', 'stars'] == 0 and s.loc['D', 'stars'] >= 1
    assert pd.isna(s.loc['E', 'stars'])
    assert decisions.star_text(s.loc['E', 'stars']) == '–' and decisions.star_text(3) == '★★★☆☆'


def test_five_stars_only_for_the_bet_offer():
    rows = [_line('A', ev=5.0, edge=6.0, event=1), _line('B', ev=-6.0, event=2)]
    assert (_stars(rows)['stars'] < decisions.MAX_STARS).all()
    decided = game_decisions(pd.DataFrame(rows), models.FITTED, _lineups('bos', 'nyk'), FETCHED, NOW)
    assert actionable(decided) == []                                    # no threshold: no 5★ either
    with_threshold = {1: _decide([rows[0]], threshold=3.0)}
    assert with_threshold[1]['status'] == OBSTAW
    assert _stars(rows, with_threshold).loc['A', 'stars'] == decisions.MAX_STARS


def test_stars_are_never_a_bet():
    rows = pd.DataFrame([_line(f'P{k}', ev=-10.0 - k, event=k) for k in range(8)])
    s = decisions.stars(rows)
    assert (s['ev net 100'] < 0).all()      # every rated line still loses on average: the page says so
    assert actionable(game_decisions(rows, models.FITTED, _lineups('bos', 'nyk'), FETCHED, NOW)) == []


def test_stars_mark_a_waiting_game_instead_of_hiding_it():
    rows = [_line('A', ev=-5.0, event=1), _line('B', ev=-6.0, event=2)]
    waiting = {1: {'status': CZEKAJ, 'reason': 'decision.reason.stale_odds'},
               2: {'status': NIE_OBSTAWIAJ, 'reason': 'decision.reason.no_threshold'}}
    s = _stars(rows, waiting)
    assert list(s['wait']) == ['decision.reason.stale_odds', '']


def test_stars_rate_each_night_apart_and_break_ties_the_same_way():
    rows = pd.DataFrame([_line('A', ev=-5.0, event=1, start_time='2026-10-30T23:00:00Z'),
                         _line('B', ev=-5.0, event=2, start_time='2026-10-30T23:30:00Z'),
                         _line('C', ev=-9.0, event=3, start_time='2026-10-31T23:00:00Z')])
    s = decisions.stars(rows)
    assert list(s['name_ESPN']) == ['A', 'B', 'C'] and list(s['rank']) == [1, 2, 1]
    assert list(decisions.stars(rows.iloc[::-1])['name_ESPN']) == ['A', 'B', 'C']


def test_stars_side_price_and_gap():
    rows = pd.DataFrame([_line('A', side='Under', **{'market over %': 40.0, 'p win %': 63.0})])
    s = decisions.stars(rows)
    assert s['side market %'].iloc[0] == 60.0 and s['above price pp'].iloc[0] == pytest.approx(3.0)


def test_stars_of_nothing_is_empty():
    assert decisions.stars(pd.DataFrame()).empty
    assert decisions.stars(pd.DataFrame([_line(odds=np.nan)])).empty
