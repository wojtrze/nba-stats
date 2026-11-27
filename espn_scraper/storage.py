import os
import shutil
from typing import Dict, Iterable, List, Optional, Set, Tuple

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from . import CURRENT_SEASON, data_dir
from safe_io import append_csv, atomic_to_csv, atomic_write, atomic_write_text, locked

from .boxscore import GAME_COLUMNS, PLAYER_COLUMNS


def games_file(season: int) -> str:
    return os.path.join(data_dir(season), "games.csv")


def players_file(season: int) -> str:
    return os.path.join(data_dir(season), "player_gamelogs.csv")


def snapshot_file(season: int, name: str) -> str:
    """A CSV data file of the season (my_bets, superbet_props_components, ...). The growing snapshots (SNAPSHOTS,
    REPLAY) are folders of Parquet files instead: load_snapshot / append_snapshot. Their CSV path is kept for the
    migration and the scripts that read old committed versions from git."""
    return os.path.join(data_dir(season), f"{name}.csv")


def _display_names(df: pd.DataFrame) -> pd.DataFrame:
    """Player names as people write them (name_resolver.display_name: Superbet's "Last, First" -> "First Last");
    keys use name_ESPN, which doesn't change."""
    if 'name' in df.columns and not pd.api.types.is_numeric_dtype(df['name']):
        from name_resolver import display_name
        names = df['name'].astype(object)
        has_comma = names.str.contains(',', na=False, regex=False)
        if has_comma.any():
            df.loc[has_comma, 'name'] = names[has_comma].map(display_name)
    return df


def read_snapshot(path: str) -> pd.DataFrame:
    """An old snapshot CSV read whole (the migration, and committed versions read from git). Columns added later
    are empty in older rows and text in newer ones; read in chunks, pandas would guess their type per chunk and
    warn (DtypeWarning). Names as people write them (_display_names)."""
    return _display_names(pd.read_csv(path, low_memory=False))


# --- the growing snapshots: one Parquet file per UTC day of fetched_at ---
# Each fetch appended its rows to one CSV that was read and rewritten whole every time; by 27.11 superbet_props.csv
# was 80 MB (GitHub refuses files over 100 MB) and took 3 s to read. Now a dataset is a folder
# data/<season>/<name>/<YYYY-MM-DD>.parquet: a fetch rewrites only its day's small file, days already past never
# change (git stores each once), and a reader loads only the columns and days it needs. The day is the UTC date of
# fetched_at, a storage unit only: a betting night (nightly.et_night) can span two of them.
# The replay (daily_snapshot.reprice_snapshots) has one folder per model version: <name>/<model_version>/<day>.
# Read back, a dataset equals what the CSV gave (scripts/migrate_snapshots_to_parquet.py checks it): the same
# columns in the same order (a column added later is empty in older days), the same types, empty text as NaN.

SNAPSHOTS = ('superbet_props', 'superbet_game_odds', 'superbet_prop_quotes', 'superbet_game_quotes',
             'superbet_event_fetches', 'rotowire_lineups')
REPLAY = 'superbet_props_replay'
_COMPRESSION = 'zstd'
_ARROW_ERRORS = (pa.ArrowInvalid, pa.ArrowTypeError, pa.ArrowNotImplementedError)


def snapshot_dir(season: int, name: str) -> str:
    return os.path.join(data_dir(season), name)


def _day(fetched_at: pd.Series) -> pd.Series:
    """'YYYY-MM-DD' (UTC) of fetched_at values ('2026-11-27T16:00:00Z')."""
    return fetched_at.astype(str).str[:10]


def _files(name: str, season: int, since: Optional[str] = None) -> List[str]:
    """The dataset's Parquet files in order (oldest day first; the replay: version by version), from `since`
    ('YYYY-MM-DD', a file's day) on."""
    root = snapshot_dir(season, name)
    if not os.path.isdir(root):
        return []
    folders = [os.path.join(root, d) for d in sorted(os.listdir(root))
               if os.path.isdir(os.path.join(root, d))] if name == REPLAY else [root]
    return [os.path.join(folder, f) for folder in folders for f in sorted(os.listdir(folder))
            if f.endswith('.parquet') and (since is None or f[:10] >= since)]


