"""One-off (27.11.2026): move the growing snapshot CSVs to day-partitioned Parquet (espn_scraper.storage).

    python -m scripts.migrate_snapshots_to_parquet            # write the folders and check them; CSVs kept
    python -m scripts.migrate_snapshots_to_parquet --delete   # the same, then remove each CSV that checked equal

superbet_props.csv had reached 80 MB (GitHub refuses files over 100 MB) and was read and rewritten whole on every
fetch. Each CSV of storage.SNAPSHOTS becomes data/<season>/<name>/<UTC day>.parquet, the replay
<name>/<model_version>/<day>.parquet. A dataset is checked before its CSV may go: read back with load_snapshot it
must equal the CSV as read_csv gave it (rows, order, columns, types, values). Stop the fetch worker (Data center)
and close the dashboards first; a dataset whose folder already exists is left alone.
"""
import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from espn_scraper import CURRENT_SEASON                                          # noqa: E402
from espn_scraper.storage import (REPLAY, SNAPSHOTS, append_snapshot, load_snapshot, snapshot_dir,  # noqa: E402
                                  snapshot_file, write_replay)
from safe_io import locked                                                       # noqa: E402


def _expected(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """The CSV's rows in the order the folder gives them back (the replay: version folders in name order)."""
    if name != REPLAY:
        return df
    order = sorted(df['model_version'].astype(str).unique())
    rank = df['model_version'].astype(str).map({v: i for i, v in enumerate(order)})
    return df.iloc[rank.argsort(kind='stable')].reset_index(drop=True)


def migrate(name: str, season: int = CURRENT_SEASON, delete: bool = False) -> str:
    csv = snapshot_file(season, name)
    if not os.path.exists(csv):
        return f"{name}: no CSV"
    if os.path.exists(snapshot_dir(season, name)):
        return f"{name}: folder exists, left alone"
    with locked(csv):                          # an old writer still running can't append meanwhile
        df = pd.read_csv(csv, low_memory=False)
        if name == REPLAY:
            if df['model_version'].isna().any():
                raise ValueError(f"{csv}: rows without model_version")
            for version, rows in df.groupby('model_version', sort=False):
                write_replay(str(version), rows, season)
        else:
            append_snapshot(name, df, season)
        back = load_snapshot(name, season, display_names=False)
        pd.testing.assert_frame_equal(back, _expected(df, name))
        mb = os.path.getsize(csv) / 1e6
        size = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(snapshot_dir(season, name))
                   for f in fs) / 1e6
        if delete:
            os.remove(csv)
    return f"{name}: {len(df)} rows, {mb:.1f} MB CSV -> {size:.1f} MB Parquet, equal" + (", CSV removed" * delete)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--delete', action='store_true', help="remove each CSV once its folder checked equal")
    parser.add_argument('--season', type=int, default=CURRENT_SEASON)
    args = parser.parse_args()
    for dataset in (*SNAPSHOTS, REPLAY):
        print(migrate(dataset, args.season, args.delete), flush=True)
