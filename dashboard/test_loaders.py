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
    loaders.rotowire_lineups.clear()
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
