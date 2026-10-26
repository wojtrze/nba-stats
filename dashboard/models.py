"""The dashboard's two pricing models as plain functions (no Streamlit), shared by the Today's props and Games
pages, daily_snapshot.py (which saves the edges it would have shown) and the results tracker."""
import hashlib
import json
import os
from typing import Callable, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

from espn_scraper import CURRENT_SEASON, NBA_TEAM_ABBRS
from metrics import (IDENTITY_CALIBRATION, POSITION_GROUPS, STATS, absence_adjustments, absence_impact,
                     add_combined_stats, allowed_by_position, blended_ratings, calibrate, context_factor, game_lines,
                     game_projection, hit_rates, line_percentile, market_edges, matchup, no_vig, percentile_band,
                     prop_probability, prop_signal, rotowire_team, team_ratings)
from superbet_fetcher import main_lines

# fitted by backtest/calibrate.py on Unibet's 2022/23 lines and the settled Superbet ones, with the 🟢 threshold;
# without it the model's chances are used as they are
CALIBRATION_FILE = os.path.join('data', 'backtest', 'calibration.json')
# which model priced a line: bump it whenever price_props / price_games change what they return, so a calibration
# is only fitted on (and trusted for) chances of one model (nightly.LINEAGE_COLUMNS, backtest/calibrate.py)
MODEL_VERSION = '2026-10-26-count'   # count distribution in metrics.prop_probability (was '2026-10-26': normal)
# calibration_status: fitted for this model; no file (the raw chances are used); fitted for another model version
FITTED, MISSING, VERSION_MISMATCH, GIVEN = 'fitted', 'missing', 'version mismatch', 'given'
FROM_FILE = object()   # price_props' default green_edge: the one saved in CALIBRATION_FILE

# the sidebar's defaults: the current season, regular season, play-in and playoffs. Preseason is opt-in:
# starters play short minutes in it (2026: 21 min and 12.5 pts, against 33 and 18.4 in the regular season)
DEFAULT_SEASON_TYPES = ['regular', 'playin', 'post']
# the game model uses the current and last season's real games
GAME_TYPES = ['regular', 'playin', 'post']
GAME_DEFAULTS = {'prior_games': 10, 'regress': 0.3, 'home_court': 1.5, 'shrink': 5, 'out_max': 25}
# props: a player with fewer games than this in the season is topped up with his latest games of the season before
TOP_UP_GAMES = 10


def prepare_logs(logs: pd.DataFrame) -> pd.DataFrame:
    """Stored player game logs, NBA teams only, sorted by date, with the derived columns the pages use."""
    logs = logs[logs['team'].isin(NBA_TEAM_ABBRS)].copy()
    logs['Date'] = pd.to_datetime(logs['Date'])
    logs = add_combined_stats(logs).sort_values(['Date', 'game_id']).reset_index(drop=True)
    logs['position_group'] = logs['position'].map(POSITION_GROUPS)
    logs['rest_days'] = logs.groupby('player_id_ESPN')['Date'].diff().dt.days
    logs['game_label'] = logs['Date'].dt.strftime('%m-%d') + ' ' + logs['type'].map({'home': 'vs', 'away': '@'}) + \
        ' ' + logs['OPP']
    return logs


def nba_games(games: pd.DataFrame) -> pd.DataFrame:
    return games[games['home'].isin(NBA_TEAM_ABBRS) & games['away'].isin(NBA_TEAM_ABBRS)]


def top_up_logs(scoped: pd.DataFrame, logs: pd.DataFrame, season: int, players: Iterable,
                min_games: int = TOP_UP_GAMES) -> pd.DataFrame:
    """scoped (prepare_logs rows in the chosen seasons and game types) plus, for each of `players` with fewer than
    min_games games of `season` in it (none counts too: opening night), his latest real games (GAME_TYPES) of
    the season before from `logs`, up to min_games. The added rows have top_up True, the rest False. Nothing is
    added when the season before is already in scoped."""
    scoped = scoped.assign(top_up=False)
    if (scoped['season_id'] == season - 1).any():
        return scoped
    have = scoped[scoped['season_id'] == season].groupby('player_id_ESPN').size()
    need = {p: min_games - have.get(p, 0) for p in set(players) if pd.notna(p) and have.get(p, 0) < min_games}
    prior = logs[(logs['season_id'] == season - 1) & logs['season_type'].isin(GAME_TYPES)
                 & logs['player_id_ESPN'].isin(need)]
    from_last = prior.groupby('player_id_ESPN').cumcount(ascending=False)
    added = prior[from_last < prior['player_id_ESPN'].map(need)]
    if added.empty:
        return scoped
    return (pd.concat([scoped, added.assign(top_up=True)])
            .sort_values(['Date', 'game_id'], kind='stable').reset_index(drop=True))


