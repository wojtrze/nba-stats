"""Save today's RotoWire lineups and Superbet offers to data/<season>/ so lines and statuses can be checked later.

    python daily_snapshot.py              # today's games
    python daily_snapshot.py --tomorrow   # RotoWire's lineups for tomorrow (Superbet always covers the next 36h)
    python daily_snapshot.py --reprice    # price every saved line again after a model change (to a replay file)

Each run appends rows with a fetched_at timestamp (UTC), so running it several times a day keeps line movement
and lineup changes. Each line also gets the dashboard's pick and edge at that moment (the default settings of
Today's props and Games), so the Results tracker settles exactly what the pages showed, with the model version
and calibration that priced it (nightly.LINEAGE_COLUMNS). Saved rows are never priced again in place.
"""
import argparse
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd

from espn_scraper import CURRENT_SEASON, SEASONS
from espn_scraper.storage import load_games, load_player_gamelogs, read_snapshot, snapshot_file
from safe_io import append_csv, atomic_to_csv, atomic_write_text, locked

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
    """Append df to a snapshot file with fetched_at first, under the file's lock and atomically (safe_io)."""
    if df.empty:
        return 0
    path = snapshot_file(CURRENT_SEASON, name)
    df.insert(0, 'fetched_at', fetched_at)
    with locked(path):
        if os.path.exists(path):
            # keep the file's column order; new columns go at the end
            existing = list(pd.read_csv(path, nrows=0).columns)
            if set(df.columns) - set(existing):
                # as text, so the saved rows are written back unchanged (ids with gaps would otherwise become floats)
                old = pd.read_csv(path, dtype=str, keep_default_na=False)
                atomic_to_csv(pd.concat([old, df], ignore_index=True), path)
                return len(df)
        return append_csv(df, path)


# --- Superbet blocks frequent requests: one shared cooldown for the dashboards and the scheduled runs ---

SUPERBET_COOLDOWN = timedelta(minutes=5)
CONTACT_FILE = os.path.join('data', 'superbet_contact.txt')


