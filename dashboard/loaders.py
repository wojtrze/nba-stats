"""Cached data loading for the dashboard."""
import logging
import os

import pandas as pd
import streamlit as st

from espn_scraper import CURRENT_SEASON, NBA_TEAM_ABBRS, SEASONS
from espn_scraper.storage import checked_through, games_file, load_player_gamelogs

from metrics import POSITION_GROUPS, add_combined_stats

log = logging.getLogger(__name__)

def season_label(season: int) -> str:
    return f"{season}/{(season + 1) % 100:02d}"


@st.cache_data(show_spinner="Loading game logs...")
def player_logs() -> pd.DataFrame:
    """All stored seasons' player game logs, NBA teams only, sorted by date, with derived columns."""
    logs = load_player_gamelogs(sorted(SEASONS))
    logs = logs[logs['team'].isin(NBA_TEAM_ABBRS)].copy()
    logs['Date'] = pd.to_datetime(logs['Date'])
    logs = add_combined_stats(logs).sort_values(['Date', 'game_id']).reset_index(drop=True)
    logs['position_group'] = logs['position'].map(POSITION_GROUPS)
    logs['rest_days'] = logs.groupby('player_id_ESPN')['Date'].diff().dt.days
    logs['game_label'] = logs['Date'].dt.strftime('%m-%d') + ' ' + logs['type'].map({'home': 'vs', 'away': '@'}) + \
        ' ' + logs['OPP']
    return logs


@st.cache_data(show_spinner="Loading games...")
def games() -> pd.DataFrame:
    frames = [pd.read_csv(games_file(s), dtype={'game_id': str}) for s in sorted(SEASONS) if os.path.exists(games_file(s))]
    df = pd.concat(frames, ignore_index=True)
    df['date'] = pd.to_datetime(df['date'])
    return df


@st.cache_data(show_spinner="Loading assessed bets...")
def assessed_bets() -> pd.DataFrame:
    df = pd.read_csv('assessed_bets.csv')
    df['closed_date'] = pd.to_datetime(df['closed_date'])
    df['is_hit'] = df['is_hit'].astype(bool)
    return df


@st.cache_data(ttl=600, show_spinner="Fetching today's Superbet props...")
def today_props() -> pd.DataFrame:
    """Superbet's over/under player props for the next 36 hours, one row per line (over and under merged)."""
    from superbet_fetcher import all_today_props
    props = pd.DataFrame(all_today_props())
    if props.empty:
        return props
    keys = ['name', 'name_ESPN', 'home', 'away', 'bet_type', 'line', 'event_id', 'start_time']
    wide = props.pivot_table(index=keys, columns='over_under', values='odds', aggfunc='first').reset_index()
    wide.columns.name = None
    return wide.rename(columns={'Over': 'over_odds', 'Under': 'under_odds'})


@st.cache_data(ttl=1800, show_spinner="Checking RotoWire lineups...")
def unlikely_to_play() -> pd.DataFrame:
    """Players RotoWire lists as doubtful/out; empty if the page can't be read."""
    try:
        from lineup_fetcher import players_unlikely_to_play
        df = pd.DataFrame(players_unlikely_to_play())
    except Exception as e:
        log.warning("RotoWire lineups unavailable: %s", e)
        return pd.DataFrame(columns=['name', 'team', 'likelihood'])
    if df.empty:
        return pd.DataFrame(columns=['name', 'team', 'likelihood', 'name_ESPN'])
    return df.assign(name_ESPN=df['name'].str.replace(' ', '', regex=False))


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
    _persistent("season_types", ['pre', 'regular', 'playin', 'post'])
    chosen = st.sidebar.multiselect("Seasons", list(labels), key="seasons", on_change=_remember, args=("seasons",))
    types = st.sidebar.multiselect("Game types", ['pre', 'regular', 'playin', 'post'], key="season_types",
                                   on_change=_remember, args=("season_types",),
                                   help="Preseason is included by default early in the season, when it's all there is.")
    return [labels[c] for c in chosen], types


def filtered_logs(seasons, season_types) -> pd.DataFrame:
    logs = player_logs()
    return logs[logs['season_id'].isin(seasons) & logs['season_type'].isin(season_types)]