def snapshot_exists(name: str, season: int = CURRENT_SEASON) -> bool:
    return bool(_files(name, season))


def snapshot_signature(name: str, season: int = CURRENT_SEASON) -> Tuple[int, float]:
    """(number of files, newest modification time): changes whenever a fetch is saved, for cache keys."""
    files = _files(name, season)
    return len(files), max((os.path.getmtime(f) for f in files), default=0.0)


def _unify(tables: List[pa.Table]) -> List[pa.Table]:
    """The tables with every column's type made one: int and float become float, a column empty in some days
    takes the others' type; a column that is a number in some days and text in others becomes text (as a CSV
    column holding both was read)."""
    types: Dict[str, set] = {}
    for t in tables:
        for field in t.schema:
            types.setdefault(field.name, set()).add(field.type)
    text = set()
    for col, kinds in types.items():
        kinds = {k for k in kinds if not pa.types.is_null(k)}
        if len(kinds) > 1:
            try:
                pa.unify_schemas([pa.schema([pa.field(col, k)]) for k in kinds], promote_options='permissive')
            except _ARROW_ERRORS:
                text.add(col)
    if not text:
        return tables
    out = []
    for t in tables:
        for col in text & set(t.column_names):
            i = t.column_names.index(col)
            t = t.set_column(i, col, t.column(i).cast(pa.string()))
        out.append(t)
    return out


def _concat(tables: List[pa.Table]) -> pa.Table:
    """The tables one after the other; columns in the order they first appear (a later one's new columns at the
    end), missing ones empty."""
    return pa.concat_tables(_unify(tables), promote_options='permissive')


def _to_pandas(table: pa.Table) -> pd.DataFrame:
    # a column with no value at all is float (NaN), as read_csv gives it
    for i, field in enumerate(table.schema):
        if pa.types.is_null(field.type):
            table = table.set_column(i, field.name, table.column(i).cast(pa.float64()))
    return table.to_pandas()


def _to_arrow(df: pd.DataFrame) -> pa.Table:
    """df as an Arrow table, as a CSV would have kept it: empty text is no value (read_csv gives NaN), and a column
    of mixed Python values (numbers and text) is saved as text."""
    df = df.reset_index(drop=True)
    columns = {}
    for col in df.columns:
        values = df[col]
        if not (pd.api.types.is_numeric_dtype(values) or pd.api.types.is_bool_dtype(values)):
            values = values.mask(values.astype(object).eq(''))
        try:
            columns[str(col)] = pa.array(values, from_pandas=True)
        except _ARROW_ERRORS:
            columns[str(col)] = pa.array(values.map(lambda v: None if pd.isna(v) else str(v)), type=pa.string())
    return pa.table(columns)


def _pin(table: pa.Table, saved: Optional[pa.Schema]) -> pa.Table:
    """The new rows' columns in the saved order (new columns at the end) and, where it fits, of the saved type, so
    the day files don't drift (an id read as int one day, as float the next)."""
    if saved is None:
        return table
    order = [c for c in saved.names if c in table.column_names] + \
            [c for c in table.column_names if c not in saved.names]
    table = table.select(order)
    for i, field in enumerate(table.schema):
        if field.name in saved.names:
            want = saved.field(field.name).type
            if field.type != want and not pa.types.is_null(want):
                try:
                    table = table.set_column(i, field.name, table.column(i).cast(want))
                except _ARROW_ERRORS:
                    pass                   # e.g. 1.5 into an int column: left to _unify when read
    return table


def _write(table: pa.Table, path: str):
    atomic_write(path, lambda f: pq.write_table(table, f, compression=_COMPRESSION), mode='wb')


