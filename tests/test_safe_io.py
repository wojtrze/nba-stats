"""Writing the data files from several processes at once. Run with: python -m pytest tests"""
import os
import subprocess
import sys
import textwrap
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

import safe_io
from safe_io import append_csv, atomic_to_csv, locked

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _start(code: str, cwd) -> subprocess.Popen:
    """A Python process running `code` in cwd, with the repository (and dashboard/) importable."""
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([ROOT, os.path.join(ROOT, 'dashboard')]))
    return subprocess.Popen([sys.executable, '-c', textwrap.dedent(code)], cwd=cwd, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def _wait(procs):
    for p in procs:
        out, err = p.communicate(timeout=120)
        assert p.returncode == 0, err


def test_appends_from_several_processes_all_land(tmp_path):
    path = tmp_path / 'log.csv'
    code = """
        import sys
        import pandas as pd
        from safe_io import append_csv
        writer = int(sys.argv[1]) if len(sys.argv) > 1 else {w}
        for i in range(40):
            append_csv(pd.DataFrame([{{'writer': writer, 'i': i, 'text': 'x' * 200}}]), 'log.csv', ['writer', 'i', 'text'])
    """
    _wait([_start(code.format(w=w), tmp_path) for w in range(4)])
    saved = pd.read_csv(path)
    assert len(saved) == 160 and not saved.duplicated(['writer', 'i']).any()     # nothing lost, nothing torn
    assert sorted(saved.groupby('writer')['i'].apply(list).map(sorted).map(tuple).unique()) == [tuple(range(40))]


def test_append_keeps_the_saved_bytes_and_line_endings(tmp_path):
    path = tmp_path / 'a.csv'
    path.write_bytes(b"id,name,extra\r\n007,A,\r\n8,B,x\r\n")
    assert append_csv(pd.DataFrame([{'name': 'C', 'id': 9, 'other': 1}]), str(path)) == 1
    assert path.read_bytes() == b"id,name,extra\r\n007,A,\r\n8,B,x\r\n9,C,\r\n"   # file's order, '007' kept
    assert append_csv(pd.DataFrame(), str(path)) == 0
    new = tmp_path / 'new.csv'
    append_csv(pd.DataFrame([{'b': 2, 'a': 1}]), str(new), ['a', 'b'])
    assert pd.read_csv(new).columns.tolist() == ['a', 'b']


def test_an_interrupted_write_leaves_the_old_file(tmp_path, monkeypatch):
    path = tmp_path / 'games.csv'
    path.write_text("game_id\n1\n2\n")

    def broken(self, f, **kw):
        f.write("game_id\n1\n")
        raise KeyboardInterrupt
    monkeypatch.setattr(pd.DataFrame, 'to_csv', broken)
    with pytest.raises(KeyboardInterrupt):
        atomic_to_csv(pd.DataFrame({'game_id': [1]}), str(path))
    assert path.read_text() == "game_id\n1\n2\n"
    assert os.listdir(tmp_path) == ['games.csv']                                     # no temporary file left


def test_lock_is_exclusive_reentrant_and_breaks_when_stale(tmp_path, monkeypatch):
    path = str(tmp_path / 'f.csv')
    holder = _start(f"""
        import time
        from safe_io import locked
        with locked({path!r}):
            print('held', flush=True)
            time.sleep(3)
    """, tmp_path)
    assert holder.stdout.readline().strip() == 'held'
    with pytest.raises(TimeoutError):
        with locked(path, timeout=0.3):
            pass
    _wait([holder])
    with locked(path):
        with locked(path):                        # the same thread may nest it
            assert os.path.exists(path + '.lock')
    assert not os.path.exists(path + '.lock')
    with open(path + '.lock', 'w') as f:          # left behind by a writer that crashed
        f.write('123\n')
    old = time.time() - safe_io.STALE_SECONDS - 10
    os.utime(path + '.lock', (old, old))
    with locked(path, timeout=1):
        pass


def test_superbet_cooldown_is_shared_and_claimed_once(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import daily_snapshot
    assert daily_snapshot.superbet_wait() is None
    code = """
        from daily_snapshot import claim_superbet
        print('claimed' if claim_superbet() is None else 'wait')
    """
    procs = [_start(code, tmp_path) for _ in range(4)]
    answers = [p.communicate(timeout=120)[0].strip() for p in procs]
    assert sorted(answers) == ['claimed', 'wait', 'wait', 'wait']                     # one process goes ahead
    wait = daily_snapshot.superbet_wait()
    assert wait is not None and wait <= daily_snapshot.SUPERBET_COOLDOWN
    assert daily_snapshot.claim_superbet() is not None
    later = datetime.now(timezone.utc) + daily_snapshot.SUPERBET_COOLDOWN + timedelta(seconds=1)
    assert daily_snapshot.superbet_wait(later) is None


def test_two_dashboards_save_one_lineup_change_once(tmp_path):
    os.makedirs(tmp_path / 'data' / '2026')
    code = """
        import pandas as pd
        from daily_snapshot import save_lineups_if_changed
        row = {{'game_date': '2026-10-27', 'tip_et': '7:30 PM ET', 'away': 'ny', 'home': 'bos', 'team': 'bos',
               'side': 'home', 'lineup_status': 'expected', 'role': 'may_not_play', 'pos': 'G', 'name': 'A Player',
               'rotowire_id': 1, 'play_pct': {pct}, 'injury': 'Ques'}}
        print(save_lineups_if_changed(pd.DataFrame([row]), '{at}') != '')
    """
    _wait([_start(code.format(pct=50, at='2026-10-27T10:00:00Z'), tmp_path)])
    procs = [_start(code.format(pct=0, at=f'2026-10-27T12:00:0{i}Z'), tmp_path) for i in range(3)]
    saved_by = [p.communicate(timeout=120)[0].strip() for p in procs]
    assert saved_by.count('True') == 1                                              # the change, saved once
    saved = pd.read_csv(tmp_path / 'data' / '2026' / 'rotowire_lineups.csv')
    assert saved['fetched_at'].nunique() == 2 and saved['play_pct'].tolist() == [50, 0]
