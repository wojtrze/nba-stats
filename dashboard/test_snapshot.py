"""Run with: python -m pytest dashboard"""
import json
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


def test_reprice_writes_a_replay_and_leaves_the_record_alone(data_dir, monkeypatch):
    saved = pd.DataFrame([_line('2026-10-21T10:00:00Z', 4397475.0, pick='Under', model_pct=51.0, signal='🔴'),
                          _line('2026-10-21T10:00:00Z', None, name='Nobody'),
                          _line('2026-10-21T20:00:00Z', 4397475.0, pick='Under', model_pct=52.0)])
    saved.to_csv(PATH, index=False)
    with open(PATH, 'rb') as f:
        record = f.read()
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
    with open(PATH, 'rb') as f:
        assert f.read() == record   # what each fetch showed is never priced again in place
    out = pd.read_csv(os.path.join('data', '2026', 'superbet_props_replay.csv'), dtype=str, keep_default_na=False)
    assert out['player_id_ESPN'].tolist() == ['4397475', '', '4397475']
    assert out['pick'].tolist() == ['Over'] * 3 and out['signal'].tolist() == ['🟢'] * 3
    assert out['raw_over_pct'].tolist() == ['63.5'] * 3 and out['market_over_pct'].tolist() == ['49.2'] * 3
    assert out['fetched_at'].tolist() == saved['fetched_at'].tolist() and out['name'].tolist() == ['A', 'Nobody', 'A']
    assert out['line'].tolist() == ['20.5'] * 3 and out['under_odds'].tolist() == ['1.85'] * 3
    assert out['prediction_origin'].tolist() == ['historical_replay'] * 3
    assert out['model_version'].tolist() == [nightly.MODEL_VERSION] * 3
    assert out['calibration_id'].tolist() == ['none'] * 3   # no calibration file in the test folder

    # another model's replay is kept next to this one's, which a second reprice replaces
    out.assign(model_version='old', raw_over_pct='70.0').to_csv(
        os.path.join('data', '2026', 'superbet_props_replay.csv'), index=False)
    pd.concat([pd.read_csv(os.path.join('data', '2026', 'superbet_props_replay.csv'), dtype=str), out])         .to_csv(os.path.join('data', '2026', 'superbet_props_replay.csv'), index=False)
    assert daily_snapshot.reprice_snapshots() == 3
    both = pd.read_csv(os.path.join('data', '2026', 'superbet_props_replay.csv'), dtype=str, keep_default_na=False)
    assert both.groupby('model_version').size().to_dict() == {nightly.MODEL_VERSION: 3, 'old': 3}
    assert set(both.loc[both['model_version'] == 'old', 'raw_over_pct']) == {'70.0'}


def test_lineage_names_the_model_and_the_calibration(data_dir):
    assert nightly.lineage(nightly.RECORDED_LIVE) == {'model_version': nightly.MODEL_VERSION,
                                                      'calibration_id': 'none', 'prediction_origin': 'recorded_live'}
    fitted = {'coefficients': {'a': 1.09, 'b': 0.08, 'c': -0.1, 'd': 0.05}, 'green_edge_pp': None,
              'superbet_through': '2026-10-25', 'fitted_on': '2026-10-26'}
    os.makedirs(os.path.dirname(models.CALIBRATION_FILE))
    with open(models.CALIBRATION_FILE, 'w') as f:
        json.dump(fitted, f)
    first = models.calibration_id()
    assert len(first) == 10 and nightly.lineage(nightly.RECORDED_LIVE)['calibration_id'] == first
    with open(models.CALIBRATION_FILE, 'w') as f:
        json.dump(fitted | {'fitted_on': '2026-10-27'}, f)   # refitted to the same numbers: the same calibration
    assert models.calibration_id() == first
    with open(models.CALIBRATION_FILE, 'w') as f:
        json.dump(fitted | {'superbet_through': '2026-10-26'}, f)
    assert models.calibration_id() != first