# --- props ---

def rotowire_status(lineups: pd.DataFrame, player_id, team) -> str:
    """starter / Out 0% / Ques 50% / bench, from RotoWire; empty when RotoWire doesn't list the game."""
    if team not in set(lineups['team']):
        return ''
    listed = lineups[lineups['player_id_ESPN'] == player_id]
    if listed.empty:
        return 'bench'
    p = listed.iloc[0]
    if p['role'] == 'starter':
        return 'starter' + (' ✔' if p['lineup_status'] == 'confirmed' else '')
    return f"{p['injury'] or 'may not play'} {p['play_pct']:.0f}%"


def _calibration_file(path: Optional[str]) -> Optional[Dict]:
    path = path or CALIBRATION_FILE
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def load_calibration(path: Optional[str] = None) -> Dict:
    """The coefficients backtest/calibrate.py fitted (metrics.calibrate), or the identity when there are none."""
    saved = _calibration_file(path)
    return saved['coefficients'] if saved else IDENTITY_CALIBRATION


def calibration_status(path: Optional[str] = None) -> str:
    """FITTED when the calibration file was fitted for MODEL_VERSION, MISSING without one, VERSION_MISMATCH when
    it was fitted for another model (or before versions were saved). Only FITTED chances may give 🟢 / 🟡 picks
    and stakes; the others are for research."""
    saved = _calibration_file(path)
    if not saved:
        return MISSING
    return FITTED if saved.get('model_version') == MODEL_VERSION else VERSION_MISMATCH


def calibration_warning(status: Optional[str] = None) -> str:
    """What the pages say when the chances aren't validated ('' when they are)."""
    status = status or calibration_status()
    if status == MISSING:
        return ("No calibration (data/backtest/calibration.json): model % is the raw model's chance, which was "
                "overconfident on past lines. No 🟢 / 🟡 picks and no stakes until `python -m backtest.calibrate` "
                "has been run.")
    if status == VERSION_MISMATCH:
        return (f"The calibration was fitted for another model version (now {MODEL_VERSION}). No 🟢 / 🟡 picks and "
                "no stakes until it's refitted: `python daily_snapshot.py --reprice`, then `python -m "
                "backtest.calibrate`.")
    return ''


def calibration_id(path: Optional[str] = None) -> str:
    """A short fingerprint of the calibration in use (coefficients, 🟢 threshold, last Superbet night), saved with
    every priced line so a later refit can't pass for the one it was priced with. 'none' without a file."""
    saved = _calibration_file(path)
    if not saved:
        return 'none'
    used = {k: saved.get(k) for k in ('coefficients', 'green_edge_pp', 'superbet_through')}
    return hashlib.sha256(json.dumps(used, sort_keys=True).encode()).hexdigest()[:10]


def load_green_edge(path: Optional[str] = None) -> Optional[float]:
    """The edge (pp) from which a prop gets 🟢: the smallest threshold whose picks paid on unseen Superbet lines
    (backtest/calibrate.py). None = no threshold did, so no 🟢."""
    saved = _calibration_file(path)
    return saved.get('green_edge_pp') if saved else None


# a projection at least this far from the line (log ratio, ~10%) gives the line a lean
LEAN_GAP = 0.10


def lean(proj_avg: pd.Series, line: pd.Series) -> pd.Series:
    """'Over' / 'Under' where the projection is at least LEAN_GAP away from the line, else ''. Information only:
    on its own it hasn't beaten Superbet's prices."""
    gap = np.log((proj_avg.clip(lower=0) + 0.5) / (line + 0.5))
    return pd.Series(np.select([gap >= LEAN_GAP, gap <= -LEAN_GAP], ['Over', 'Under'], ''), index=line.index)


def bet_side(best_side: pd.Series, signal: pd.Series) -> pd.Series:
    """The side to bet: best side where the signal is 🟢 / 🟡, '' (pass) everywhere else."""
    return best_side.where(signal.isin(['🟢', '🟡']), '').fillna('')


