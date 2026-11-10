import os
import threading
from datetime import datetime, timedelta, timezone

import pandas as pd

from core import fetch_worker

UTC = timezone.utc
NOW = datetime(2026, 11, 6, 8, tzinfo=UTC)


def test_a_loop_is_stuck_only_after_a_slots_limit_and_the_margin():
    limit = 6
    fresh = {'beat': NOW - timedelta(minutes=limit) - fetch_worker.STALE_MARGIN}
    assert fetch_worker.stuck_since(fresh, NOW, limit) is None
    old = {'beat': NOW - timedelta(minutes=limit) - fetch_worker.STALE_MARGIN - timedelta(seconds=1)}
    assert fetch_worker.stuck_since(old, NOW, limit) == old['beat']
    assert fetch_worker.stuck_since({}, NOW, limit) is None


def test_the_supervisor_replaces_a_stuck_loop_and_logs_it(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs('data')
    stuck = threading.Event()
    old_thread = threading.Thread(target=stuck.wait, args=(5,), daemon=True)
    old_thread.start()
    old_stop = threading.Event()
    w = {'thread': old_thread, 'stop': old_stop, 'restarts': 0,
         'status': {'beat': NOW - timedelta(hours=2), 'state': 'fetching (hourly)'}}
    launched = []
    monkeypatch.setattr(fetch_worker, '_launch', lambda w: launched.append(True))
    try:
        assert fetch_worker.check(w, now=lambda: NOW)
        assert old_stop.is_set() and launched == [True] and w['restarts'] == 1
        log = pd.read_csv(os.path.join('data', 'run_log.csv'))
        assert log['command'].tolist() == ['scheduled restart']
        assert 'stuck since 06:00 UTC' in log['summary'].iloc[0]
        assert os.path.exists(os.path.join('data', 'fetch_hangs.log'))
        w['status']['beat'] = NOW                                       # a healthy loop is left alone
        assert not fetch_worker.check(w, now=lambda: NOW)
    finally:
        stuck.set()
