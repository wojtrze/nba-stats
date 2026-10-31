"""How fresh each data source is (no Streamlit, so it can be tested): ok, stale or missing, with a short label."""
import os
from datetime import date, datetime, timedelta, timezone
from typing import Dict, Optional
from zoneinfo import ZoneInfo

import pandas as pd

from decisions import MAX_ODDS_AGE
from espn_scraper import CURRENT_SEASON
from i18n import t
from espn_scraper.storage import checked_through, snapshot_file

ET = ZoneInfo('US/Eastern')
PL = ZoneInfo('Europe/Warsaw')
# odds and lineups change through the day; older than this, the page is reading yesterday's picture (the same limit
# makes a decision wait for fresh odds: decisions.MAX_ODDS_AGE)
MAX_LIVE_AGE = MAX_ODDS_AGE
LEVEL_ICONS = {'ok': '🟢', 'stale': '🟠', 'missing': '🔴'}


def _status(level: str, label: str, detail: str = '') -> Dict:
    return {'level': level, 'icon': LEVEL_ICONS[level], 'label': label, 'detail': detail}


def age_text(age: timedelta, lang: str = 'en') -> str:
    minutes = int(age.total_seconds() // 60)
    if minutes < 1:
        return t('fresh.just_now', lang)
    if minutes < 60:
        return t('fresh.min_ago', lang, n=minutes)
    if minutes < 48 * 60:
        return t('fresh.h_ago', lang, n=minutes // 60)
    return t('fresh.days_ago', lang, n=minutes // (24 * 60))


def stats_status(checked: Optional[str], now: datetime, lang: str = 'en') -> Dict:
    """ESPN stats are complete when every game up to yesterday (US Eastern) is stored."""
    if not checked:
        return _status('missing', t('fresh.no_games', lang), t('fresh.run_update', lang))
    yesterday = now.astimezone(ET).date() - timedelta(days=1)
    day = date.fromisoformat(checked)
    if day >= yesterday:
        return _status('ok', t('fresh.through', lang, day=f"{day:%b %d}"), t('fresh.complete', lang))
    behind = (yesterday - day).days
    return _status('stale', t('fresh.through', lang, day=f"{day:%b %d}"), t('fresh.behind', lang, n=behind))


def live_status(live: Optional[bool], fetched_at: Optional[datetime], rows: Optional[int], now: datetime,
                what: str, lang: str = 'en') -> Dict:
    """Superbet / RotoWire: live = fetched from the site (Superbet only on demand, so it ages too); False = the site failed and the last saved snapshot
    was used (fetched_at = that snapshot's time); None = not fetched in this session, only the snapshot file is
    known (rows None = not counted)."""
    if fetched_at is None:
        return _status('missing', t('fresh.not_fetched', lang), t('fresh.none_yet', lang, what=what))
    age = now - fetched_at
    level = 'ok' if age <= MAX_LIVE_AGE else 'stale'
    when = f"{fetched_at.astimezone(PL):%a %H:%M}"
    if live:
        count = t('fresh.count', lang, n=rows, what=what) if rows is not None else ""
        return _status(level, t('fresh.fetched', lang, age=age_text(age, lang)),
                       t('fresh.fetched_detail', lang, count=count, when=when))
    count = t('fresh.snapshot_count', lang, n=rows, what=what) if rows is not None else t('fresh.snapshot_plain', lang)
    return _status(level, t('fresh.snapshot', lang, age=age_text(age, lang)),
                   t('fresh.saved', lang, count=count, when=when)
                   + (t('fresh.unreachable', lang) if live is False else ""))


def last_snapshot(name: str, season: int = CURRENT_SEASON) -> Optional[datetime]:
    """Time of the newest saved snapshot of 'superbet_props', 'superbet_game_odds' or 'rotowire_lineups'."""
    path = snapshot_file(season, name)
    if not os.path.exists(path):
        return None
    fetched = pd.read_csv(path, usecols=['fetched_at'])['fetched_at']
    return pd.to_datetime(fetched.max(), utc=True).to_pydatetime() if len(fetched) else None


def overview(live: Dict[str, Dict], now: Optional[datetime] = None, lang: str = 'en') -> Dict[str, Dict]:
    """Status of every source. live: {'superbet' / 'rotowire': {'live', 'fetched_at', 'rows'}} as recorded by
    core.data when it last fetched; a source missing there falls back to its newest snapshot file."""
    now = now or datetime.now(timezone.utc)
    out = {'stats': stats_status(checked_through(CURRENT_SEASON), now, lang)}
    for key, snapshot, what in (('superbet', 'superbet_props', 'lines'), ('rotowire', 'rotowire_lineups', 'players')):
        seen = live.get(key)
        what = t(f'fresh.{what}', lang)
        if seen:
            out[key] = live_status(seen['live'], seen['fetched_at'], seen['rows'], now, what, lang)
        else:   # not read in this session yet: the newest saved fetch (every Superbet fetch is saved)
            out[key] = live_status(True if key == 'superbet' else None, last_snapshot(snapshot), None, now, what,
                                   lang)
    return out
