"""Cached data loading for the dashboard."""
import logging
import os

import pandas as pd
import streamlit as st

from espn_scraper import CURRENT_SEASON, SEASONS
from espn_scraper.storage import checked_through, load_games, load_player_gamelogs, snapshot_file
from name_resolver import NameResolver

from models import DEFAULT_SEASON_TYPES, prepare_logs

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


@st.cache_data(ttl=600, show_spinner="Fetching today's Superbet offers...")
def superbet_offers() -> dict:
    """Superbet's player props (over and under merged into one row per line) and game odds for the next 36 hours,
    with ESPN player ids. Falls back to the latest snapshot if Superbet can't be reached."""
    from daily_snapshot import merge_over_under
    try:
        from superbet_fetcher import todays_offers
        offers = todays_offers()
        props, game_odds = merge_over_under(pd.DataFrame(offers['props'])), pd.DataFrame(offers['game_odds'])
    except Exception as e:
        log.warning("Superbet unavailable, using the last snapshot: %s", e)
        props, game_odds = _latest_snapshot('superbet_props'), _latest_snapshot('superbet_game_odds')
    if not props.empty:
        props = name_resolver().add_ids(props, team_cols=('home', 'away'))
    return {'props': props, 'game_odds': game_odds}


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
