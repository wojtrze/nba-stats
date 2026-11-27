"""The snapshot datasets (espn_scraper.storage): one Parquet file per UTC day of fetched_at."""
import os

import pandas as pd
import pytest

from espn_scraper.storage import (REPLAY, append_snapshot, export_csv, latest_fetch, latest_snapshot, load_snapshot,
                                  snapshot_dir, snapshot_exists, snapshot_signature, write_replay)

NAME = 'superbet_props'


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    yield tmp_path


def _rows(fetched_at, n=2, **extra):
    return pd.DataFrame({'fetched_at': [fetched_at] * n, 'name': [f'P{i}' for i in range(n)],
                         'event_id': list(range(1, n + 1)), 'line': [20.5] * n, **extra})


def _files(name=NAME):
    return sorted(os.listdir(snapshot_dir(2026, name)))


def test_nothing_saved_reads_empty():
    assert not snapshot_exists(NAME)
    assert load_snapshot(NAME).empty and latest_snapshot(NAME).empty and latest_fetch(NAME) is None
    assert list(load_snapshot(NAME, columns=['fetched_at']).columns) == ['fetched_at']
    assert snapshot_signature(NAME) == (0, 0.0)


def test_rows_go_to_the_file_of_their_utc_day_and_read_back_in_order():
    append_snapshot(NAME, _rows('2026-11-26T23:59:59Z'))
    append_snapshot(NAME, _rows('2026-11-27T00:00:00Z', 3))       # just after midnight UTC: the next day's file
    append_snapshot(NAME, _rows('2026-11-27T16:00:00Z', 1))
    assert _files() == ['2026-11-26.parquet', '2026-11-27.parquet']
    saved = load_snapshot(NAME)
    assert saved['fetched_at'].tolist() == ['2026-11-26T23:59:59Z'] * 2 + ['2026-11-27T00:00:00Z'] * 3 + \
        ['2026-11-27T16:00:00Z']
    assert saved['event_id'].tolist() == [1, 2, 1, 2, 3, 1] and saved['event_id'].dtype == 'int64'
    assert latest_fetch(NAME) == '2026-11-27T16:00:00Z'
    assert latest_snapshot(NAME)['name'].tolist() == ['P0']


def test_one_append_spanning_two_days_is_split():
    both = pd.concat([_rows('2026-11-26T23:00:00Z'), _rows('2026-11-27T01:00:00Z')], ignore_index=True)
    assert append_snapshot(NAME, both) == 4
    assert _files() == ['2026-11-26.parquet', '2026-11-27.parquet']
    pd.testing.assert_frame_equal(load_snapshot(NAME), both)


def test_an_earlier_day_is_never_rewritten():
    append_snapshot(NAME, _rows('2026-11-26T10:00:00Z'))
    path = os.path.join(snapshot_dir(2026, NAME), '2026-11-26.parquet')
    before = open(path, 'rb').read()
    append_snapshot(NAME, _rows('2026-11-27T10:00:00Z', signal=['x', None]))
    assert open(path, 'rb').read() == before


def test_a_column_added_later_is_empty_in_older_days_and_comes_last():
    append_snapshot(NAME, _rows('2026-11-26T10:00:00Z'))
    append_snapshot(NAME, _rows('2026-11-27T10:00:00Z', decision=['NIE_OBSTAWIAJ', None]))
    saved = load_snapshot(NAME)
    assert list(saved.columns) == ['fetched_at', 'name', 'event_id', 'line', 'decision']
    assert saved['decision'].isna().tolist() == [True, True, False, True]


def test_new_rows_take_the_saved_types():
    append_snapshot(NAME, _rows('2026-11-26T10:00:00Z'))
    # ids that came as floats (a gap elsewhere in the fetch) and a new day's file: still int, no drift
    append_snapshot(NAME, _rows('2026-11-27T10:00:00Z').assign(event_id=[1.0, 2.0]))
    assert load_snapshot(NAME)['event_id'].dtype == 'int64'
    # a value that doesn't fit the saved type is kept, and the column read as what holds both
    append_snapshot(NAME, _rows('2026-11-28T10:00:00Z').assign(event_id=[1.5, None]))
    ids = load_snapshot(NAME)['event_id']
    assert ids.dtype == 'float64' and ids.tolist()[:4] == [1, 2, 1, 2] and ids.iloc[4] == 1.5


