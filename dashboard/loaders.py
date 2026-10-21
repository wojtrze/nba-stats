"""Cached data loading for the dashboard."""
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import pandas as pd
import streamlit as st

from espn_scraper import CURRENT_SEASON, SEASONS
from espn_scraper.storage import checked_through, load_games, load_player_gamelogs, snapshot_file
from name_resolver import NameResolver

from models import DEFAULT_SEASON_TYPES, prepare_logs
from schedule import offers_status, upcoming

log = logging.getLogger(__name__)

def season_label(season: int) -> str:
    return f"{season}/{(season + 1) % 100:02d}"


@st.cache_data(show_spinner="Loading game logs...")
def player_logs() -> pd.DataFrame:
    """All stored seasons' player game logs, NBA teams only, sorted by date, with derived columns."""
    return prepare_logs(load_player_gamelogs(sorted(SEASONS)))


@st.cache_data(show_spinner="Loading games...")
def games() -> pd.DataFrame:
    return load_games(sorted(SEASONS))


@st.cache_data(show_spinner="Loading assessed bets...")
def assessed_bets() -> pd.DataFrame:
    df = pd.read_csv('assessed_bets.csv')
    df['closed_date'] = pd.to_datetime(df['closed_date'])
    df['is_hit'] = df['is_hit'].astype(bool)
    return df


@st.cache_resource(show_spinner=False)
def name_resolver() -> NameResolver:
    return NameResolver(player_logs())


def _latest_snapshot(name: str) -> pd.DataFrame:
    """The last fetch stored by daily_snapshot.py, used when a live source fails."""
    path = snapshot_file(CURRENT_SEASON, name)
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path)
    return df[df['fetched_at'] == df['fetched_at'].max()].drop(columns='fetched_at')


@st.cache_data(ttl=600, show_spinner=False)
def snapshot_history(name: str) -> pd.DataFrame:
    """Every fetch stored by daily_snapshot.py (empty if none), for line movement and settling bets."""
    path = snapshot_file(CURRENT_SEASON, name)
    return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()


# --- Superbet, on demand only ---
# Superbet blocks frequent requests, so the pages never fetch it themselves. A fetch happens only when asked for
# (fetch_superbet, behind a "Fetch from Superbet" button, or a snapshot run) and is always saved to the snapshot
# files, so the pages read one source, the newest snapshot, and a restart shows exactly what was fetched.

# the shortest gap between two requests to Superbet (fetches and snapshot runs)
SUPERBET_COOLDOWN = timedelta(minutes=5)
# the snapshot's model columns; the pages price the lines themselves
_MODEL_COLUMNS = ['player_id_ESPN', 'pick', 'model_pct', 'edge_pp', 'edge_low', 'proj_avg']


@st.cache_resource(show_spinner=False)
def _superbet_store() -> Dict:
    """The last request to Superbet ('tried_at') and the last fetch's error, shared by every browser tab so two
    tabs can't double the requests."""
    return {}


def _snapshot_mtime() -> float:
    path = snapshot_file(CURRENT_SEASON, 'superbet_props')
    return os.path.getmtime(path) if os.path.exists(path) else 0.0


@st.cache_data(show_spinner="Reading the latest Superbet fetch...")
def _superbet_snapshot(mtime: float) -> Dict:
    """Every line and game odd of the newest fetch (props with ESPN ids) and when it was fetched; mtime is the
    file's, so a new fetch is read again."""
    path = snapshot_file(CURRENT_SEASON, 'superbet_props')
    fetched = pd.read_csv(path, usecols=['fetched_at'])['fetched_at'] if os.path.exists(path) else pd.Series()
    props = _latest_snapshot('superbet_props').drop(columns=_MODEL_COLUMNS, errors='ignore')
    if not props.empty:
        props = name_resolver().add_ids(props, team_cols=('home', 'away'))
    return {'props': props, 'game_odds': _latest_snapshot('superbet_game_odds'),
            'fetched_at': pd.to_datetime(fetched.max(), utc=True).to_pydatetime() if len(fetched) else None}


def superbet_offers() -> dict:
    """The newest Superbet fetch, never contacting Superbet: 'props' (over and under merged into one row per line,
    with ESPN player ids) and 'game_odds' of the games that haven't tipped off, earliest first; 'fetched_at';
    'status' (schedule.offers_status: available / all_started / none_saved, the nights, games and lines)."""
    snapshot = _superbet_snapshot(_snapshot_mtime())
    now = datetime.now(timezone.utc)
    return {'props': upcoming(snapshot['props'], now), 'game_odds': upcoming(snapshot['game_odds'], now),
            'fetched_at': snapshot['fetched_at'],
            'status': offers_status(snapshot['props'], snapshot['game_odds'], snapshot['fetched_at'], now)}


def superbet_wait() -> Optional[timedelta]:
    """How long until Superbet may be contacted again; None = now."""
    tried = _superbet_store().get('tried_at')
    left = tried + SUPERBET_COOLDOWN - datetime.now(timezone.utc) if tried else None
    return left if left and left > timedelta(0) else None


def superbet_error() -> Optional[str]:
    """The last on-demand fetch's error, None if it worked."""
    return _superbet_store().get('error')


def note_superbet_contact():
    """daily_snapshot.py contacts Superbet too: start the cooldown before running it."""
    _superbet_store()['tried_at'] = datetime.now(timezone.utc)


