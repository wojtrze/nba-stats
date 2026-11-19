"""Run with: python -m pytest dashboard

Audit package E: the reason log (reason_log.py) and the reason_lift metadata. Every player, game and number here
is SYNTHETIC (made up for the test): no real NBA result is used or implied."""
import json
import os

import pandas as pd
import pytest

import i18n
import reason_log
from decisions import NIE_OBSTAWIAJ, _decision
from reasons import LIFT, LIFT_SCHEMA, NO_LIFT, lift_definitions, lift_status, prop_reasons, validation_label

PLAYER, MATE = 3900001, 3900002          # synthetic ids
FETCHED = '2026-10-25T20:00:00Z'


def _logs():
    """Synthetic: PLAYER's 12 games (MATE misses games 4-6), with the columns offer_records reads."""
    pts = [20.0, 24, 18, 26, 30, 31, 28, 22, 27, 25, 19, 23]
    rows = [{'player_id_ESPN': PLAYER, 'player_display_name': 'Synthetic Player', 'game_id': g, 'PTS': p,
             'MIN': 34.0} for g, p in enumerate(pts)]
    rows += [{'player_id_ESPN': MATE, 'player_display_name': 'Synthetic Mate', 'game_id': g, 'PTS': 10.0,
              'MIN': 25.0} for g in range(12) if g not in {4, 5, 6}]
    logs = pd.DataFrame(rows).assign(team='nyk', season_id=2026, season_type='regular', OPP='BOS', type='home',
                                     starter=True)
    return logs.assign(Date=pd.Timestamp('2026-10-01') + pd.to_timedelta(logs['game_id'] * 2, unit='D'))


def _table():
    from metrics import absence_adjustments
    logs = _logs()
    games = logs[logs['player_id_ESPN'] == PLAYER]
    adj = float(absence_adjustments(logs, [PLAYER], [MATE], ['PTS']).loc[PLAYER, 'PTS'])
    avg = games['PTS'].mean()
    row = {'event_id': 1, 'player_id': PLAYER, 'name': 'Synthetic Player', 'team': 'nyk', 'opp': 'bos',
           'home': 'nyk', 'away': 'bos', 'bet_type': 'PTS', 'line': 24.5, 'side': 'Over', 'side odds': 1.9,
           'over_odds': 1.9, 'under_odds': 1.85, 'p win %': 51.0, 'break-even net %': 59.8, 'edge net pp': -8.8,
           'ev net 100': -14.7, 'cost profile': 'superbet_standard', 'market over %': 50.0, 'avg': avg,
           'adj avg': avg + adj, 'lineup adj': adj, 'pace factor': 1.0, 'matchup factor': 1.0, 'proj avg': avg + adj,
           'RotoWire': 'starter', 'is_home': True, 'start_time': '2026-10-25T23:30:00Z', 'red flag': '',
           'signal': ''}
    return pd.DataFrame([row, row | {'line': 26.5, 'side': 'Under', 'side odds': 1.8}])


def _lineups():
    return pd.DataFrame({'player_id_ESPN': [PLAYER, MATE], 'team': 'nyk', 'name': ['Synthetic Player', None],
                         'role': ['starter', 'may_not_play'], 'play_pct': [100, 0], 'lineup_status': 'confirmed',
                         'fetched_at': '2026-10-25T19:00:00Z'})


VERSION = {'schema': reason_log.SCHEMA_VERSION, 'code': 'synthetic', 'code_dirty': False, 'model': 'm1',
           'calibration': 'c1', 'reasons': reason_log.REASONS_VERSION, 'texts': 't1'}


def _records(origin=reason_log.RECORDED, version=VERSION, recorded=None):
    table, logs = _table(), _logs()
    decided = {1: _decision(NIE_OBSTAWIAJ, 'decision.reason.no_threshold')}
    return reason_log.offer_records(table, decided, logs, logs, _lineups(), FETCHED, FETCHED, version, origin,
                                    'superbet_standard', {'a': 1.0, 'b': 1.0, 'c': 0.0, 'd': 0.0}, {}, {},
                                    recorded=recorded)


