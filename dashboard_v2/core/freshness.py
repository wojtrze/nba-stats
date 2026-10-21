"""How fresh each data source is (no Streamlit, so it can be tested): ok, stale or missing, with a short label."""
import os
from datetime import date, datetime, timedelta, timezone
from typing import Dict, Optional
from zoneinfo import ZoneInfo

import pandas as pd

from espn_scraper import CURRENT_SEASON
from espn_scraper.storage import checked_through, snapshot_file

ET = ZoneInfo('US/Eastern')
PL = ZoneInfo('Europe/Warsaw')
# odds and lineups change through the day; older than this, the page is reading yesterday's picture
MAX_LIVE_AGE = timedelta(hours=3)
LEVEL_ICONS = {'ok': '🟢', 'stale': '🟠', 'missing': '🔴'}


def _status(level: str, label: str, detail: str = '') -> Dict:
    return {'level': level, 'icon': LEVEL_ICONS[level], 'label': label, 'detail': detail}


def age_text(age: timedelta) -> str:
    minutes = int(age.total_seconds() // 60)
    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{minutes} min ago"
    if minutes < 48 * 60:
        return f"{minutes // 60} h ago"
    return f"{minutes // (24 * 60)} days ago"


def stats_status(checked: Optional[str], now: datetime) -> Dict:
    """ESPN stats are complete when every game up to yesterday (US Eastern) is stored."""
    if not checked:
        return _status('missing', "no games stored", "Run the stats update")
    yesterday = now.astimezone(ET).date() - timedelta(days=1)
    day = date.fromisoformat(checked)
    if day >= yesterday:
        return _status('ok', f"through {day:%b %d}", "Every finished game is stored")
    behind = (yesterday - day).days
    return _status('stale', f"through {day:%b %d}", f"{behind} day{'s' * (behind > 1)} of games missing: run the "
                                                    f"stats update")


def live_status(live: Optional[bool], fetched_at: Optional[datetime], rows: Optional[int], now: datetime,
                what: str) -> Dict:
    """Superbet / RotoWire: live = fetched from the site (Superbet only on demand, so it ages too); False = the site failed and the last saved snapshot
    was used (fetched_at = that snapshot's time); None = not fetched in this session, only the snapshot file is
    known (rows None = not counted)."""
    if fetched_at is None:
        return _status('missing', "not fetched", f"No {what} yet: fetch them in the Data center")
    age = now - fetched_at
    level = 'ok' if age <= MAX_LIVE_AGE else 'stale'
    if live:
        count = f"{rows} {what}, " if rows is not None else ""
        return _status(level, f"fetched {age_text(age)}", f"{count}fetched {fetched_at.astimezone(PL):%a %H:%M}")
    count = f"{rows} {what} from the snapshot" if rows is not None else "Snapshot"
    return _status(level, f"snapshot, {age_text(age)}",
                   f"{count} saved {fetched_at.astimezone(PL):%a %H:%M}"
                   + (": the site couldn't be reached" if live is False else ""))


def last_snapshot(name: str, season: int = CURRENT_SEASON) -> Optional[datetime]:
    """Time of the newest saved snapshot of 'superbet_props', 'superbet_game_odds' or 'rotowire_lineups'."""
    path = snapshot_file(season, name)
    if not os.path.exists(path):
        return None
    fetched = pd.read_csv(path, usecols=['fetched_at'])['fetched_at']
    return pd.to_datetime(fetched.max(), utc=True).to_pydatetime() if len(fetched) else None


def overview(live: Dict[str, Dict], now: Optional[datetime] = None) -> Dict[str, Dict]:
    """Status of every source. live: {'superbet' / 'rotowire': {'live', 'fetched_at', 'rows'}} as recorded by
    core.data when it last fetched; a source missing there falls back to its newest snapshot file."""
    now = now or datetime.now(timezone.utc)
    out = {'stats': stats_status(checked_through(CURRENT_SEASON), now)}
    for key, snapshot, what in (('superbet', 'superbet_props', 'lines'), ('rotowire', 'rotowire_lineups', 'players')):
        seen = live.get(key)
        if seen:
            out[key] = live_status(seen['live'], seen['fetched_at'], seen['rows'], now, what)
        else:   # not read in this session yet: the newest saved fetch (every Superbet fetch is saved)
            out[key] = live_status(True if key == 'superbet' else None, last_snapshot(snapshot), None, now, what)
    return out