def last_superbet_contact() -> Optional[datetime]:
    """When any process last contacted Superbet (a dashboard fetch or a snapshot run), from CONTACT_FILE."""
    try:
        with open(CONTACT_FILE, encoding='utf-8') as f:
            return datetime.fromisoformat(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None


def superbet_wait(now: Optional[datetime] = None) -> Optional[timedelta]:
    """How long until Superbet may be contacted again; None = now."""
    last = last_superbet_contact()
    left = last + SUPERBET_COOLDOWN - (now or datetime.now(timezone.utc)) if last else None
    return left if left and left > timedelta(0) else None


def claim_superbet() -> Optional[timedelta]:
    """Record a contact now unless one was made within SUPERBET_COOLDOWN, checked and written under one lock so
    two processes can't both go ahead. None = claimed (go ahead); otherwise how long to wait."""
    with locked(CONTACT_FILE):
        wait = superbet_wait()
        if wait:
            return wait
        atomic_write_text(CONTACT_FILE, datetime.now(timezone.utc).isoformat() + '\n')
        return None


# --- RotoWire: the dashboards save every fetch that differs from the last saved version of that day ---

# what lineup_fetcher.fetch_lineups returns, as saved (the ESPN ids are added when the dashboards read it)
LINEUP_COLUMNS = ['game_date', 'tip_et', 'away', 'home', 'team', 'side', 'lineup_status', 'role', 'pos', 'name',
                  'rotowire_id', 'play_pct', 'injury']
_PLAYER_KEY = ['game_date', 'team', 'name']
_PLAYER_FIELDS = ['role', 'pos', 'play_pct', 'injury']


def _as_text(df: pd.DataFrame) -> pd.DataFrame:
    """Rows comparable between a fresh fetch and a saved one (read back from CSV): every value as text."""
    out = df.reindex(columns=LINEUP_COLUMNS).copy()
    out['play_pct'] = pd.to_numeric(out['play_pct'], errors='coerce').map(lambda v: '' if pd.isna(v) else f"{v:.0f}")
    return out.astype(object).where(out.notna(), '').astype(str).replace({'nan': '', 'None': ''})


def _status(row) -> str:
    """'starter', 'Out 0%', 'Ques 50%'."""
    if row['role'] == 'starter':
        return 'starter'
    return f"{row['injury'] or 'may not play'} {row['play_pct']}%".strip() if row['play_pct'] else \
        (row['injury'] or row['role'])


def lineup_changes(old: pd.DataFrame, new: pd.DataFrame) -> list:
    """What changed between two versions of RotoWire's page, in words: lineups confirmed (or back to expected),
    players whose role, chance to play or injury changed, players newly listed or no longer listed."""
    old, new = _as_text(old), _as_text(new)
    changes = []
    old_status = old.drop_duplicates('team').set_index('team')['lineup_status']
    for team, status in new.drop_duplicates('team').set_index('team')['lineup_status'].items():
        if team in old_status.index and old_status[team] != status and status:
            changes.append(f"{team.upper()} lineup {status}")
    before = old.drop_duplicates(_PLAYER_KEY).set_index(_PLAYER_KEY)
    after = new.drop_duplicates(_PLAYER_KEY).set_index(_PLAYER_KEY)
    for key in after.index:
        name, team = key[2], key[1].upper()
        if key not in before.index:
            changes.append(f"new: {name} ({team}, {_status(after.loc[key])})")
        elif any(before.loc[key, f] != after.loc[key, f] for f in _PLAYER_FIELDS):
            changes.append(f"{name} ({team}): {_status(before.loc[key])} → {_status(after.loc[key])}")
    changes += [f"no longer listed: {key[2]} ({key[1].upper()})" for key in before.index if key not in after.index]
    return changes


def save_lineups_if_changed(lineups: pd.DataFrame, fetched_at: str) -> str:
    """Append a RotoWire fetch to rotowire_lineups.csv when it's the first of its day (game_date) or differs
    from the last saved version of that day. Returns what was saved ('' when nothing was)."""
    if lineups.empty:
        return ''
    path = snapshot_file(CURRENT_SEASON, 'rotowire_lineups')
    with locked(path):      # two dashboards seeing the same change save it once
        saved = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame(columns=['fetched_at'] + LINEUP_COLUMNS)
        days = set(lineups['game_date'].astype(str))
        same_day = saved[saved['game_date'].astype(str).isin(days)]
        last = same_day[same_day['fetched_at'] == same_day['fetched_at'].max()] if len(same_day) else same_day
        changes = lineup_changes(last, lineups) if len(last) else None
        if changes == []:
            return ''
        _append('rotowire_lineups', lineups.reindex(columns=LINEUP_COLUMNS).copy(), fetched_at)
    when = ', '.join(f"{pd.Timestamp(d):%b %d}" for d in sorted(days))
    if changes is None:
        return f"saved {len(lineups)} players for {when} (first fetch of the day)"
    shown = '; '.join(changes[:3]) + (f"; …and {len(changes) - 3} more" if len(changes) > 3 else '')
    return f"saved {len(lineups)} players for {when}: {len(changes)} change{'s' * (len(changes) > 1)} – {shown}"


def add_model_columns(props: pd.DataFrame, game_odds: pd.DataFrame, lineups: pd.DataFrame):
    """props with player_id_ESPN and nightly.MODEL_COLUMNS (pick, model_pct, edge_pp, edge_low, proj_avg, signal
    🟢/🟡/🔴, red_flag and the raw chances the calibration is refit from); game_odds with model_pct, edge_pp and
    the game's projected score (proj_home_pts, proj_away_pts). Same models and defaults as the dashboard pages
    (current season without preseason, players with few games topped up with last season's)."""
    from models import (DEFAULT_SEASON_TYPES, GAME_DEFAULTS, GAME_TYPES, game_ratings, prepare_logs, price_games,
                        price_props, top_up_logs)
    from name_resolver import NameResolver
    from decisions import game_decisions, shortlist, team_decision
    from metrics import ACTIVE_PROFILE
    from models import calibration_status
    from nightly import DECISION_COLUMN, MODEL_VERSION, RECORDED_LIVE, SHORTLIST_COLUMNS, lineage, model_columns
    from tracking import PROP_KEY
    from reasons import flag_props

    logs = prepare_logs(load_player_gamelogs(sorted(SEASONS)))
    games = load_games(sorted(SEASONS))
    # once a newer night has settled, the calibration and 🟢 threshold are refitted with its lines first
    from backtest.calibrate import refresh
    refresh(logs, games)
    resolver = NameResolver(logs)
    if not lineups.empty:
        lineups = resolver.add_ids(lineups)
    if not props.empty:
        props = resolver.add_ids(props, team_cols=('home', 'away'))
        current = top_up_logs(logs[(logs['season_id'] == CURRENT_SEASON) & logs['season_type'].isin(DEFAULT_SEASON_TYPES)],
                              logs, CURRENT_SEASON, props['player_id_ESPN'].dropna().unique())
        played = games[(games['season_id'] == CURRENT_SEASON) & games['season_type'].isin(DEFAULT_SEASON_TYPES)]
        # the red flags known at fetch time (the line hasn't moved yet)
        table = flag_props(price_props(props, current, lineups, game_odds, played), current, lineups)
        # the decision for each game's players as of this fetch (decisions.py): what the pages show now
        now = pd.Timestamp.now(tz='UTC')
        decided = game_decisions(table, calibration_status(), lineups, now, now)
        # where each line stood in the night's shortlist, so it's settled as shown before the game
        ranked = shortlist(table, decided)[PROP_KEY + ['tier', 'rank']].rename(columns={'rank': 'night_rank'})
        listed = table[PROP_KEY].merge(ranked, on=PROP_KEY, how='left').set_axis(table.index)
        props = props.assign(**model_columns(table), **lineage(RECORDED_LIVE),
                             **{DECISION_COLUMN: table['event_id'].map(lambda e: decided[e]['status'])},
                             **{c: listed[c] for c in SHORTLIST_COLUMNS})
        props['tier'] = props['tier'].fillna('')
        props['night_rank'] = props['night_rank'].astype('Int64')
    if not game_odds.empty:
        model = game_ratings(games, CURRENT_SEASON, GAME_DEFAULTS['prior_games'], GAME_DEFAULTS['regress'])
        recent = logs[logs['season_id'].isin([CURRENT_SEASON - 1, CURRENT_SEASON]) & logs['season_type'].isin(GAME_TYPES)]
        priced = price_games(game_odds, model['ratings'], lineups, model['games'], recent, GAME_DEFAULTS['home_court'],
                             GAME_DEFAULTS['shrink'], GAME_DEFAULTS['out_max'], all_lines=True)
        if priced:
            edges = pd.concat([g['edges'] for g in priced])[['event_id', 'market', 'side', 'line', 'model %', 'edge pp',
                                                             'ev net 100']]
            game_odds = game_odds.merge(edges.rename(columns={'model %': 'model_pct', 'edge pp': 'edge_pp',
                                                              'ev net 100': 'ev_net_100'}).round(1),
                                        on=['event_id', 'market', 'side', 'line'], how='left')                 .assign(cost_profile=ACTIVE_PROFILE, decision=team_decision()['status'])
            projected = pd.DataFrame([{'event_id': g['event_id'],
                                       'proj_home_pts': round(g['projection']['home_pts'], 1),
                                       'proj_away_pts': round(g['projection']['away_pts'], 1)} for g in priced])
            game_odds = game_odds.merge(projected, on='event_id', how='left') \
                .assign(model_version=MODEL_VERSION, prediction_origin=RECORDED_LIVE)
    return props, game_odds


def take_snapshot(date: str = 'today') -> dict:
    """Fetch both sources and append them. A source that fails is reported and skipped. Superbet is skipped too
    when any process (a dashboard, another run) contacted it within SUPERBET_COOLDOWN: that fetch is saved."""
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
    wait = claim_superbet()
    if wait:
        log.warning("Superbet was contacted %.0f s ago by another run: not fetched again (that fetch is saved)",
                    (SUPERBET_COOLDOWN - wait).total_seconds())
        counts['superbet_props'] = counts['superbet_game_odds'] = None
        return counts
    try:
        offers = todays_offers()
    except Exception as e:
        log.error("Superbet failed: %s", e)
        counts['superbet_props'] = counts['superbet_game_odds'] = None
        return counts
    return counts | save_superbet(offers, lineups, fetched_at)


def save_superbet(offers: dict, lineups: pd.DataFrame, fetched_at: str) -> dict:
    """Append one Superbet fetch (superbet_fetcher.todays_offers output) to the snapshot files, each line with the
    dashboard's pick and edge. The dashboards save every on-demand fetch through this too."""
    props, game_odds = merge_over_under(pd.DataFrame(offers['props'])), pd.DataFrame(offers['game_odds'])
    try:
        props, game_odds = add_model_columns(props, game_odds, lineups)
    except Exception as e:
        # the odds are worth keeping even when the model can't run (e.g. no game logs yet)
        log.error("Pricing failed, saving the odds without picks: %s", e)
    return {'superbet_props': _append('superbet_props', props, fetched_at),
            'superbet_game_odds': _append('superbet_game_odds', game_odds, fetched_at)}


def reprice_snapshots() -> int:
    """Price every saved Superbet line again with the current model and defaults, as of its fetch: the games
    finished before that day, the RotoWire version saved by then and the game odds of the same fetch
    (nightly.recompute_props). Writes them to superbet_props_replay.csv (the saved lines with the new model
    columns, prediction_origin historical_replay), replacing that file's rows of the current MODEL_VERSION and
    keeping other versions'; superbet_props.csv, the record of what each fetch showed, is left as it is. Returns
    the rows of the current version."""
    from models import prepare_logs
    from name_resolver import NameResolver
    from nightly import (DECISION_COLUMN, HISTORICAL_REPLAY, LINEAGE_COLUMNS, MODEL_COLUMNS, MODEL_VERSION,
                         SHORTLIST_COLUMNS, et_night, lineage, lineups_before_tip, recompute_props)

    path = snapshot_file(CURRENT_SEASON, 'superbet_props')
    model_cols = ['player_id_ESPN', *MODEL_COLUMNS, DECISION_COLUMN, *SHORTLIST_COLUMNS, *LINEAGE_COLUMNS]
    saved = pd.read_csv(path, dtype=str, keep_default_na=False).drop(columns=model_cols, errors='ignore')
    props = read_snapshot(path).drop(columns=model_cols, errors='ignore')
    odds = read_snapshot(snapshot_file(CURRENT_SEASON, 'superbet_game_odds'))
    rotowire = pd.read_csv(snapshot_file(CURRENT_SEASON, 'rotowire_lineups'))
    logs = prepare_logs(load_player_gamelogs(sorted(SEASONS)))
    games = load_games(sorted(SEASONS))
    resolver = NameResolver(logs)
    props = resolver.add_ids(props, team_cols=('home', 'away'))
    rotowire = resolver.add_ids(rotowire)

    model = pd.DataFrame(index=props.index, columns=MODEL_COLUMNS, dtype=object)
    for (fetched_at, night), rows in props.groupby(['fetched_at', et_night(props['start_time'])]):
        lineups = lineups_before_tip(rotowire, night, pd.Timestamp(fetched_at) + pd.Timedelta(seconds=1))
        priced = recompute_props(rows, logs, games, lineups, odds[odds['fetched_at'] == fetched_at],
                                 et_night(pd.Series([fetched_at])).iloc[0])
        model.loc[rows.index] = priced[MODEL_COLUMNS].values
        log.info("%s, games of %s: %d lines priced", fetched_at, night.date(), len(rows))

    out = saved.assign(player_id_ESPN=pd.array(props['player_id_ESPN'], dtype='Int64'))
    for col in MODEL_COLUMNS:
        out[col] = model[col].values
    out = out.assign(**lineage(HISTORICAL_REPLAY))
    # one block per model version, so several models can be compared on the same lines; this one's is replaced
    replay = snapshot_file(CURRENT_SEASON, 'superbet_props_replay')
    if os.path.exists(replay):
        others = pd.read_csv(replay, dtype=str, keep_default_na=False)
        others = others[others['model_version'] != MODEL_VERSION]
        out = pd.concat([others, out.astype(str).replace({'<NA>': '', 'nan': ''})], ignore_index=True)
    atomic_to_csv(out, replay)
    return int((out['model_version'] == MODEL_VERSION).sum())


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--tomorrow', action='store_true', help="RotoWire's lineups for tomorrow")
    parser.add_argument('--reprice', action='store_true',
                        help="price every saved Superbet line again with the current model, into "
                             "superbet_props_replay.csv")
    args = parser.parse_args()
    if args.reprice:
        print(f"superbet_props_replay: {reprice_snapshots()} rows repriced (superbet_props.csv unchanged)")
        sys.exit()
    for name, n in take_snapshot('tomorrow' if args.tomorrow else 'today').items():
        print(f"{name}: {'failed' if n is None else f'{n} rows'}")
