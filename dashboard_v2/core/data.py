"""Cached data shared by every v2 page, so Overview, Props and Games price the same lines once.

The stored stats and Superbet's offers come from the old dashboard's loaders (same caches, same columns).
Superbet blocks frequent requests, so it's only contacted on demand (loaders.fetch_superbet, the Data center's
Fetch now and Save snapshot), and every fetch is saved; the pages read the newest one.
RotoWire is fetched here rather than through loaders, so the pages can tell live lineups from a fallback
snapshot; it's kept for 30 minutes.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, List

import pandas as pd
import streamlit as st

from espn_scraper import CURRENT_SEASON
from loaders import (LINEUP_COLUMNS, _latest_snapshot, filtered_logs, games, name_resolver, player_logs,
                     reload_superbet_snapshot, snapshot_history, superbet_offers)
from metrics import absence_adjustments, absence_impact
from models import GAME_DEFAULTS, GAME_TYPES, game_ratings, price_games, price_props
from tracking import game_odds_movement, prop_movement

log = logging.getLogger(__name__)

# what the pages are reading from each source: {'live', 'fetched_at', 'rows'}; read by the freshness strip.
# Module-level, so it survives reruns and page switches.
LAST_FETCH: Dict[str, Dict] = {}


def _snapshot_time(name: str):
    history = snapshot_history(name)
    return pd.to_datetime(history['fetched_at'].max(), utc=True).to_pydatetime() if len(history) else None


def superbet() -> Dict:
    """loaders.superbet_offers (the newest saved fetch; never contacts Superbet), noting for the freshness strip
    when it was fetched."""
    offers = superbet_offers()
    LAST_FETCH['superbet'] = {'live': True, 'fetched_at': offers['fetched_at'], 'rows': len(offers['props'])}
    return offers


@st.cache_data(ttl=1800, show_spinner="Checking RotoWire's lineups...")
def rotowire() -> Dict:
    """RotoWire's expected/confirmed lineups for today with ESPN ids ('lineups'), live or from the latest
    snapshot; empty (with the usual columns) when there's neither."""
    try:
        from lineup_fetcher import fetch_lineups
        df = pd.DataFrame(fetch_lineups())
        live, fetched_at, error = True, datetime.now(timezone.utc), None
    except Exception as e:
        log.warning("RotoWire lineups unavailable, using the last snapshot: %s", e)
        df = _latest_snapshot('rotowire_lineups')
        live, fetched_at, error = False, _snapshot_time('rotowire_lineups'), str(e)
    df = pd.DataFrame(columns=LINEUP_COLUMNS) if df.empty else name_resolver().add_ids(df)
    LAST_FETCH['rotowire'] = {'live': live, 'fetched_at': fetched_at, 'rows': len(df)}
    return {'lineups': df, 'live': live, 'fetched_at': fetched_at, 'error': error}


def props() -> pd.DataFrame:
    return superbet()['props']


def game_odds() -> pd.DataFrame:
    return superbet()['game_odds']


def lineups() -> pd.DataFrame:
    return rotowire()['lineups']


def clear_live():
    """Re-read the snapshots and fetch RotoWire again on the next page load. Superbet's last on-demand fetch is
    kept: the pages use it until a newer snapshot exists."""
    reload_superbet_snapshot()
    rotowire.clear()
    snapshot_history.clear()


def clear_stats():
    """Reload the stored stats after the scraper added games."""
    player_logs.clear()
    games.clear()
    name_resolver.clear()


@st.cache_data(show_spinner="Adjusting for tonight's absences...")
def _adjustments(part, players, out, stats):
    return absence_adjustments(part, players, out, stats)


@st.cache_data(ttl=600, show_spinner="Pricing today's lines...")
def _priced_props(seasons, season_types, props_, lineups_, odds) -> pd.DataFrame:
    g = games()
    g = g[g['season_id'].isin(seasons) & g['season_type'].isin(season_types)]
    table = price_props(props_, filtered_logs(list(seasons), list(season_types)), lineups_, odds, g,
                        adjust=_adjustments)
    table = prop_movement(snapshot_history('superbet_props'), table)
    # ESPN's "Bam Adebayo" reads better than Superbet's "Adebayo, Bam"; unmatched names stay as Superbet has them
    display = player_logs().groupby('player_id_ESPN')['player_display_name'].last()
    table['name'] = table['player_id'].map(display).fillna(table['name'])
    # the hit rate of the picked side, so one column answers "how often did this pick win lately"
    over = table['best side'] == 'Over'
    table['pick % L10'] = table['over % L10'].where(over, table['under % L10'])
    table['pick %'] = table['over %'].where(over, table['under %'])
    return table


def priced_props(seasons: List[int], season_types: List[str]) -> pd.DataFrame:
    """Every Superbet line priced with models.price_props (empty when Superbet has no props)."""
    if props().empty:
        return pd.DataFrame()
    return _priced_props(tuple(seasons), tuple(season_types), props(), lineups(), game_odds())


def game_model(prior_games=GAME_DEFAULTS['prior_games'], regress=GAME_DEFAULTS['regress']) -> Dict:
    """models.game_ratings plus the logs the absence model uses (current and last season, real games)."""
    model = game_ratings(games(), CURRENT_SEASON, prior_games, regress)
    logs = player_logs()
    model['logs'] = logs[logs['season_id'].isin([CURRENT_SEASON - 1, CURRENT_SEASON])
                         & logs['season_type'].isin(GAME_TYPES)]
    return model


@st.cache_data(show_spinner=False)
def _impact(team, player_id, shrink, prior_games, regress):
    model = game_model(prior_games, regress)
    return absence_impact(model['games'], model['logs'], team, player_id, shrink)


@st.cache_data(ttl=600, show_spinner="Pricing today's games...")
def _priced_games(odds, lineups_, prior_games, regress, home_court, shrink, out_max, all_lines) -> List[Dict]:
    model = game_model(prior_games, regress)
    priced = price_games(odds, model['ratings'], lineups_, model['games'], model['logs'], home_court, shrink, out_max,
                         all_lines, impact=lambda t, p, s: _impact(t, p, s, prior_games, regress))
    history = snapshot_history('superbet_game_odds')
    for game in priced:
        game['edges'] = game_odds_movement(history, game['edges'])
    return priced


def priced_games(prior_games=GAME_DEFAULTS['prior_games'], regress=GAME_DEFAULTS['regress'],
                 home_court=GAME_DEFAULTS['home_court'], shrink=GAME_DEFAULTS['shrink'],
                 out_max=GAME_DEFAULTS['out_max'], all_lines=False) -> List[Dict]:
    """models.price_games for every Superbet game, with odds movement; [] when Superbet has no games."""
    if game_odds().empty:
        return []
    return _priced_games(game_odds(), lineups(), prior_games, regress, home_court, shrink, out_max, all_lines)