def test_computing_records_writes_nothing_and_gives_plain_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    records = _records()
    assert os.listdir(tmp_path) == []                                     # computing never writes
    assert len(records) == 2 and json.loads(json.dumps(records)) == records
    r = records[0]
    assert r['snapshot_id'] == FETCHED and r['origin'] == 'recorded' and r['cost_profile'] == 'superbet_standard'
    assert r['offer'] | {} == r['offer'] and (r['offer']['stat'], r['offer']['line'], r['offer']['side'],
                                               r['offer']['odds']) == ('PTS', 24.5, 'Over', 1.9)
    assert r['decision']['game']['status'] == NIE_OBSTAWIAJ
    assert r['decision']['offer']['reason'] == 'decision.reason.no_threshold'
    assert r['data_times']['lineup_at'] == '2026-10-25T19:00:00Z' and r['data_times']['odds_at'] == FETCHED
    keys = [x['key'] for x in r['reasons']]
    assert 'reason.model' in keys and 'reason.teammates' in keys and None not in keys
    teammates = next(x for x in r['reasons'] if x['key'] == 'reason.teammates')
    assert teammates['kind'] == 'driver' and teammates['n'] == 3 and teammates['source'] == 'RotoWire · ESPN'
    assert all('text' not in x for x in r['reasons'])                    # data, not words


def test_writing_the_same_snapshot_again_adds_no_observations(tmp_path):
    directory, archive = str(tmp_path / 'log'), str(tmp_path / 'archive')
    assert reason_log.write(_records(), directory=directory, archive_dir=archive) == 2
    assert reason_log.write(_records(), directory=directory, archive_dir=archive) == 0
    assert len(reason_log.read(reason_log.log_path(FETCHED, directory))) == 2


def test_a_reconstruction_is_kept_beside_the_recorded_one_never_over_it(tmp_path):
    directory = str(tmp_path / 'log')
    reason_log.write(_records(), directory=directory, archive_dir=str(tmp_path / 'a'))
    saved = pd.DataFrame([{'decision': 'OBSTAW', 'model_pct': 58.0}] * 2)
    rebuilt = _records(reason_log.RECONSTRUCTED, recorded=saved)
    assert reason_log.write(rebuilt, directory=directory, archive_dir=str(tmp_path / 'a')) == 2
    other = _records(reason_log.COUNTERFACTUAL, version=VERSION | {'calibration': 'c2'})
    assert reason_log.write(other, directory=directory, archive_dir=str(tmp_path / 'a')) == 2
    every = reason_log.read(reason_log.log_path(FETCHED, directory))
    assert [r['origin'] for r in every] == ['recorded'] * 2 + ['reconstructed'] * 2 + ['counterfactual'] * 2
    assert every[:2] == _records()                                       # the recorded ones are untouched
    assert every[2]['recorded'] == {'decision': 'OBSTAW', 'model_pct': 58.0}   # what was shown then, kept beside


def test_a_rebuild_is_counterfactual_unless_priced_with_the_same_model_and_calibration():
    now = {'model': 'm1', 'calibration': 'c1'}
    assert reason_log.origin_for({'model_version': 'm1', 'calibration_id': 'c1'}, now) == reason_log.RECONSTRUCTED
    assert reason_log.origin_for({'model_version': 'm1', 'calibration_id': 'c0'}, now) == reason_log.COUNTERFACTUAL
    assert reason_log.origin_for({}, now) == reason_log.COUNTERFACTUAL
    with pytest.raises(ValueError):
        _records('replayed')


def test_the_calibration_is_archived_whole_once(tmp_path):
    arts = {'calibration': {'id': 'c1', 'content': {'coefficients': {'a': 1.1, 'b': 0.2}, 'green_edge_pp': None}},
            'mispricing_status': {'id': 's1', 'content': {'hypotheses': {'H2': {'status': 'untested'}}}},
            'reason_lift': {'id': 'none', 'content': None}}
    directory = str(tmp_path / 'archive')
    assert reason_log.archive(arts, directory) == 2 and reason_log.archive(arts, directory) == 0
    with open(os.path.join(directory, 'calibration', 'c1.json'), encoding='utf-8') as f:
        assert json.load(f) == arts['calibration']['content']


