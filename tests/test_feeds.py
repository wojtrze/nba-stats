"""RotoWire and Superbet parsing, against pages saved on 2026-10-20. Run with: python -m pytest tests"""
import json
import os
from collections import Counter

import pandas as pd
import pytest

from lineup_fetcher import espn_team, parse_game_lines, parse_lineups, players_unlikely_to_play
from name_resolver import NameResolver, normalize
from superbet_fetcher import event_game_odds, event_props, main_lines

FIXTURES = os.path.join(os.path.dirname(__file__), 'fixtures')


@pytest.fixture(scope='module')
def lineups():
    with open(os.path.join(FIXTURES, 'rotowire_lineups.html'), encoding='utf8') as f:
        return parse_lineups(f.read())


@pytest.fixture(scope='module')
def event():
    with open(os.path.join(FIXTURES, 'superbet_event.json'), encoding='utf8') as f:
        return json.load(f)


def test_rotowire_games_and_starters(lineups):
    df = pd.DataFrame(lineups)
    assert set(zip(df['away'], df['home'])) == {('bos', 'det'), ('phi', 'ny'), ('okc', 'sa')}
    starters = df[df['role'] == 'starter']
    assert starters.groupby('team').size().to_dict() == {t: 5 for t in ['bos', 'det', 'phi', 'ny', 'okc', 'sa']}
    bos = starters[starters['team'] == 'bos']
    assert bos['name'].tolist() == ['Derrick White', 'Paul George', 'Jayson Tatum', 'Jordan Walsh', 'Mitchell Robinson']
    assert bos['pos'].tolist() == ['PG', 'SG', 'SF', 'PF', 'C']
    assert (df['game_date'] == '2026-10-20').all() and set(df['lineup_status']) == {'expected'}


def test_rotowire_may_not_play(lineups):
    carter = next(p for p in lineups if p['name'] == 'Devin Carter')
    assert (carter['role'], carter['team'], carter['play_pct'], carter['injury'], carter['rotowire_id']) == \
        ('may_not_play', 'bos', 0, 'Out', 6265)
    unlikely = players_unlikely_to_play(lineups)
    assert {'name': 'Adem Bona', 'team': 'phi', 'likelihood': 50} in unlikely
    assert all(p['likelihood'] < 100 for p in unlikely)


def test_rotowire_team_codes_and_game_lines():
    assert [espn_team(c) for c in ['NYK', 'SAS', 'GSW', 'BOS', 'uta']] == ['ny', 'sa', 'gs', 'bos', 'utah']
    with open(os.path.join(FIXTURES, 'rotowire_lineups.html'), encoding='utf8') as f:
        lines = parse_game_lines(f.read())
    assert lines[0] == {'away': 'bos', 'home': 'det', 'line': 'BOS -120', 'spread': 'BOS -1.5', 'total': '221.5 Pts'}


def test_superbet_player_props(event):
    props = event_props(event)
    counts = Counter(p['bet_type'] for p in props)
    assert {'PTS', 'REB', 'AST', '3PM', 'PA', 'PR', 'RA', 'ARP', 'BLK', 'STL', 'TO'} <= set(counts)
    cade = [p for p in props if p['name'] == 'Cunningham, Cade' and p['bet_type'] == 'PTS']
    assert {(p['over_under'], p['line'], p['odds']) for p in cade} == {('Under', 23.5, 1.9), ('Over', 23.5, 1.82)}
    assert cade[0]['home'] == 'det' and cade[0]['away'] == 'bos' and cade[0]['name_ESPN'] == 'CadeCunningham'
    assert counts['PTS'] % 2 == 0   # over and under of every line


def test_superbet_game_odds_and_main_lines(event):
    rows = event_game_odds(event)
    ml = {r['side']: (r['team'], r['odds']) for r in rows if r['market'] == 'ML'}
    assert ml == {'home': ('det', 2.0), 'away': ('bos', 1.78)}
    spread = [r for r in rows if r['market'] == 'SPREAD' and r['side'] == 'home' and r['line'] == -8.5]
    assert spread and spread[0]['team'] == 'det' and spread[0]['odds'] == 3.45
    main = {(r['market'], r['side']): r['line'] for r in main_lines(rows)}
    assert main[('SPREAD', 'home')] == -main[('SPREAD', 'away')]
    assert main[('TOTAL', 'over')] == main[('TOTAL', 'under')] == 220.5
    assert {m for m, _ in main} == {'ML', 'SPREAD', 'TOTAL', 'HOME_TOTAL', 'AWAY_TOTAL'}


def test_normalize_names():
    assert normalize('Jackson Jr., Jaren') == normalize('Jaren Jackson Jr.') == 'jaren jackson'
    assert normalize('Nikola Jokić') == 'nikola jokic'
    assert normalize("De'Aaron Fox") == 'deaaron fox'
    assert normalize('Shai Gilgeous-Alexander') == 'shai gilgeous alexander'


def test_name_resolver_prefers_team_and_initial_fallback():
    logs = pd.DataFrame({
        'player_id_ESPN': [1, 2, 3, 4],
        'player_display_name': ['Jalen Williams', 'Jalen Williams', 'Nicolas Claxton', 'Derrick Jones Jr.'],
        'team': ['okc', 'por', 'bkn', 'lac'],
        'Date': pd.to_datetime(['2026-10-10'] * 4)})
    r = NameResolver(logs)
    assert r.resolve('Jalen Williams', 'okc') == 1
    assert r.resolve('Williams, Jalen', ['por', 'lal']) == 2
    assert r.resolve('Jalen Williams') is None           # ambiguous without a team
    assert r.resolve('Nic Claxton', 'bkn') == 3
    assert r.resolve('Derrick Jones', 'lac') == 4
    assert r.resolve('Nobody Here', 'lac') is None
