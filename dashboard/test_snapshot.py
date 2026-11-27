"""Run with: python -m pytest dashboard"""
import json
import os

import pandas as pd
import pytest

import daily_snapshot
import models
import name_resolver
import nightly
from espn_scraper.storage import append_snapshot, load_snapshot, snapshot_dir, write_replay

FOLDER = os.path.join('data', '2026', 'superbet_props')


def _record_bytes():
    """Every byte of the saved record (superbet_props), file by file."""
    return {f: open(os.path.join(FOLDER, f), 'rb').read() for f in sorted(os.listdir(FOLDER))}


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
    append_snapshot('superbet_props', pd.DataFrame({'fetched_at': ['2026-10-20T10:00:00Z'] * 2, 'name': ['A', 'B'],
                                                    'player_id_ESPN': [4397475, None]}))
    before = _record_bytes()
    new = pd.DataFrame([{'name': 'C', 'player_id_ESPN': 7, 'signal': 'x'}])
    assert daily_snapshot._append('superbet_props', new, '2026-10-21T10:00:00Z') == 1
    after = _record_bytes()
    assert after['2026-10-20.parquet'] == before['2026-10-20.parquet']      # an earlier day is never rewritten
    saved = load_snapshot('superbet_props')
    assert list(saved.columns) == ['fetched_at', 'name', 'player_id_ESPN', 'signal']
    assert saved['name'].tolist() == ['A', 'B', 'C'] and saved['player_id_ESPN'].tolist()[::2] == [4397475, 7]
    assert pd.isna(saved.loc[1, 'player_id_ESPN']) and saved['signal'].isna().tolist() == [True, True, False]


def test_reprice_writes_a_replay_and_leaves_the_record_alone(data_dir, monkeypatch):
    saved = pd.DataFrame([_line('2026-10-21T10:00:00Z', 4397475.0, pick='Under', model_pct=51.0, signal='🔴'),
                          _line('2026-10-21T10:00:00Z', None, name='Nobody'),
                          _line('2026-10-21T20:00:00Z', 4397475.0, pick='Under', model_pct=52.0)])
    append_snapshot('superbet_props', saved)
    record = _record_bytes()
    odds = pd.DataFrame([{'fetched_at': f, 'event_id': 1, 'market': 'ML'} for f in saved['fetched_at'].unique()])
    append_snapshot('superbet_game_odds', odds)
    append_snapshot('rotowire_lineups', pd.DataFrame([{'fetched_at': '2026-10-21T09:00:00Z', 'game_date': '2026-10-21',
                                                       'team': 'bos', 'name': 'X'}]))

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
                             'market_over_pct': 49.2, 'cost_profile': 'superbet_standard', 'eval_side': 'Over',
                             'ev_net_100': -4.0}, index=rows.index)

    monkeypatch.setattr(daily_snapshot, 'load_player_gamelogs', lambda seasons: pd.DataFrame())
    monkeypatch.setattr(daily_snapshot, 'load_games', lambda seasons: pd.DataFrame())
    monkeypatch.setattr(models, 'prepare_logs', lambda logs: logs)
    monkeypatch.setattr(name_resolver, 'NameResolver', Resolver)
    monkeypatch.setattr(nightly, 'recompute_props', recompute)

    assert daily_snapshot.reprice_snapshots() == 3
    assert calls == [('2026-10-21T10:00:00Z', 1, 1, '2026-10-21'), ('2026-10-21T20:00:00Z', 1, 1, '2026-10-21')]
    assert _record_bytes() == record   # what each fetch showed is never priced again in place
    out = load_snapshot('superbet_props_replay', display_names=False)
    assert out['player_id_ESPN'].tolist()[::2] == [4397475, 4397475] and pd.isna(out.loc[1, 'player_id_ESPN'])
    assert out['pick'].tolist() == ['Over'] * 3 and out['signal'].tolist() == ['🟢'] * 3
    assert out['raw_over_pct'].tolist() == [63.5] * 3 and out['market_over_pct'].tolist() == [49.2] * 3
    assert out['fetched_at'].tolist() == saved['fetched_at'].tolist() and out['name'].tolist() == ['A', 'Nobody', 'A']
    assert out['line'].tolist() == [20.5] * 3 and out['under_odds'].tolist() == [1.85] * 3
    assert out['prediction_origin'].tolist() == ['historical_replay'] * 3
    assert out['model_version'].tolist() == [nightly.MODEL_VERSION] * 3
    assert out['calibration_id'].tolist() == ['none'] * 3   # no calibration file in the test folder

    # another model's replay is kept next to this one's, which a second reprice replaces
    write_replay('old', out.assign(model_version='old', raw_over_pct=70.0))
    assert daily_snapshot.reprice_snapshots() == 3
    both = load_snapshot('superbet_props_replay', display_names=False)
    assert both.groupby('model_version').size().to_dict() == {nightly.MODEL_VERSION: 3, 'old': 3}
    assert set(both.loc[both['model_version'] == 'old', 'raw_over_pct']) == {70.0}
    assert sorted(os.listdir(snapshot_dir(2026, 'superbet_props_replay'))) == sorted([nightly.MODEL_VERSION, 'old'])


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


# --- audit package E: the snapshot writes its reason log once (synthetic records, no real result) ---

def test_a_saved_fetch_logs_its_reasons_once(data_dir, monkeypatch):
    import reason_log
    from test_reason_log import VERSION, _records

    def priced(props, game_odds, lineups, evaluation=None):
        # what log_reasons reads; offer_records is replaced below, so these are placeholders
        evaluation.update({k: None for k in ('decisions', 'scope', 'every_game', 'lineups', 'evaluated_at',
                                             'version', 'profile', 'coef', 'lifts', 'statuses')})
        evaluation.update(table='t', arts={'calibration': {'id': 'c1', 'content': {'coefficients': {'a': 1.0}}}})
        return props.assign(player_id_ESPN=1), game_odds

    monkeypatch.setattr(daily_snapshot, 'add_model_columns', priced)
    records = _records()
    monkeypatch.setattr(reason_log, 'offer_records', lambda *a, **kw: records)
    offers = {'props': [{'name': 'A', 'name_ESPN': 'A', 'home': 'bos', 'away': 'ny', 'bet_type': 'PTS',
                         'line': 20.5, 'event_id': 1, 'start_time': '2026-10-21T23:30:00Z', 'over_under': side,
                         'odds': 1.9} for side in ('Over', 'Under')], 'game_odds': []}
    daily_snapshot.save_superbet(offers, pd.DataFrame(), '2026-10-25T20:00:00Z', reasons='wait')
    daily_snapshot.save_superbet(offers, pd.DataFrame(), '2026-10-25T20:00:00Z', reasons='wait')
    log = reason_log.read(reason_log.log_path('2026-10-25T20:00:00Z'))
    assert len(log) == 2 and {r['origin'] for r in log} == {'recorded'} and log[0]['versions'] == VERSION
    assert os.path.exists(os.path.join('data', 'archive', 'calibration', 'c1.json'))
    # 'off' saves the snapshot without a log
    daily_snapshot.save_superbet(offers, pd.DataFrame(), '2026-10-26T20:00:00Z', reasons='off')
    assert not os.path.exists(reason_log.log_path('2026-10-26T20:00:00Z'))