def test_only_the_snapshot_writes_the_log():
    """Pages and the functions that compute or render reasons never write it (Streamlit reruns would repeat it)."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    writers = []
    for folder in ('dashboard', 'dashboard_v2', os.path.join('dashboard_v2', 'views'),
                   os.path.join('dashboard_v2', 'core'), os.path.join('dashboard', 'views'), '.'):
        for name in os.listdir(os.path.join(root, folder)):
            if name.endswith('.py') and not name.startswith('test_'):
                with open(os.path.join(root, folder, name), encoding='utf-8') as f:
                    if 'reason_log.write(' in f.read():
                        writers.append(name)
    assert writers == ['daily_snapshot.py']


@pytest.mark.parametrize('lang', ['en', 'pl'])
def test_every_reason_has_the_same_key_in_both_languages(lang):
    from test_reasons import _absence_bet, B, C, D, E
    bet, games, _ = _absence_bet([B, C, D, E])
    reasons = prop_reasons(bet, games, games.iloc[0:0], lang)
    other = prop_reasons(bet, games, games.iloc[0:0], 'pl' if lang == 'en' else 'en')
    assert [r['key'] for r in reasons] == [r['key'] for r in other]
    assert all(r['key'] in i18n.TEXTS or r['key'].startswith('mispricing.h') for r in reasons)


# --- reason_lift: no direction from a test whose metadata doesn't match the current code ---

def _lift_file(tmp_path, meta):
    path = tmp_path / 'reason_lift.json'
    saved = {'features': {'hits_l10': {'status': LIFT, 'over_sign': 1}, 'rest': {'status': NO_LIFT}}}
    if meta is not None:
        saved['meta'] = meta
    path.write_text(json.dumps(saved), encoding='utf-8')
    return str(path)


def _meta(**kw):
    from models import MODEL_VERSION
    defs = lift_definitions()
    return {'schema_version': LIFT_SCHEMA, 'model_version': MODEL_VERSION,
            'features': {f: {'definition': d} for f, d in defs.items()}} | kw


def test_a_lift_without_matching_metadata_is_shown_unverified_and_gives_no_direction(tmp_path):
    from models import MODEL_VERSION
    assert lift_status(_lift_file(tmp_path, None))['hits_l10']['problems'] == ['meta', 'definition']
    assert lift_status(_lift_file(tmp_path, _meta(model_version='old')))['hits_l10']['problems'] == ['model']
    assert lift_status(_lift_file(tmp_path, _meta(schema_version=0)))['hits_l10']['problems'] == ['schema']
    changed = _meta()
    changed['features']['hits_l10'] = {'definition': 'other'}
    assert lift_status(_lift_file(tmp_path, changed))['hits_l10']['problems'] == ['definition']
    assert lift_status(_lift_file(tmp_path, _meta()))['hits_l10'] == {'status': LIFT, 'over_sign': 1,
                                                                       'verified': True, 'problems': []}
    assert MODEL_VERSION


@pytest.mark.parametrize('lang', ['en', 'pl'])
def test_only_a_verified_lift_gives_the_history_a_direction(tmp_path, lang):
    from test_reasons import _bet, _games
    bet, games = _bet(**{'market over %': 50.0}), _games([25.0] * 12)
    history = lambda meta: next(r for r in prop_reasons(bet, games, games.iloc[0:0], lang,
                                                        validation=lift_status(_lift_file(tmp_path, meta)))
                                if r['key'] == 'reason.history_last')
    unverified, verified = history(None), history(_meta())
    assert unverified['supports'] is None and unverified['verified'] is False
    assert verified['supports'] is True and verified['verified'] is True
    assert validation_label(unverified, lang).endswith(i18n.t('panel.validation.unverified', lang))
    assert validation_label(verified, lang) == i18n.t('panel.validation.lift', lang)


def test_reason_lift_saves_what_its_verdicts_rest_on():
    from backtest.reason_lift import FEATURES, NOT_TESTABLE, metadata
    from models import MODEL_VERSION
    results = {'2022': pd.DataFrame([{'feature': 'hits_l10', 'ranges': {'fit': ['2022-11-09', '2023-01-31'],
                                                                        'test': ['2023-02-01', '2023-05-08']}}])}
    meta = metadata(results, created_at='2026-11-11T00:00:00Z')
    assert meta['schema_version'] == LIFT_SCHEMA and meta['model_version'] == MODEL_VERSION
    assert meta['ranges']['2022'] == {'fit': ['2022-11-09', '2023-01-31'], 'test': ['2023-02-01', '2023-05-08']}
    assert set(meta['features']) == set(FEATURES) | set(NOT_TESTABLE)
    assert meta['features']['hits_l10']['definition'] == lift_definitions()['hits_l10']
    assert meta['created_at'] == '2026-11-11T00:00:00Z' and 'commit' in meta['code_version']
    assert lift_status.__doc__ and 'verified' in lift_status.__doc__
