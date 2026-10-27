"""The plain-language words of dashboard v2 (dashboard/i18n.py). Run with: python -m pytest tests"""
import os
import string
import sys

import numpy as np
import pandas as pd
import pytest

sys.path[:0] = [os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dashboard'),
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dashboard_v2')]

import i18n  # noqa: E402
from core.columns import OVERVIEW_PROPS, PROPS_MAIN, PROPS_MORE  # noqa: E402


def _fields(text: str) -> set:
    return {name.split('|')[0] for _, name, _, _ in string.Formatter().parse(text) if name}


def test_every_term_and_text_is_in_both_languages():
    for key, term in i18n.TERMS.items():
        for part in ('label', 'what', 'higher', 'lower', 'example'):
            words = getattr(term, part)
            if words is not None:
                assert set(words) == set(i18n.LANGS) and all(words.values()), (key, part)
    for key, words in i18n.TEXTS.items():
        assert set(words) == set(i18n.LANGS), key
        assert _fields(words['en']) == _fields(words['pl']), key        # the same values fill both


def test_the_numbers_a_pick_rests_on_say_what_more_and_less_mean():
    for key in i18n.DECISION_TERMS:
        term = i18n.TERMS[key]
        assert term.higher and term.lower, key
        for lang in i18n.LANGS:
            tip = i18n.tooltip(key, lang)
            assert '↑' in tip and '↓' in tip, (key, lang)


def test_every_props_and_overview_column_has_a_term():
    for column in PROPS_MAIN + PROPS_MORE + OVERVIEW_PROPS:
        assert i18n.term(column) is not None, column


def test_edge_tooltip_explains_with_an_example():
    en, pl = i18n.tooltip('edge pp', 'en'), i18n.tooltip('edge pp', 'pl')
    assert '52.6%' in en and '+2.4 pp' in en and 'break even' in en
    assert '52.6%' in pl and '+2.4 pp' in pl
    assert i18n.label('edge pp', 'pl') == "przewaga (pp)"
    assert i18n.label('edge pp', 'en', context='games') == "edge (pp), estimate"      # the games page's own
    assert i18n.label('not a column', 'pl') == 'not a column' and i18n.tooltip('not a column', 'pl') is None


def test_t_fills_values_and_fails_loudly():
    assert i18n.t('banner.all', 'pl', confirmed=2, total=5).startswith("📋 Każdy mecz")
    with pytest.raises(KeyError):
        i18n.t('no such text', 'en')
    with pytest.raises(KeyError):
        i18n.t('banner.all', 'de', confirmed=2, total=5)


def test_cell_values():
    assert [i18n.value(v, 'pl') for v in ('Over', 'Under', 'pass', '')] == ["Powyżej", "Poniżej", "odpuść", ""]
    assert i18n.value('starter ✔', 'pl') == "pierwsza piątka ✔" and i18n.value('Ques 50%', 'pl') == 'Ques 50%'
    assert i18n.value(np.nan, 'pl') is np.nan or pd.isna(i18n.value(np.nan, 'pl'))


def test_reasons_and_warnings_in_polish():
    from reasons import flag_texts, prop_flag_items, prop_reasons, verdict
    games = pd.DataFrame({'PTS': [20.0, 25, 22, 30, 18, 26, 24, 21, 27, 23, 25, 19], 'MIN': [34.0] * 12,
                          'type': ['home', 'away'] * 6, 'season_type': 'regular'})
    bet = {'name': 'A Player', 'stat': 'PTS', 'side': 'Over', 'line': 20.5, 'odds': 1.9, 'model %': 55.0,
           'break-even %': 52.6, 'edge pp': 2.4, 'edge low': -1.0, 'avg': 23.3, 'proj avg': 24.0, 'home': True}
    en = [r['text'] for r in prop_reasons(bet, games, games.iloc[0:0])]
    pl = [r['text'] for r in prop_reasons(bet, games, games.iloc[0:0], 'pl')]
    assert len(en) == len(pl)
    assert en[0].startswith("Model: Over wins 55%") and pl[0].startswith("Model: Powyżej wygrywa w 55%")
    assert any(text.startswith("Oczekiwane dziś 24.0 PTS") for text in pl)
    items = prop_flag_items(3, True, 50, 'Ques 50%', pd.Series([10.0, 30, 12]), -2.0, 'Over')
    assert [k for k, _ in items] == ['flag.few_games', 'flag.preseason', 'flag.may_not_play', 'flag.line_against']
    assert flag_texts(items)[0] == "Only 3 games in the sample: too few to trust the numbers"
    assert flag_texts(items, 'pl')[0] == "Tylko 3 mecze w próbie: za mało, żeby ufać liczbom"
    assert flag_texts([('flag.few_games', {'n': 5})], 'pl')[0].startswith("Tylko 5 meczów")
    assert flag_texts([('flag.few_games', {'n': 1})])[0].startswith("Only 1 game in")
    assert [i18n.plural(n, 'mecz', 'mecze', 'meczów', 'pl') for n in (1, 2, 4, 5, 12, 22, 25)] ==         ['mecz', 'mecze', 'mecze', 'meczów', 'meczów', 'mecze', 'meczów']
    word, _, why = verdict([{'supports': False, 'text': 'x', 'flag': False}], 2.4, np.nan, 'pl')
    assert word == 'Pass' and why.startswith("Model meczów")                     # a game outcome: never past Pass
    assert i18n.t('verdict.Pass', 'pl') == "Odpuść"


def test_every_results_and_games_column_has_a_term_in_its_context():
    import night_view
    from core.columns import (GAMES_ABSENCES, GAMES_MARKETS, GAMES_SUMMARY, RATE_COLUMNS, RESULTS_ALL,
                              RESULTS_BY_TYPE)
    from nightly import GROUP_AXES
    for context, columns in (('games', GAMES_SUMMARY + GAMES_MARKETS + GAMES_ABSENCES),
                             ('results', RESULTS_ALL + RESULTS_BY_TYPE + RATE_COLUMNS + night_view.LINE_COLUMNS
                              + night_view.GROUP_COLUMNS + night_view.GAME_COLUMNS + list(GROUP_AXES))):
        for column in columns:
            assert i18n.term(column, context) is not None, (context, column)
    assert i18n.label('pick', 'en', 'results') == "our pick then"            # not tonight's pick
    assert i18n.label('model %', 'pl', 'games') == "szansa z modelu %"        # the game model's, not calibrated


def test_game_reasons_and_labels_in_polish():
    from core.labels import describe_outcome, winner
    from reasons import game_flags
    outcome = {'market': 'TOTAL', 'side': 'over', 'line': 225.5, 'team': None}
    assert describe_outcome(outcome) == "Total over 225.5"
    assert describe_outcome(outcome, 'pl') == "Suma powyżej 225.5"
    assert describe_outcome({'market': 'ML', 'side': 'home', 'line': np.nan, 'team': 'bos'}, 'pl') == "Zwycięzca BOS"
    assert winner({'margin': -3.5}, 'bos', 'ny', 'pl') == "NY o 3.5"
    assert game_flags(20, 2, False, 'pl')[0].startswith("Początek sezonu")
    assert len(game_flags(20, 2, False)) == 3 and game_flags(1, 20, True, 'pl') == []
