"""Run with: python -m pytest dashboard"""
import os

import pandas as pd
import pytest

import lineup_fetcher
import loaders
import superbet_fetcher

EVENT = {'home': 'bos', 'away': 'ny', 'event_id': 7, 'start_time': '2026-10-22T23:30:00Z'}
OFFERS = {'props': [{'name': 'Tatum, Jayson', 'name_ESPN': 'JaysonTatum', 'bet_type': 'PTS', 'line': 27.5,
                     'over_under': side, 'odds': odds, **EVENT} for side, odds in (('Over', 1.9), ('Under', 1.85))],
          'game_odds': [{'market': 'ML', 'side': side, 'line': None, 'odds': odds, 'team': team, **EVENT}
                        for side, odds, team in (('home', 1.5, 'bos'), ('away', 2.6, 'ny'))]}


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """An empty data folder, no RotoWire, no earlier request to Superbet."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(lineup_fetcher, 'fetch_lineups', lambda *a: (_ for _ in ()).throw(OSError("offline")))
    loaders._superbet_store().clear()
    loaders.clear_rotowire()
    yield tmp_path
    loaders._superbet_store().clear()


def _saved(name):
    path = os.path.join('data', '2026', f'{name}.csv')
    return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()


def test_every_fetch_is_saved(data_dir, monkeypatch):
    monkeypatch.setattr(superbet_fetcher, 'todays_offers', lambda: OFFERS)
    assert loaders.fetch_superbet() is None
    props, odds = _saved('superbet_props'), _saved('superbet_game_odds')
    assert len(props) == 1 and props['fetched_at'].nunique() == 1          # Over and Under in one row
    assert (props.loc[0, 'over_odds'], props.loc[0, 'under_odds']) == (1.9, 1.85)
    assert len(odds) == 2 and odds['fetched_at'].iloc[0] == props['fetched_at'].iloc[0]
    run = pd.read_csv(loaders.RUN_LOG).iloc[-1]                          # the Data center's "last fetch"
    assert (run['job'], run['exit_code']) == ('fetch', 0)
    assert run['started_at'] == props['fetched_at'].iloc[0]
    assert run['summary'] == "saved 1 player line and 2 game odds (1 game)"


def test_cooldown_blocks_a_second_request(data_dir, monkeypatch):
    calls = []
    monkeypatch.setattr(superbet_fetcher, 'todays_offers', lambda: calls.append(1) or OFFERS)
    assert loaders.fetch_superbet() is None
    assert "less than 5 minutes" in loaders.fetch_superbet()
    assert len(calls) == 1 and len(_saved('superbet_props')) == 1


def test_a_failed_fetch_saves_nothing(data_dir, monkeypatch):
    def blocked():
        raise ConnectionError("403 Forbidden")
    monkeypatch.setattr(superbet_fetcher, 'todays_offers', blocked)
    assert "403" in loaders.fetch_superbet()
    assert loaders.superbet_error() == "403 Forbidden"
    assert _saved('superbet_props').empty
    run = pd.read_csv(loaders.RUN_LOG).iloc[-1]
    assert (run['job'], run['exit_code'], run['summary']) == ('fetch', 1, "failed: 403 Forbidden")


# --- RotoWire: saved whenever it changed ---

def _player(name, team='bos', role='starter', pct=None, injury=None, status='expected', day='2026-10-22'):
    return {'game_date': day, 'tip_et': '7:30 PM ET', 'away': 'ny', 'home': 'bos', 'team': team,
            'side': 'home' if team == 'bos' else 'away', 'lineup_status': status, 'role': role, 'pos': 'G',
            'name': name, 'rotowire_id': 1, 'play_pct': pct, 'injury': injury}


PAGE = [_player('Jayson Tatum'), _player('Jaylen Brown', role='may_not_play', pct=50, injury='Ques'),
        _player('Jalen Brunson', team='ny')]


def test_lineup_changes_in_words():
    from daily_snapshot import lineup_changes
    old = pd.DataFrame(PAGE)
    new = pd.DataFrame([_player('Jayson Tatum', status='confirmed'),
                        _player('Jaylen Brown', role='may_not_play', pct=0, injury='Out', status='confirmed'),
                        _player('Mikal Bridges', team='ny', role='may_not_play', pct=25, injury='Doubt')])
    assert lineup_changes(old, new) == ["BOS lineup confirmed", "Jaylen Brown (BOS): Ques 50% → Out 0%",
                                        "new: Mikal Bridges (NY, Doubt 25%)", "no longer listed: Jalen Brunson (NY)"]
    assert lineup_changes(old, pd.DataFrame(PAGE)) == []


def test_lineups_saved_only_when_changed(data_dir):
    from daily_snapshot import save_lineups_if_changed
    first = save_lineups_if_changed(pd.DataFrame(PAGE), '2026-10-22T10:00:00Z')
    assert first == "saved 3 players for Oct 22 (first fetch of the day)"
    assert save_lineups_if_changed(pd.DataFrame(PAGE), '2026-10-22T10:30:00Z') == ''        # identical page
    changed = [*PAGE[:1], _player('Jaylen Brown', role='may_not_play', pct=0, injury='Out'), PAGE[2]]
    assert save_lineups_if_changed(pd.DataFrame(changed), '2026-10-22T11:00:00Z') == \
        "saved 3 players for Oct 22: 1 change – Jaylen Brown (BOS): Ques 50% → Out 0%"
    tomorrow = [_player('Jayson Tatum', day='2026-10-23')]                                   # another page
    assert save_lineups_if_changed(pd.DataFrame(tomorrow), '2026-10-22T11:05:00Z').endswith("(first fetch of the day)")
    saved = _saved('rotowire_lineups')
    assert saved['fetched_at'].unique().tolist() == ['2026-10-22T10:00:00Z', '2026-10-22T11:00:00Z',
                                                     '2026-10-22T11:05:00Z']


def test_the_shared_fetch_saves_and_logs(data_dir, monkeypatch):
    class Resolver:
        def add_ids(self, df, **kw):
            return df.assign(player_id_ESPN=None)
    monkeypatch.setattr(loaders, 'name_resolver', lambda: Resolver())
    monkeypatch.setattr(lineup_fetcher, 'fetch_lineups', lambda *a: PAGE)
    first = loaders.fetch_rotowire()
    assert first['live'] and first['saved'].endswith("(first fetch of the day)") and len(first['lineups']) == 3
    loaders.clear_rotowire()
    again = loaders.fetch_rotowire()                         # the same page half an hour later
    assert again['saved'] == '' and _saved('rotowire_lineups')['fetched_at'].nunique() == 1
    runs = pd.read_csv(loaders.RUN_LOG)
    assert runs['job'].tolist() == ['lineups']               # only the save is logged


def test_failed_lineups_fetch_saves_nothing(data_dir):
    out = loaders.fetch_rotowire()                           # the fixture's RotoWire is offline
    assert not out['live'] and out['error'] == "offline" and out['lineups'].empty
    assert _saved('rotowire_lineups').empty and not os.path.exists(loaders.RUN_LOG)
