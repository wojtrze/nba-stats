import re

import pandas as pd

import i18n
from core import cards

ROW = {'name': 'Darius Acuff', 'side': 'Under', 'line': 1.5, 'bet_type': 'BLK', 'side odds': 1.55, 'proj avg': 0.6,
       'p win %': 66.2, 'side market %': 58.4, 'break-even net %': 73.3, 'pick % L10': 80.0, 'games': 14, 'wait': ''}


def test_card_reads_as_plain_sentences():
    c = cards.card(ROW, 'en', tip='Thu 01:30')
    assert c['title'] == "Darius Acuff · Under 1.5 BLK · @1.55 · Thu 01:30"
    assert c['lines'][0] == "we expect 0.6 against the line 1.5 · Under in 8 of his last 10"
    assert c['lines'][1] == "our chance 66% · Superbet's 58% · needed after tax 73%"


def test_card_in_polish_and_with_few_games_and_a_wait():
    c = cards.card({**ROW, 'bet_type': 'ARP', 'games': 4, 'pick % L10': 75.0, 'wait': 'no lineup'}, 'pl')
    assert ' PRA ' in c['title']
    assert 'w 3 z ost. 4 meczów' in c['lines'][0]
    assert c['lines'][-1] == "⏳ no lineup"


def test_card_skips_what_it_doesnt_know():
    c = cards.card({**ROW, 'proj avg': float('nan'), 'pick % L10': None, 'side market %': pd.NA}, 'en')
    assert c['lines'] == ["our chance 66% · needed after tax 73%"]


def test_card_texts_dont_encourage_betting():
    banned = re.compile(r"bet it|worth it|sure|pewn|warto|graj|obstaw", re.I)
    for key, words in i18n.TEXTS.items():
        if key.startswith('card.'):
            for text in words.values():
                assert not banned.search(text), key
