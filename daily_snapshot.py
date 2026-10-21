"""Save today's RotoWire lineups and Superbet offers to data/<season>/ so lines and statuses can be checked later.

    python daily_snapshot.py              # today's games
    python daily_snapshot.py --tomorrow   # RotoWire's lineups for tomorrow (Superbet always covers the next 36h)

Each run appends rows with a fetched_at timestamp (UTC), so running it several times a day keeps line movement
and lineup changes. Each line also gets the dashboard's pick and edge at that moment (the default settings of
Today's props and Games), so the Results tracker settles exactly what the pages showed.
"""
import argparse
import logging
import os
import sys
from datetime import datetime, timezone

import pandas as pd

from espn_scraper import CURRENT_SEASON, SEASONS
from espn_scraper.storage import load_games, load_player_gamelogs, snapshot_file

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dashboard'))

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


def add_model_columns(props: pd.DataFrame, game_odds: pd.DataFrame, lineups: pd.DataFrame):
    """props with player_id_ESPN, pick, model_pct, edge_pp, edge_low and proj_avg; game_odds with model_pct and
    edge_pp. Same models and defaults as the dashboard pages (current season, every game type but All-Star)."""
    from models import (DEFAULT_SEASON_TYPES, GAME_DEFAULTS, GAME_TYPES, game_ratings, prepare_logs, price_games,
                        price_props)
    from name_resolver import NameResolver

    logs = prepare_logs(load_player_gamelogs(sorted(SEASONS)))
    games = load_games(sorted(SEASONS))
    resolver = NameResolver(logs)
    if not lineups.empty:
        lineups = resolver.add_ids(lineups)
    if not props.empty:
        props = resolver.add_ids(props, team_cols=('home', 'away'))
        current = logs[(logs['season_id'] == CURRENT_SEASON) & logs['season_type'].isin(DEFAULT_SEASON_TYPES)]
        played = games[(games['season_id'] == CURRENT_SEASON) & games['season_type'].isin(DEFAULT_SEASON_TYPES)]
        table = price_props(props, current, lineups, game_odds, played)
        props = props.assign(pick=table['best side'], model_pct=table['model %'].round(1),
                             edge_pp=table['edge pp'].round(1), edge_low=table['edge low'].round(1),
                             proj_avg=table['proj avg'].round(2))
    if not game_odds.empty:
        model = game_ratings(games, CURRENT_SEASON, GAME_DEFAULTS['prior_games'], GAME_DEFAULTS['regress'])
        recent = logs[logs['season_id'].isin([CURRENT_SEASON - 1, CURRENT_SEASON]) & logs['season_type'].isin(GAME_TYPES)]
        priced = price_games(game_odds, model['ratings'], lineups, model['games'], recent, GAME_DEFAULTS['home_court'],
                             GAME_DEFAULTS['shrink'], GAME_DEFAULTS['out_max'], all_lines=True)
        if priced:
            edges = pd.concat([g['edges'] for g in priced])[['event_id', 'market', 'side', 'line', 'model %', 'edge pp']]
            game_odds = game_odds.merge(edges.rename(columns={'model %': 'model_pct', 'edge pp': 'edge_pp'}).round(1),
                                        on=['event_id', 'market', 'side', 'line'], how='left')
    return props, game_odds


def take_snapshot(date: str = 'today') -> dict:
    """Fetch both sources and append them. A source that fails is reported and skipped."""
    from lineup_fetcher import fetch_lineups
    from superbet_fetcher import todays_offers

    fetched_at = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    counts = {}
    lineups = pd.DataFrame()
    try:
        lineups = pd.DataFrame(fetch_lineups(date))
        counts['rotowire_lineups'] = _append('rotowire_lineups', lineups.copy(), fetched_at)
    except Exception as e:
        log.error("RotoWire failed: %s", e)
        counts['rotowire_lineups'] = None
    try:
        offers = todays_offers()
    except Exception as e:
        log.error("Superbet failed: %s", e)
        counts['superbet_props'] = counts['superbet_game_odds'] = None
        return counts
    props, game_odds = merge_over_under(pd.DataFrame(offers['props'])), pd.DataFrame(offers['game_odds'])
    try:
        props, game_odds = add_model_columns(props, game_odds, lineups)
    except Exception as e:
        # the odds are worth keeping even when the model can't run (e.g. no game logs yet)
        log.error("Pricing failed, saving the odds without picks: %s", e)
    counts['superbet_props'] = _append('superbet_props', props, fetched_at)
    counts['superbet_game_odds'] = _append('superbet_game_odds', game_odds, fetched_at)
    return counts


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--tomorrow', action='store_true', help="RotoWire's lineups for tomorrow")
    args = parser.parse_args()
    for name, n in take_snapshot('tomorrow' if args.tomorrow else 'today').items():
        print(f"{name}: {'failed' if n is None else f'{n} rows'}")
