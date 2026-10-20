"""Save today's RotoWire lineups and Superbet offers to data/<season>/ so lines and statuses can be checked later.

    python daily_snapshot.py              # today's games
    python daily_snapshot.py --tomorrow   # RotoWire's lineups for tomorrow (Superbet always covers the next 36h)

Each run appends rows with a fetched_at timestamp (UTC), so running it several times a day keeps line movement
and lineup changes.
"""
import argparse
import logging
import os
from datetime import datetime, timezone

import pandas as pd

from espn_scraper import CURRENT_SEASON
from espn_scraper.storage import snapshot_file

log = logging.getLogger(__name__)


def merge_over_under(props: pd.DataFrame) -> pd.DataFrame:
    """One row per player line with over_odds and under_odds (Superbet lists them as separate outcomes)."""
    if props.empty:
        return props
    keys = ['name', 'name_ESPN', 'home', 'away', 'bet_type', 'line', 'event_id', 'start_time']
    wide = props.pivot_table(index=keys, columns='over_under', values='odds', aggfunc='first').reset_index()
    wide.columns.name = None
    return wide.rename(columns={'Over': 'over_odds', 'Under': 'under_odds'})


def _append(name: str, df: pd.DataFrame, fetched_at: str) -> int:
    if df.empty:
        return 0
    path = snapshot_file(CURRENT_SEASON, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.insert(0, 'fetched_at', fetched_at)
    if os.path.exists(path):
        # keep the file's column order; new columns go at the end
        existing = list(pd.read_csv(path, nrows=0).columns)
        if set(df.columns) - set(existing):
            old = pd.read_csv(path)
            pd.concat([old, df], ignore_index=True).to_csv(path, index=False)
            return len(df)
        df = df.reindex(columns=existing)
    df.to_csv(path, mode='a', header=not os.path.exists(path), index=False)
    return len(df)


def take_snapshot(date: str = 'today') -> dict:
    """Fetch both sources and append them. A source that fails is reported and skipped."""
    from lineup_fetcher import fetch_lineups
    from superbet_fetcher import todays_offers

    fetched_at = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    counts = {}
    try:
        counts['rotowire_lineups'] = _append('rotowire_lineups', pd.DataFrame(fetch_lineups(date)), fetched_at)
    except Exception as e:
        log.error("RotoWire failed: %s", e)
        counts['rotowire_lineups'] = None
    try:
        offers = todays_offers()
        counts['superbet_props'] = _append('superbet_props', merge_over_under(pd.DataFrame(offers['props'])), fetched_at)
        counts['superbet_game_odds'] = _append('superbet_game_odds', pd.DataFrame(offers['game_odds']), fetched_at)
    except Exception as e:
        log.error("Superbet failed: %s", e)
        counts['superbet_props'] = counts['superbet_game_odds'] = None
    return counts


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--tomorrow', action='store_true', help="RotoWire's lineups for tomorrow")
    args = parser.parse_args()
    for name, n in take_snapshot('tomorrow' if args.tomorrow else 'today').items():
        print(f"{name}: {'failed' if n is None else f'{n} rows'}")