def load_snapshot(name: str, season: int = CURRENT_SEASON, columns: Optional[List[str]] = None,
                  since=None, display_names: bool = True) -> pd.DataFrame:
    """Every saved row of a dataset (SNAPSHOTS or REPLAY), oldest fetch first; empty when nothing is saved.
    columns: only these (a column a day lacks is empty there). since: a day (date, Timestamp or 'YYYY-MM-DD');
    days before it are skipped, starting one day early, so a night (ET) that began on the UTC day before is whole;
    the rows aren't filtered further. display_names: names as people write them (read_snapshot did that; False
    gives them as saved)."""
    if since is not None:
        since = (pd.Timestamp(since).normalize() - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    files = _files(name, season, since)
    if not files:
        return pd.DataFrame(columns=columns) if columns else pd.DataFrame()
    tables = []
    for path in files:
        if columns is None:
            tables.append(pq.read_table(path))
        else:
            have = set(pq.read_schema(path).names)
            tables.append(pq.read_table(path, columns=[c for c in columns if c in have]))
    df = _to_pandas(_concat(tables))
    if columns is not None:
        df = df.reindex(columns=columns)
    return _display_names(df) if display_names else df


def latest_snapshot(name: str, season: int = CURRENT_SEASON, columns: Optional[List[str]] = None,
                    display_names: bool = True) -> pd.DataFrame:
    """The rows of the newest fetch (its fetched_at kept); empty when nothing is saved. Reads only the newest day's
    file, which holds the newest fetch."""
    files = _files(name, season)
    if not files:
        return pd.DataFrame(columns=columns) if columns else pd.DataFrame()
    read = None if columns is None else list(dict.fromkeys(['fetched_at', *columns]))
    if read is not None:
        have = set(pq.read_schema(files[-1]).names)
        read = [c for c in read if c in have]
    df = _to_pandas(pq.read_table(files[-1], columns=read))
    df = df[df['fetched_at'] == df['fetched_at'].max()].reset_index(drop=True)
    if columns is not None:
        df = df.reindex(columns=list(dict.fromkeys(['fetched_at', *columns])))
    return _display_names(df) if display_names else df


def latest_fetch(name: str, season: int = CURRENT_SEASON) -> Optional[str]:
    """fetched_at of the newest saved fetch ('2026-11-27T16:00:00Z'), None when nothing is saved."""
    files = _files(name, season)
    if not files:
        return None
    fetched = pq.read_table(files[-1], columns=['fetched_at']).column('fetched_at')
    last = pc.max(fetched).as_py()
    return last if isinstance(last, str) else None


def dataset_lock(name: str, season: int = CURRENT_SEASON):
    """The dataset's lock (safe_io.locked): held while a fetch is appended, and by a caller that reads the saved
    rows and appends what changed (fetch_loop.save_quotes)."""
    return locked(snapshot_dir(season, name))


def append_snapshot(name: str, df: pd.DataFrame, season: int = CURRENT_SEASON) -> int:
    """Append rows (with fetched_at) to their days' files, under the dataset's lock and atomically: the rows
    already saved stay as they are, new columns go at the end. Returns the rows appended."""
    if df.empty:
        return 0
    days = _day(df['fetched_at']).reset_index(drop=True)
    with dataset_lock(name, season):
        files = _files(name, season)
        new = _pin(_to_arrow(df), pq.read_schema(files[-1]) if files else None)
        for day in sorted(days.unique()):
            rows = new.take(pa.array(days.index[days == day]))
            path = os.path.join(snapshot_dir(season, name), f"{day}.parquet")
            _write(_concat([pq.read_table(path), rows]) if os.path.exists(path) else rows, path)
    return len(df)


def write_replay(version: str, df: pd.DataFrame, season: int = CURRENT_SEASON) -> int:
    """Replace the replay of one model version with df (other versions' are kept), one file per day of
    fetched_at. A day whose rows didn't change is written with the same bytes, so git sees no change."""
    folder = os.path.join(snapshot_dir(season, REPLAY), version)
    days = _day(df['fetched_at']).reset_index(drop=True)
    with dataset_lock(REPLAY, season):
        table = _to_arrow(df)
        keep = set()
        for day in sorted(days.unique()):
            path = os.path.join(folder, f"{day}.parquet")
            _write(table.take(pa.array(days.index[days == day])), path)
            keep.add(path)
        for old in (os.path.join(folder, f) for f in os.listdir(folder)) if os.path.isdir(folder) else []:
            if old.endswith('.parquet') and old not in keep:
                os.remove(old)
    return len(df)


def export_csv(name: str, out: str, season: int = CURRENT_SEASON) -> int:
    """A dataset written to one CSV file (to read it as text); returns its rows."""
    df = load_snapshot(name, season, display_names=False)
    df.to_csv(out, index=False)
    return len(df)


def _checked_file(season: int) -> str:
    return os.path.join(data_dir(season), "checked_through.txt")


# current season's files, used by the analysis code
GAMES_FILE = games_file(CURRENT_SEASON)
PLAYERS_FILE = players_file(CURRENT_SEASON)


def _read(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path, dtype={'game_id': str})


def stored_game_ids(season: int) -> Set[str]:
    games = _read(games_file(season))
    return set(games['game_id']) if not games.empty else set()


def checked_through(season: int) -> Optional[str]:
    """Last date (YYYY-MM-DD) up to which every day's games are known to be stored."""
    if not os.path.exists(_checked_file(season)):
        return None
    with open(_checked_file(season)) as f:
        return f.read().strip() or None


def set_checked_through(season: int, day: str):
    atomic_write_text(_checked_file(season), day + '\n')


def _append(season: int, path: str, rows: List[Dict], columns: List[str]):
    append_csv(pd.DataFrame(rows, columns=columns), path, columns)


def _drop_game(path: str, game_id: str):
    with locked(path):
        df = _read(path)
        if not df.empty and (df['game_id'] == game_id).any():
            atomic_to_csv(df[df['game_id'] != game_id], path)


def save_game(season: int, game: Dict, players: List[Dict], replace: bool = False):
    """Store one game. Player rows go first and the game row last, so an interrupted
    save leaves the game unrecorded and it gets re-scraped on the next run.
    replace=True first removes rows already stored for this game (needed when re-scraping it)."""
    if replace:
        _drop_game(games_file(season), game['game_id'])
        _drop_game(players_file(season), game['game_id'])
    _append(season, players_file(season), players, PLAYER_COLUMNS)
    _append(season, games_file(season), [game], GAME_COLUMNS)


def load_player_gamelogs(seasons: Iterable[int]) -> pd.DataFrame:
    """Player game logs of several seasons in one DataFrame, e.g. load_player_gamelogs([2024, 2025, 2026])."""
    frames = [_read(players_file(season)) for season in seasons]
    return pd.concat([f for f in frames if not f.empty], ignore_index=True)


def load_games(seasons: Iterable[int]) -> pd.DataFrame:
    """games.csv of several seasons in one DataFrame, with `date` parsed."""
    frames = [_read(games_file(season)) for season in seasons]
    df = pd.concat([f for f in frames if not f.empty], ignore_index=True)
    df['date'] = pd.to_datetime(df['date'])
    return df


def wipe(season: int):
    if os.path.isdir(data_dir(season)):
        shutil.rmtree(data_dir(season))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Read a saved snapshot dataset as text.")
    sub = parser.add_subparsers(dest='command', required=True)
    export = sub.add_parser('export', help="write a dataset (e.g. superbet_props) to one CSV file")
    export.add_argument('name', choices=[*SNAPSHOTS, REPLAY])
    export.add_argument('out')
    export.add_argument('--season', type=int, default=CURRENT_SEASON)
    args = parser.parse_args()
    print(f"{args.out}: {export_csv(args.name, args.out, args.season)} rows")
