"""Which fetched Superbet lines can still be bet, and how tip-off times read (no Streamlit, so it can be tested)."""
from datetime import datetime
from typing import Dict, Optional

import pandas as pd

PL, ET = 'Europe/Warsaw', 'US/Eastern'
# a game this close to tip-off gets the "starts soon" mark
SOON_MINUTES = 60


def _start(df: pd.DataFrame) -> pd.Series:
    return pd.to_datetime(df['start_time'], utc=True)


def upcoming(df: pd.DataFrame, now: datetime) -> pd.DataFrame:
    """Rows of games that haven't tipped off, earliest tip-off first (ties keep their order). A started game can't
    be bet before the game any more."""
    if df.empty:
        return df
    start = _start(df)
    keep = df[start > pd.Timestamp(now)]
    return keep.iloc[_start(keep).argsort(kind='stable')].reset_index(drop=True)


def offers_status(props: pd.DataFrame, game_odds: pd.DataFrame, fetched_at: Optional[datetime],
                  now: datetime) -> Dict:
    """What the last fetch still offers. props / game_odds: every line of the last fetch (started or not).
    state: 'available' (some game hasn't tipped off), 'all_started' (every game has), 'none_saved' (nothing
    fetched yet). Also: fetched_at, nights (the games' US-Eastern dates, as the stored stats use), games, lines."""
    parts = [df[['event_id', 'start_time']] for df in (props, game_odds) if not df.empty]
    rows = pd.concat(parts) if parts else pd.DataFrame()
    if fetched_at is None or rows.empty:
        return {'state': 'none_saved', 'fetched_at': fetched_at, 'nights': [], 'games': 0, 'lines': 0}
    start = _start(rows)
    nights = sorted(set(start.dt.tz_convert(ET).dt.date))
    return {'state': 'available' if (start > pd.Timestamp(now)).any() else 'all_started', 'fetched_at': fetched_at,
            'nights': nights, 'games': rows['event_id'].nunique(), 'lines': len(props)}


def _utc(start_time) -> pd.Timestamp:
    ts = pd.Timestamp(start_time)
    return ts.tz_localize('UTC') if ts.tzinfo is None else ts.tz_convert('UTC')


def minutes_to(start_time, now: datetime) -> float:
    return (_utc(start_time) - pd.Timestamp(now)).total_seconds() / 60


def starts_soon(start_time, now: datetime) -> bool:
    """Tip-off within the next SOON_MINUTES."""
    return 0 < minutes_to(start_time, now) <= SOON_MINUTES


def tip_label(start_time, now: datetime) -> str:
    """'Thu 01:00' in Polish time; '⏰ in 35 min (01:00)' when tip-off is at most an hour away."""
    start = _utc(start_time)
    if starts_soon(start, now):
        return f"⏰ in {max(1, round(minutes_to(start, now)))} min ({start.tz_convert(PL):%H:%M})"
    return f"{start.tz_convert(PL):%a %H:%M}"


def nights_text(nights) -> str:
    """'Oct 21', or 'Oct 21 – Oct 22' when the fetch covered two nights."""
    if not nights:
        return ''
    return f"{nights[0]:%b %d}" + (f" – {nights[-1]:%b %d}" if nights[-1] != nights[0] else '')


def no_offers_text(status: Dict, results_stored: bool, lang: str = 'en') -> str:
    """Markdown for the pages when the last fetch has nothing left to bet (status: offers_status output).
    results_stored: the stored stats already hold that night, so its lines are settled. lang: i18n language."""
    from i18n import t
    if status['state'] == 'none_saved':
        return t('offers.none_saved', lang)
    when = pd.Timestamp(status['fetched_at']).tz_convert(PL)
    text = t('offers.all_started', lang, when=f"{when:%a %d %b %H:%M}", lines=f"{status['lines']:,}",
             games=status['games'], nights=nights_text(status['nights']))
    if not results_stored:
        text += t('offers.pending', lang)
    return text
