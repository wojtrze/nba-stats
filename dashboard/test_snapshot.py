"""Run with: python -m pytest dashboard"""
import os

import pandas as pd
import pytest

import daily_snapshot
import models
import name_resolver
import nightly

PATH = os.path.join('data', '2026', 'superbet_props.csv')


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs(os.path.join('data', '2026'))
    yield tmp_path


def _line(fetched, pid, name='A', start='2026-10-21T23:30:00Z', **kw):
    return {'fetched_at': fetched, 'name': name, 'name_ESPN': name, 'home': 'bos', 'away': 'ny', 'bet_type': 'PTS',
            'line': 20.5, 'event_id': 1, 'start_time': start, 'over_odds': 1.9, 'under_odds': 1.85,
            'player_id_ESPN': pid} | kw


def test_a_new_column_keeps_the_saved_rows_as_they_were(data_dir):
    with open(PATH, 'w') as f:
        f.write("fetched_at,name,player_id_ESPN\n2026-10-20T10:00:00Z,A,4397475\n2026-10-20T10:00:00Z,B,\n")
    new = pd.DataFrame([{'name': 'C', 'player_id_ESPN': 7, 'signal': ''}])
    assert daily_snapshot._append('superbet_props', new, '2026-10-21T10:00:00Z') == 1
    with open(PATH) as f:
        text = f.read().splitlines()
    assert text[0] == 'fetched_at,name,player_id_ESPN,signal'
    assert text[1:3] == ['2026-10-20T10:00:00Z,A,4397475,', '2026-10-20T10:00:00Z,B,,']


def test_reprice_rewrites_only_the_model_columns(data_dir, monkeypatch):
    saved = pd.DataFrame([_line('2026-10-21T10:00:00Z', 4397475.0, pick='Under', model_pct=51.0, signal='🔴'),
                          _line('2026-10-21T10:00:00Z', None, name='Nobody'),
                          _line('2026-10-21T20:00:00Z', 4397475.0, pick='Under', model_pct=52.0)])
    saved.to_csv(PATH, index=False)
    odds = pd.DataFrame([{'fetched_at': f, 'event_id': 1, 'market': 'ML'} for f in saved['fetched_at'].unique()])
    odds.to_csv(os.path.join('data', '2026', 'superbet_game_odds.csv'), index=False)
    pd.DataFrame([{'fetched_at': '2026-10-21T09:00:00Z', 'game_date': '2026-10-21', 'team': 'bos', 'name': 'X'}]) \
        .to_csv(os.path.join('data', '2026', 'rotowire_lineups.csv'), index=False)

    class Resolver:
        def __init__(self, logs):
            pass

        def add_ids(self, df, team_cols=None):
            return df.assign(player_id_ESPN=df['name'].map({'A': 4397475}).astype(object))

    calls = []

    def recompute(rows, logs, games, lineups, odds_, night):
        calls.append((rows['fetched_at'].iloc[0], len(odds_), len(lineups), str(night.date())))
        return pd.DataFrame({'pick': 'Over', 'model_pct': 60.0, 'edge_pp': 7.0, 'edge_low': 1.0, 'proj_avg': 24.0,
                             'signal': '🟢', 'red_flag': '', 'raw_over_pct': 63.5, 'raw_under_pct': 36.5,
                             'market_over_pct': 49.2}, index=rows.index)

    monkeypatch.setattr(daily_snapshot, 'load_player_gamelogs', lambda seasons: pd.DataFrame())
    monkeypatch.setattr(daily_snapshot, 'load_games', lambda seasons: pd.DataFrame())
    monkeypatch.setattr(models, 'prepare_logs', lambda logs: logs)
    monkeypatch.setattr(name_resolver, 'NameResolver', Resolver)
    monkeypatch.setattr(nightly, 'recompute_props', recompute)

    assert daily_snapshot.reprice_snapshots() == 3
    assert calls == [('2026-10-21T10:00:00Z', 1, 1, '2026-10-21'), ('2026-10-21T20:00:00Z', 1, 1, '2026-10-21')]
    out = pd.read_csv(PATH, dtype=str, keep_default_na=False)
    assert out['player_id_ESPN'].tolist() == ['4397475', '', '4397475']
    assert out['pick'].tolist() == ['Over'] * 3 and out['signal'].tolist() == ['🟢'] * 3
    assert out['raw_over_pct'].tolist() == ['63.5'] * 3 and out['market_over_pct'].tolist() == ['49.2'] * 3
    assert out['fetched_at'].tolist() == saved['fetched_at'].tolist() and out['name'].tolist() == ['A', 'Nobody', 'A']
    assert out['line'].tolist() == ['20.5'] * 3 and out['under_odds'].tolist() == ['1.85'] * 3