def price_props(props: pd.DataFrame, logs: pd.DataFrame, lineups: pd.DataFrame, game_odds: pd.DataFrame,
                games: pd.DataFrame, adjust: Optional[Callable] = None,
                calibration: Optional[Dict] = None, green_edge=FROM_FILE) -> pd.DataFrame:
    """Every Superbet line (props with player_id_ESPN) compared with the player's game logs and priced.

    logs: prepare_logs output in the seasons and game types to use, optionally top_up_logs output (the topped-up
    rows feed the player's own numbers, not the matchup or the absence adjustments); games: games.csv rows of
    the same. adjust(logs, players, out, stats): absence_adjustments, or a cached version of it.
    Adds, per line: the player's numbers (avg, sd, hit rates, percentile...), RotoWire status, lineup adj and adj avg,
    the game context (opponent, spread, implied total, matchup) and proj avg, and the pick: best side (the side
    with the bigger edge, even a negative one), model %, market % (margin-free), break-even %, edge pp, edge low,
    pick odds, signal (metrics.prop_signal with green_edge, default: the one in CALIBRATION_FILE), bet (best side
    when there's a positive edge, else '' = pass) and lean (the projection's side when it's well off the line).
    model %, edge pp and edge low are calibrated (metrics.calibrate with `calibration`, default: the fitted
    coefficients in CALIBRATION_FILE); raw model %, raw over/under % (and their low ends) and market over % are
    the model's own chances before that, which backtest/calibrate.py fits on. calibration: calibration_status, or
    GIVEN for coefficients passed in; unless FITTED or GIVEN no line gets 🟢 / 🟡 or a bet (research only).
    """
    adjust = adjust or absence_adjustments
    # last season's games of a few players would distort opponents' defense and teammates' absence effects
    own = logs[~logs['top_up']] if 'top_up' in logs else logs
    by_player = {pid: g for pid, g in logs.groupby('player_id_ESPN')}
    current_team = logs.groupby('player_id_ESPN')['team'].last()
    position = logs.groupby('player_id_ESPN')['position_group'].last()
    empty = logs.iloc[0:0]

    def assess(row) -> pd.Series:
        games_ = by_player.get(row['player_id_ESPN'], empty)
        values = games_[row['bet_type']] if len(games_) else pd.Series(dtype=float)
        season, last10 = hit_rates(values, row['line']), hit_rates(values.tail(10), row['line'])
        p30, p70 = percentile_band(values) if len(values) else (np.nan, np.nan)
        return pd.Series({
            'player_id': row['player_id_ESPN'], 'team': current_team.get(row['player_id_ESPN']),
            'games': len(values), 'avg': values.mean(), 'sd': values.std(), 'avg L5': values.tail(5).mean(),
            'over %': 100 * season['over'], 'under %': 100 * season['under'],
            'over % L10': 100 * last10['over'], 'under % L10': 100 * last10['under'],
            'percentile': line_percentile(values, row['line']), 'p30': p30, 'p70': p70,
            'min L5': games_['MIN'].tail(5).mean() if len(games_) else np.nan})

    table = pd.concat([props.drop(columns='player_id_ESPN'), props.apply(assess, axis=1)], axis=1)
    table['game'] = table['away'].str.upper() + ' @ ' + table['home'].str.upper()
    table['RotoWire'] = [rotowire_status(lineups, p, t) for p, t in zip(table['player_id'], table['team'])]

    # tonight's absences: each player's usual change when RotoWire's out teammates miss games
    table['lineup adj'] = 0.0
    for team, rows in table.groupby('team'):
        out = rotowire_team(lineups, team)['out']
        players = tuple(sorted(p for p in rows['player_id'].dropna().unique() if p not in out))
        if not out or not players:
            continue
        part = own[own['player_id_ESPN'].isin(set(players) | set(out))]
        adj = adjust(part, players, tuple(sorted(out)), STATS)
        for i, row in rows.iterrows():
            if row['player_id'] in adj.index and row['bet_type'] in adj.columns:
                table.loc[i, 'lineup adj'] = adj.loc[row['player_id'], row['bet_type']]
    table['adj avg'] = table['avg'] + table['lineup adj']

    # the game: Superbet's main handicap and total, and the opponent's defense against the player's position
    lines = game_lines(pd.DataFrame(main_lines(game_odds.to_dict('records')))) if len(game_odds) else pd.DataFrame()
    played = nba_games(games)
    usual = team_ratings(played)['pts'] if len(played) else pd.Series(dtype=float)
    allowed = {}
    context = []
    for _, row in table.iterrows():
        team = row['team']
        known = team in (row['home'], row['away'])
        is_home = team == row['home'] if known else None
        opp = (row['away'] if is_home else row['home']) if known else None
        g = lines.loc[row['event_id']] if row['event_id'] in lines.index else None
        spread = implied = np.nan
        if g is not None and known:
            spread = g['home_spread'] if is_home else -g['home_spread']
            implied = g['home_implied'] if is_home else g['away_implied']
        m = {}
        if opp and row['bet_type'] in own and len(own):
            if row['bet_type'] not in allowed:
                a = allowed_by_position(own, row['bet_type'])
                allowed[row['bet_type']] = a[a.index.isin(NBA_TEAM_ABBRS)]   # preseason guests skew the average
            m = matchup(allowed[row['bet_type']], opp, position.get(row['player_id']))
        team_pts = usual.get(team, np.nan)
        context.append({'is_home': is_home, 'opp': opp, 'spread': spread,
                        'game total': g['total'] if g is not None else np.nan, 'implied': implied,
                        'team_pts': team_pts, 'matchup_info': m, 'matchup': m.get('word', ''),
                        'pace factor': context_factor(implied / team_pts if team_pts else np.nan),
                        'matchup factor': context_factor(m.get('ratio', np.nan))})
    table = table.join(pd.DataFrame(context, index=table.index))
    table['proj avg'] = table['adj avg'] * table['pace factor'] * table['matchup factor']

    coef = load_calibration() if calibration is None else calibration
    status = calibration_status() if calibration is None else GIVEN

    def price(row) -> pd.Series:
        games_ = by_player.get(row['player_id'], empty)
        values = games_[row['bet_type']] if len(games_) else pd.Series(dtype=float)
        market = dict(zip(['Over', 'Under'], no_vig(row['over_odds'], row['under_odds'])))
        best, raw = None, {'market over %': 100 * market['Over']}
        for side, odds in (('Over', row['over_odds']), ('Under', row['under_odds'])):
            if pd.isna(odds):
                continue
            chance = prop_probability(values, row['line'], side, market[side], mean=row['proj avg'])
            raw.update({f'raw {side.lower()} %': 100 * chance['p'], f'raw {side.lower()} low %': 100 * chance['low']})
            p, low = (calibrate(chance[k], market[side], side, coef) for k in ('p', 'low'))
            cand = {'best side': side, 'model %': 100 * p, 'raw model %': 100 * chance['p'],
                    'market %': 100 * market[side], 'break-even %': 100 / odds, 'edge pp': 100 * p - 100 / odds,
                    'edge low': 100 * low - 100 / odds, 'pick odds': odds}
            if best is None or cand['edge pp'] > best['edge pp']:
                best = cand
        best = best or dict.fromkeys(['best side', 'model %', 'raw model %', 'market %', 'break-even %', 'edge pp',
                                      'edge low', 'pick odds'], np.nan)
        return pd.Series(best | raw)

    table = pd.concat([table, table.apply(price, axis=1)], axis=1)
    table['in band'] = (table['p30'] <= table['line']) & (table['line'] <= table['p70'])
    table['calibration'] = status
    table['signal'] = prop_signal(table['edge pp'], load_green_edge() if green_edge is FROM_FILE else green_edge)
    if status not in (FITTED, GIVEN):
        table['signal'] = ''
    table['bet'] = bet_side(table['best side'], table['signal'])
    table['lean'] = lean(table['proj avg'], table['line'])
    return table