def fetch_superbet() -> Optional[str]:
    """Fetch Superbet's offers now, unless it was contacted within SUPERBET_COOLDOWN, and save them to the
    snapshot files with the dashboard's pick for every line (daily_snapshot.save_superbet). Returns the error, or
    None when it worked. A failed fetch saves nothing; the pages keep the previous fetch."""
    from daily_snapshot import save_superbet
    from superbet_fetcher import todays_offers
    if superbet_wait():
        return f"Superbet was contacted less than {SUPERBET_COOLDOWN.seconds // 60} minutes ago"
    store = _superbet_store()
    note_superbet_contact()
    try:
        offers = todays_offers()
    except Exception as e:
        log.warning("Superbet fetch failed: %s", e)
        store['error'] = str(e)
        return store['error']
    try:
        save_superbet(offers, rotowire_lineups(), datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
    except Exception as e:
        log.error("Superbet's offers were fetched but couldn't be saved: %s", e)
        store['error'] = f"fetched, but couldn't be saved: {e}"
        return store['error']
    store['error'] = None
    reload_superbet_snapshot()
    snapshot_history.clear()   # line movement and the results read every fetch
    return None


def reload_superbet_snapshot():
    """Read the snapshot file again (a new fetch is picked up by its mtime anyway)."""
    _superbet_snapshot.clear()


def superbet_fetch_controls(where=st, key: str = 'superbet'):
    """A "Fetch from Superbet" button, off during the cooldown, and when the offers shown were fetched. The fetch
    runs in the click's callback, before the page draws, so the page already shows the new offers."""
    def fetch():
        with st.spinner("Fetching and saving today's Superbet offers..."):
            fetch_superbet()

    offers, wait = superbet_offers(), superbet_wait()
    b, c = where.columns([1, 4], vertical_alignment='center')
    b.button("Fetch from Superbet", key=f'fetch_{key}', disabled=wait is not None, on_click=fetch,
             help=f"Possible again in {wait.seconds // 60 + 1} min" if wait else
             "Superbet blocks frequent requests, so it's only fetched when you press this (at most once every "
             f"{SUPERBET_COOLDOWN.seconds // 60} minutes). Every fetch is saved.")
    when = offers['fetched_at']
    c.caption((f"💰 Superbet offers fetched {pd.Timestamp(when).tz_convert('Europe/Warsaw'):%a %d %b %H:%M} (saved)"
               if when else "💰 No Superbet offers fetched yet")
              + (f" · the last fetch failed: {superbet_error()[:100]}" if superbet_error() else ""))


def today_props() -> pd.DataFrame:
    return superbet_offers()['props']


def today_game_odds() -> pd.DataFrame:
    return superbet_offers()['game_odds']


LINEUP_COLUMNS = ['game_date', 'tip_et', 'away', 'home', 'team', 'side', 'lineup_status', 'role', 'pos', 'name',
                  'rotowire_id', 'play_pct', 'injury', 'player_id_ESPN']


@st.cache_data(ttl=1800, show_spinner="Checking RotoWire lineups...")
def rotowire_lineups() -> pd.DataFrame:
    """RotoWire's expected/confirmed lineups for today with ESPN player ids. Falls back to the latest snapshot
    if the page can't be read; empty if there's none."""
    try:
        from lineup_fetcher import fetch_lineups
        df = pd.DataFrame(fetch_lineups())
    except Exception as e:
        log.warning("RotoWire lineups unavailable, using the last snapshot: %s", e)
        df = _latest_snapshot('rotowire_lineups')
    if df.empty:
        return pd.DataFrame(columns=LINEUP_COLUMNS)
    return name_resolver().add_ids(df)


def unlikely_to_play() -> pd.DataFrame:
    """Players RotoWire lists under "may not play" with less than a 100% chance."""
    df = rotowire_lineups()
    return df[(df['role'] == 'may_not_play') & (df['play_pct'] < 100)]


def season_status() -> pd.DataFrame:
    rows = []
    g = games()
    for season in sorted(SEASONS, reverse=True):
        part = g[g['season_id'] == season]
        counts = part['season_type'].value_counts()
        rows.append({'season': season_label(season), 'games': len(part),
                     'last game': part['date'].max().date() if len(part) else None,
                     'checked through': checked_through(season),
                     **{t: int(counts.get(t, 0)) for t in ['pre', 'regular', 'playin', 'post', 'allstar']}})
    return pd.DataFrame(rows)


def _persistent(key: str, default):
    """Streamlit drops a widget's state when the page changes; keep a copy so filters survive navigation."""
    st.session_state[key] = st.session_state.get(f"_{key}", default)


def _remember(key: str):
    st.session_state[f"_{key}"] = st.session_state[key]


def sidebar_filters():
    """Season and game-type filters shared by the pages. Returns (seasons, season_types)."""
    st.sidebar.header("Filters")
    labels = {season_label(s): s for s in sorted(SEASONS, reverse=True)}
    _persistent("seasons", [season_label(CURRENT_SEASON)])
    _persistent("season_types", DEFAULT_SEASON_TYPES)
    chosen = st.sidebar.multiselect("Seasons", list(labels), key="seasons", on_change=_remember, args=("seasons",))
    types = st.sidebar.multiselect("Game types", ['pre', 'regular', 'playin', 'post'], key="season_types",
                                   on_change=_remember, args=("season_types",),
                                   help="Preseason is included by default early in the season, when it's all there is.")
    return [labels[c] for c in chosen], types


def filtered_logs(seasons, season_types) -> pd.DataFrame:
    logs = player_logs()
    return logs[logs['season_id'].isin(seasons) & logs['season_type'].isin(season_types)]
