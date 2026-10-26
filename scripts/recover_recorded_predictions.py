"""Recover what each Superbet fetch showed before `daily_snapshot.py --reprice` rewrote it in place (it no longer
does: repricing now goes to superbet_props_replay.csv).

    python scripts/recover_recorded_predictions.py

Every committed version of data/<season>/superbet_props.csv is read, oldest first, and each saved line
(fetched_at, event, player, stat) keeps the model columns of the first version that had them: the closest thing
to the recorded live prediction that still exists. A line whose fetch was first committed without the model's
numbers (saved before picks were, e.g. Oct 20) only ever got them from a reprice: historical_replay, not
recorded_live. Writes superbet_props_recorded_legacy.csv next to it, with recovered_from (the commit) and
prediction_origin. Nothing else is touched.
"""
import io
import os
import subprocess
import sys

import pandas as pd

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dashboard'))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from espn_scraper import CURRENT_SEASON  # noqa: E402
from espn_scraper.storage import snapshot_file  # noqa: E402
from nightly import HISTORICAL_REPLAY, MODEL_COLUMNS, RECORDED_LIVE  # noqa: E402

KEY = ['fetched_at', 'event_id', 'name_ESPN', 'bet_type']


def committed_versions(path: str):
    """(commit, DataFrame) of every commit that changed path, oldest first."""
    posix = path.replace(os.sep, '/')
    commits = subprocess.run(['git', 'log', '--reverse', '--format=%h', '--', posix], capture_output=True,
                             text=True, check=True).stdout.split()
    for commit in commits:
        text = subprocess.run(['git', 'show', f'{commit}:{posix}'], capture_output=True, check=True).stdout
        yield commit, pd.read_csv(io.BytesIO(text))


def recover(path: str) -> pd.DataFrame:
    found = []
    first_seen, recovered = set(), set()
    for commit, version in committed_versions(path):
        keys = list(zip(*(version[c] for c in KEY)))
        has_pick = version['pick'].notna() if 'pick' in version else pd.Series(False, index=version.index)
        new = pd.Series([k not in recovered for k in keys], index=version.index) & has_pick
        live = pd.Series([k not in first_seen for k in keys], index=version.index)   # priced by the fetch itself
        first_seen.update(keys)
        rows = version[new]
        recovered.update(k for k, n in zip(keys, new) if n)
        cols = [c for c in KEY + ['line', 'over_odds', 'under_odds', 'start_time', *MODEL_COLUMNS] if c in rows]
        found.append(rows[cols].assign(recovered_from=commit,
                                       prediction_origin=live[new].map({True: RECORDED_LIVE, False: HISTORICAL_REPLAY})))
    return pd.concat(found, ignore_index=True) if found else pd.DataFrame(columns=KEY)


if __name__ == '__main__':
    source = snapshot_file(CURRENT_SEASON, 'superbet_props')
    out = recover(source)
    target = snapshot_file(CURRENT_SEASON, 'superbet_props_recorded_legacy')
    out.to_csv(target, index=False)
    per_commit = out.groupby(['recovered_from', 'prediction_origin'], sort=False).size()
    print(f"{target}: {len(out)} lines ({', '.join(f'{c} {o}: {n}' for (c, o), n in per_commit.items())})")