# --- games ---

def game_ratings(games: pd.DataFrame, season: int = CURRENT_SEASON, prior_games: float = 10,
                 regress: float = 0.3) -> Dict:
    """blended_ratings of the season and the one before (real games only), and the game counts behind them."""
    real = games[games['season_type'].isin(GAME_TYPES)]
    current, prior = real[real['season_id'] == season], real[real['season_id'] == season - 1]
    return {'ratings': blended_ratings(current, prior, prior_games, regress), 'games': real,
            'current': len(current), 'prior': len(prior)}


def price_games(odds: pd.DataFrame, ratings: pd.DataFrame, lineups: pd.DataFrame, games: pd.DataFrame,
                logs: pd.DataFrame, home_court: float = 1.5, shrink: float = 5, out_max: int = 25,
                all_lines: bool = False, impact: Optional[Callable] = None) -> List[Dict]:
    """Per Superbet event: the projection (ratings, home court, RotoWire's out players) and every outcome's
    edge. Returns dicts with event_id, home, away, start_time, projection, edges (market_edges of the main lines,
    or of every line with all_lines) and absences ({team: [(player_id, absence_impact)]}). Events with a team the
    ratings don't know are skipped.

    impact(team, player_id, shrink): absence_impact on games and logs, or a cached version of it."""
    impact = impact or (lambda team, player_id, shrink_: absence_impact(games, logs, team, player_id, shrink_))
    priced = []
    for event_id, game_odds in odds.groupby('event_id', sort=False):
        home, away = game_odds['home'].iloc[0], game_odds['away'].iloc[0]
        if home not in ratings.index or away not in ratings.index:
            continue
        absences = {team: [(p, impact(team, p, shrink)) for p in rotowire_team(lineups, team, out_max)['out']]
                    for team in (home, away)}
        projection = game_projection(ratings, home, away, home_court,
                                     [imp for _, imp in absences[home]], [imp for _, imp in absences[away]])
        shown = game_odds if all_lines else pd.DataFrame(main_lines(game_odds.to_dict('records')))
        priced.append({'event_id': event_id, 'home': home, 'away': away,
                       'start_time': game_odds['start_time'].iloc[0], 'projection': projection,
                       'edges': market_edges(projection, shown), 'absences': absences})
    return priced