def test_number_in_one_day_text_in_another_reads_as_text():
    append_snapshot(NAME, _rows('2026-11-26T10:00:00Z', red_flag=[1.0, None]))
    append_snapshot(NAME, _rows('2026-11-27T10:00:00Z', red_flag=['late scratch', None]))
    flags = load_snapshot(NAME)['red_flag']
    assert flags.iloc[2] == 'late scratch' and pd.isna(flags.iloc[1])


def test_empty_text_is_no_value_as_in_the_csv():
    append_snapshot(NAME, _rows('2026-11-26T10:00:00Z', signal=['', '🟢']))
    signal = load_snapshot(NAME)['signal']
    assert pd.isna(signal.iloc[0]) and signal.iloc[1] == '🟢'


def test_columns_and_since_read_less():
    for day in ('2026-11-24', '2026-11-25', '2026-11-26', '2026-11-27'):
        append_snapshot(NAME, _rows(f'{day}T12:00:00Z'))
    some = load_snapshot(NAME, columns=['event_id', 'fetched_at', 'missing'])
    assert list(some.columns) == ['event_id', 'fetched_at', 'missing'] and len(some) == 8
    # since a day: from one day earlier (a night in ET starts on the UTC day before)
    assert sorted(load_snapshot(NAME, since='2026-11-26')['fetched_at'].str[:10].unique()) == ['2026-11-25',
                                                                                               '2026-11-26',
                                                                                               '2026-11-27']
    assert len(load_snapshot(NAME, since=pd.Timestamp('2026-11-27 20:00', tz='UTC'))) == 4


def test_names_shown_first_last_unless_asked_as_saved():
    append_snapshot(NAME, pd.DataFrame({'fetched_at': ['2026-11-27T10:00:00Z'] * 2,
                                        'name': ['White, Coby', 'Reed Sheppard']}))
    assert load_snapshot(NAME)['name'].tolist() == ['Coby White', 'Reed Sheppard']
    assert load_snapshot(NAME, display_names=False)['name'].tolist() == ['White, Coby', 'Reed Sheppard']
    assert latest_snapshot(NAME)['name'].tolist() == ['Coby White', 'Reed Sheppard']


def test_the_signature_changes_with_every_save():
    append_snapshot(NAME, _rows('2026-11-27T10:00:00Z'))
    first = snapshot_signature(NAME)
    os.utime(os.path.join(snapshot_dir(2026, NAME), '2026-11-27.parquet'), (1, 1))
    append_snapshot(NAME, _rows('2026-11-27T11:00:00Z'))
    assert snapshot_signature(NAME) != first and snapshot_signature(NAME)[0] == 1


def test_a_replay_version_is_replaced_and_the_others_kept():
    old = _rows('2026-11-26T10:00:00Z').assign(model_version='a', model_pct=[50.0, 51.0])
    write_replay('a', old)
    write_replay('b', pd.concat([_rows('2026-11-25T10:00:00Z'), _rows('2026-11-26T10:00:00Z')]).assign(
        model_version='b', model_pct=60.0))
    folder = os.path.join(snapshot_dir(2026, REPLAY), 'b')
    day = open(os.path.join(folder, '2026-11-26.parquet'), 'rb').read()
    # repriced: the 25th's lines are gone, the 26th's are the same (same bytes, so git sees no change)
    assert write_replay('b', _rows('2026-11-26T10:00:00Z').assign(model_version='b', model_pct=60.0)) == 2
    assert sorted(os.listdir(folder)) == ['2026-11-26.parquet']
    assert open(os.path.join(folder, '2026-11-26.parquet'), 'rb').read() == day
    both = load_snapshot(REPLAY)
    assert both['model_version'].tolist() == ['a', 'a', 'b', 'b'] and both['model_pct'].tolist() == [50, 51, 60, 60]


def test_export_writes_one_csv():
    append_snapshot(NAME, _rows('2026-11-26T10:00:00Z'))
    append_snapshot(NAME, _rows('2026-11-27T10:00:00Z'))
    assert export_csv(NAME, 'out.csv') == 4
    assert pd.read_csv('out.csv')['fetched_at'].str[:10].tolist() == ['2026-11-26'] * 2 + ['2026-11-27'] * 2
