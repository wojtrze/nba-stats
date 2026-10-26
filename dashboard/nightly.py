"""A night's lines and games against what the dashboard projected before tip-off (no Streamlit, tested in
test_nightly.py). Both dashboards' "previous night" views are built on it.

A line is judged by its last saved fetch before tip-off (the final projection); its first one gives the opening
line and the pick at the open. Nights are US-Eastern dates, as the stored stats use.
"""
from typing import Callable, Dict, Optional

import numpy as np
import pandas as pd

from tracking import GAME_KEY, PROP_KEY, edge_signal, settle_games, settle_props

ET = 'US/Eastern'


def et_night(start_time: pd.Series) -> pd.Series:
    """The game's US-Eastern date (tip-off times are UTC)."""
    return pd.to_datetime(start_time, utc=True).dt.tz_convert(ET).dt.tz_localize(None).dt.normalize()


def pre_tip(snapshots: pd.DataFrame, night) -> pd.DataFrame:
    """The night's rows saved before their game's tip-off, oldest fetch first."""
    if snapshots.empty:
        return snapshots
    rows = snapshots[et_night(snapshots['start_time']) == pd.Timestamp(night)]
    fetched = pd.to_datetime(rows['fetched_at'], utc=True)
    return rows[fetched < pd.to_datetime(rows['start_time'], utc=True)].sort_values('fetched_at', kind='stable')


def nights(prop_snapshots: pd.DataFrame, games: pd.DataFrame, now) -> pd.DataFrame:
    """Nights with saved lines whose first game has tipped off, newest first: night, games, lines and settled (the
    stored stats hold that night's games)."""
    if prop_snapshots.empty:
        return pd.DataFrame(columns=['night', 'games', 'lines', 'settled'])
    rows = prop_snapshots.assign(night=et_night(prop_snapshots['start_time']),
                                 tip=pd.to_datetime(prop_snapshots['start_time'], utc=True))
    started = rows.groupby('night')['tip'].min() <= pd.Timestamp(now)
    stored = set(pd.to_datetime(games['date']).dt.normalize()) if len(games) else set()
    out = rows.groupby('night').agg(games=('event_id', 'nunique'),
                                    lines=('event_id', lambda s: len(rows.loc[s.index].drop_duplicates(PROP_KEY))))
    out = out[started.reindex(out.index, fill_value=False)].reset_index()
    out['settled'] = out['night'].isin(stored)
    return out.sort_values('night', ascending=False).reset_index(drop=True)


# the model's numbers saved with each line (daily_snapshot.py); the raw chances let backtest/calibrate.py refit
# the calibration from the settled lines without pricing them again
MODEL_COLUMNS = ['pick', 'model_pct', 'edge_pp', 'edge_low', 'proj_avg', 'signal', 'red_flag',
                 'raw_over_pct', 'raw_under_pct', 'market_over_pct']

# which model priced a saved line: bump MODEL_VERSION whenever price_props / price_games change what they return,
# so a calibration is only fitted on (and applied to) chances of one model. calibration_id: models.calibration_id
# at pricing time. prediction_origin: recorded_live = saved by the fetch itself, historical_replay = priced later
# as of the fetch (daily_snapshot.py --reprice, kept in its own file). Rows saved before Oct 26 leave them empty.
MODEL_VERSION = '2026-10-26'
LINEAGE_COLUMNS = ['model_version', 'calibration_id', 'prediction_origin']
RECORDED_LIVE, HISTORICAL_REPLAY = 'recorded_live', 'historical_replay'


def lineage(origin: str) -> Dict[str, str]:
    """LINEAGE_COLUMNS for lines priced now with the current model and calibration."""
    from models import calibration_id
    return {'model_version': MODEL_VERSION, 'calibration_id': calibration_id(), 'prediction_origin': origin}


def night_props(snapshots: pd.DataFrame, logs: pd.DataFrame, games: pd.DataFrame, night,
                recompute: Optional[Callable[[pd.DataFrame], pd.DataFrame]] = None) -> pd.DataFrame:
    """Every prop line of the night, judged by its last fetch before tip-off: tracking.settle_props columns (pick,
    odds, model_pct, edge_pp, actual, status, result, profit...) plus proj_avg, signal (saved, else from the
    edges), red_flag, open line / pick at open (the first fetch), proj error (actual − proj_avg), line error
    (actual − line), closer than line (|actual − proj_avg| < |actual − line|), pick changed, over_odds /
    under_odds, the player's position, team and venue (home / away), and recomputed.
    Lines whose fetch was saved without the model's numbers (before Oct 21) get them from recompute(those last
    rows), which returns MODEL_COLUMNS on the same index (recompute_props); recomputed marks them."""
    rows = pre_tip(snapshots, night)
    if rows.empty:
        return pd.DataFrame()
    last = rows.drop_duplicates(PROP_KEY, keep='last').reset_index(drop=True)
    first = rows.drop_duplicates(PROP_KEY, keep='first').set_index(PROP_KEY)
    for col in MODEL_COLUMNS:
        if col not in last:
            last[col] = np.nan
    last[MODEL_COLUMNS] = last[MODEL_COLUMNS].astype(object)
    missing = last['pick'].isna()
    if recompute is not None and missing.any():
        filled = recompute(last[missing])
        for col in MODEL_COLUMNS:
            if col in filled:
                last.loc[missing, col] = filled[col]
    for col in ['model_pct', 'edge_pp', 'edge_low', 'proj_avg']:
        last[col] = pd.to_numeric(last[col], errors='coerce')
    out = settle_props(snapshots, logs, games, bets=last)
    assert len(out) == len(last)   # settle_props keeps the order of the bets it's given
    for col in ['proj_avg', 'edge_low', 'signal', 'red_flag', 'event_id', 'name_ESPN', 'fetched_at', 'over_odds',
                'under_odds', 'home', 'away']:
        out[col] = last[col].values if col in last else np.nan
    out['recomputed'] = (missing & last['pick'].notna()).values
    saved = out['signal'].astype(object).where(out['signal'].notna(), None)
    out['signal'] = saved.where(saved.notna(), edge_signal(out['edge_pp'])).fillna('')
    out['red_flag'] = out['red_flag'].fillna('')
    keys = list(zip(*(last[k] for k in PROP_KEY)))
    out['open line'] = [first.loc[k, 'line'] for k in keys]
    out['pick at open'] = [first.loc[k, 'pick'] if 'pick' in first else np.nan for k in keys]
    out['fetches'] = rows.groupby(PROP_KEY).size().reindex(keys).values
    settled = out['status'] == 'settled'
    out['proj error'] = (out['actual'] - out['proj_avg']).where(settled)
    out['line error'] = (out['actual'] - out['line']).where(settled)
    out['closer than line'] = ((out['proj error'].abs() < out['line error'].abs())
                               .where(settled & out['proj_avg'].notna()))
    out['pick changed'] = (out['pick at open'].notna() & out['pick'].notna() & (out['pick at open'] != out['pick']))
    return out.assign(**_player_context(out, logs, night))


def _player_context(lines: pd.DataFrame, logs: pd.DataFrame, night) -> Dict[str, pd.Series]:
    """Each line's player position (G / F / C), team (that night's, else the latest before it) and venue."""
    played = logs[logs['Date'] <= pd.Timestamp(night)].sort_values('Date')
    latest = played.drop_duplicates('player_id_ESPN', keep='last').set_index('player_id_ESPN')
    pid = pd.to_numeric(lines['player_id'], errors='coerce')
    column = lambda c: pid.map(latest[c]) if c in latest and len(latest) else pd.Series(np.nan, index=lines.index)
    team, position = column('team'), column('position_group')
    venue = np.select([team == lines['home'], team == lines['away']], ['home', 'away'], '')
    return {'position': position.fillna(''), 'team': team.fillna('').str.upper(),
            'venue': pd.Series(venue, index=lines.index)}


def recompute_props(rows: pd.DataFrame, logs: pd.DataFrame, games: pd.DataFrame, lineups: pd.DataFrame,
                    game_odds: pd.DataFrame, night) -> pd.DataFrame:
    """The model's numbers for saved lines (with player_id_ESPN) as the dashboard would have shown them before
    that night: models.price_props on that season's games before the night (the default game types, topped up
    with the season before's), the lineups and game odds saved before tip-off, then reasons.flag_props.
    MODEL_COLUMNS on rows' index."""
    from models import DEFAULT_SEASON_TYPES, price_props, top_up_logs
    from reasons import flag_props
    night = pd.Timestamp(night)
    before = logs[logs['Date'] < night]
    season = before['season_id'].max()
    scope = top_up_logs(before[(before['season_id'] == season) & before['season_type'].isin(DEFAULT_SEASON_TYPES)],
                        before, season, rows['player_id_ESPN'].dropna().unique())
    played = games[(pd.to_datetime(games['date']) < night) & (games['season_id'] == season)
                   & games['season_type'].isin(DEFAULT_SEASON_TYPES)]
    lines = rows[['name', 'name_ESPN', 'home', 'away', 'bet_type', 'line', 'event_id', 'start_time', 'over_odds',
                  'under_odds', 'player_id_ESPN']]
    table = flag_props(price_props(lines, scope, lineups, game_odds, played), scope, lineups)
    return model_columns(table).set_axis(rows.index)


def model_columns(table: pd.DataFrame) -> pd.DataFrame:
    """MODEL_COLUMNS from price_props + flag_props output, rounded as saved. pick is the best side even without an
    edge (so every line can be judged); the dashboards' bet is pick where the signal is 🟢 / 🟡."""
    return pd.DataFrame({'pick': table['best side'], 'model_pct': table['model %'].round(1),
                         'edge_pp': table['edge pp'].round(1), 'edge_low': table['edge low'].round(1),
                         'proj_avg': table['proj avg'].round(2), 'signal': table['signal'],
                         'red_flag': table['red flag'], 'raw_over_pct': table['raw over %'].round(2),
                         'raw_under_pct': table['raw under %'].round(2),
                         'market_over_pct': table['market over %'].round(2)}, index=table.index)[MODEL_COLUMNS]


# what the group analysis can split the lines by
GROUP_AXES = {'bet_type': "Stat", 'position': "Position", 'venue': "Home / away", 'pick': "Our pick (Over / Under)",
              'signal': "Signal", 'team': "Team", 'game': "Game"}


def group_outcomes(props: pd.DataFrame, by, min_lines: int = 1) -> pd.DataFrame:
    """For each group of settled lines: how often betting Over and betting Under won and paid (1 unit at the
    line's odds; pushes left out), how our picks did, and the better side with its hit rate's 95% range. Sorted by
    the better side's hit rate, so the groups where a bet was most likely to win come first."""
    from metrics import wilson_interval
    by = [by] if isinstance(by, str) else list(by)
    settled = props[(props['status'] == 'settled') & (props['actual'] != props['line'])]
    rows = []
    for key, part in settled.groupby(by, dropna=False):
        over_won = part['actual'] > part['line']
        n, wins = len(part), int(over_won.sum())
        sides = {'Over': (wins, 100 * np.mean(np.where(over_won, part['over_odds'] - 1, -1.0))),
                 'Under': (n - wins, 100 * np.mean(np.where(~over_won, part['under_odds'] - 1, -1.0)))}
        best = 'Over' if wins >= n - wins else 'Under'
        low, high = wilson_interval(sides[best][0], n)
        picks = part[part['result'].isin(['win', 'loss'])]
        row = dict(zip(by, key if isinstance(key, tuple) else (key,)))
        row.update({'lines': n, 'over %': 100 * wins / n, 'over ROI %': sides['Over'][1],
                    'under %': 100 * (n - wins) / n, 'under ROI %': sides['Under'][1], 'best side': best,
                    'best side %': 100 * sides[best][0] / n, 'ci low %': 100 * low, 'ci high %': 100 * high,
                    'best side ROI %': sides[best][1], 'our picks': len(picks),
                    'our hit %': 100 * (picks['result'] == 'win').mean() if len(picks) else np.nan,
                    'our ROI %': 100 * picks['profit'].mean() if len(picks) else np.nan})
        rows.append(row)
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out = out[out['lines'] >= min_lines]
    return out.sort_values(['best side %', 'lines'], ascending=False).reset_index(drop=True)


def night_games(snapshots: pd.DataFrame, games: pd.DataFrame, night,
                recompute: Optional[Callable[[pd.DataFrame], Optional[Dict]]] = None) -> Dict[str, pd.DataFrame]:
    """The night's games against the projection: 'games' (one row per game: projected and actual score, winner
    called, margin and total errors, the best market outcome and its result, recomputed) and 'outcomes' (every
    market outcome, judged by its last fetch before tip-off, settled with tracking.settle_games).
    The projected score comes from the saved proj_home_pts / proj_away_pts; for fetches saved before those
    existed, recompute(the event's last odds rows) returns {'home_pts', 'away_pts'} (or None)."""
    rows = pre_tip(snapshots, night)
    if rows.empty:
        return {'games': pd.DataFrame(), 'outcomes': pd.DataFrame()}
    last = rows.drop_duplicates(GAME_KEY, keep='last').reset_index(drop=True)
    outcomes = settle_games(snapshots, games, bets=last)
    outcomes['event_id'] = last['event_id'].values
    finals = games.assign(night=pd.to_datetime(games['date']).dt.normalize())
    finals = finals[finals['night'] == pd.Timestamp(night)].set_index(['home', 'away'])
    out = []
    for event_id, event in rows.groupby('event_id', sort=False):
        latest = event[event['fetched_at'] == event['fetched_at'].max()]
        home, away = latest['home'].iloc[0], latest['away'].iloc[0]
        saved = 'proj_home_pts' in latest and latest['proj_home_pts'].notna().any()
        projection = {'home_pts': latest['proj_home_pts'].dropna().iloc[0],
                      'away_pts': latest['proj_away_pts'].dropna().iloc[0]} if saved else \
            (recompute(latest) if recompute else None)
        final = finals.loc[(home, away)] if (home, away) in finals.index else None
        mine = outcomes[outcomes['event_id'] == event_id]
        best = mine.loc[mine['edge_pp'].idxmax()] if mine['edge_pp'].notna().any() else None
        row = {'event_id': event_id, 'game': f"{away.upper()} @ {home.upper()}", 'home': home, 'away': away,
               'start_time': latest['start_time'].iloc[0], 'recomputed': projection is not None and not saved,
               'proj home': np.nan, 'proj away': np.nan, 'home score': np.nan, 'away score': np.nan,
               'best bet': None if best is None else _outcome_text(best),
               'best edge pp': np.nan if best is None else best['edge_pp'],
               'best result': None if best is None else best['result']}
        if projection is not None:
            row['proj home'], row['proj away'] = projection['home_pts'], projection['away_pts']
        if final is not None:
            row['home score'], row['away score'] = final['home_score'], final['away_score']
        out.append(row)
    g = pd.DataFrame(out)
    g['proj winner'] = np.where(g['proj home'] >= g['proj away'], g['home'], g['away'])
    g['winner'] = np.where(g['home score'] > g['away score'], g['home'], g['away'])
    known = g['proj home'].notna() & g['home score'].notna()
    g['winner called'] = (g['proj winner'] == g['winner']).where(known)
    g['margin error'] = ((g['home score'] - g['away score']) - (g['proj home'] - g['proj away'])).where(known)
    g['total error'] = ((g['home score'] + g['away score']) - (g['proj home'] + g['proj away'])).where(known)
    for col in ['winner', 'proj winner']:
        g[col] = g[col].where(known).str.upper()
    return {'games': g.sort_values('start_time').reset_index(drop=True), 'outcomes': outcomes}


def lineups_before_tip(rotowire_snapshots: pd.DataFrame, night, start_time) -> pd.DataFrame:
    """The last RotoWire version of that night saved before the game's tip-off (what the projection would have
    used); empty when none was saved."""
    if rotowire_snapshots.empty:
        return rotowire_snapshots
    rows = rotowire_snapshots[(pd.to_datetime(rotowire_snapshots['game_date']) == pd.Timestamp(night))
                              & (pd.to_datetime(rotowire_snapshots['fetched_at'], utc=True)
                                 < pd.to_datetime(start_time, utc=True))]
    return rows[rows['fetched_at'] == rows['fetched_at'].max()] if len(rows) else rows


def recompute_projection(event_odds: pd.DataFrame, games: pd.DataFrame, logs: pd.DataFrame,
                         lineups: pd.DataFrame, night) -> Optional[Dict]:
    """The game projection as the dashboard would have made it before that night: ratings from the games played
    before it, absences from `lineups` (lineups_before_tip, with ESPN ids), the dashboard's default settings.
    event_odds: the event's saved odds rows. {'home_pts', 'away_pts', ...} or None."""
    from models import GAME_DEFAULTS, GAME_TYPES, game_ratings, price_games
    night = pd.Timestamp(night)
    before = games[pd.to_datetime(games['date']) < night]
    if before.empty:
        return None
    season = int(before.sort_values('date')['season_id'].iloc[-1])
    model = game_ratings(before, season, GAME_DEFAULTS['prior_games'], GAME_DEFAULTS['regress'])
    recent = logs[logs['season_id'].isin([season - 1, season]) & logs['season_type'].isin(GAME_TYPES)
                  & (logs['Date'] < night)]
    priced = price_games(event_odds, model['ratings'], lineups, model['games'], recent, GAME_DEFAULTS['home_court'],
                         GAME_DEFAULTS['shrink'], GAME_DEFAULTS['out_max'])
    return priced[0]['projection'] if priced else None


def _outcome_text(o) -> str:
    """'ML BOS', 'SPREAD DET +1.5', 'TOTAL over 220.5'."""
    who = str(o['team']).upper() if o['market'] in ('ML', 'SPREAD') else o['side']
    line = '' if pd.isna(o['line']) else f" {o['line']:+g}" if o['market'] == 'SPREAD' else f" {o['line']:g}"
    return f"{o['market']} {who}{line}"


def _rate(part: pd.DataFrame) -> Dict:
    decided = part[part['result'].isin(['win', 'loss'])]
    n = len(decided)
    return {'picks': n, 'hit %': 100 * (decided['result'] == 'win').mean() if n else np.nan,
            'ROI %': 100 * decided['profit'].mean() if n else np.nan}


def night_summary(props: pd.DataFrame, games: Dict[str, pd.DataFrame]) -> Dict:
    """The night in numbers: how many lines settled, how the picks did (all, 🟢🟡, 🔴, no signal), how close the
    projected averages were compared with the lines, and how the game projections did."""
    out = {}
    if len(props):
        settled = props[props['status'] == 'settled']
        picks = props[props['pick'].notna()]
        out.update({
            'lines': len(props), 'settled': len(settled), 'pending': int((props['status'] == 'pending').sum()),
            'void': int((props['status'] == 'void').sum()),
            'picks': _rate(picks), 'edge picks': _rate(picks[picks['signal'].isin(['🟢', '🟡'])]),
            'red picks': _rate(picks[picks['signal'] == '🔴']), 'plain picks': _rate(picks[picks['signal'] == '']),
            'median proj miss': settled['proj error'].abs().median() if len(settled) else np.nan,
            'median line miss': settled['line error'].abs().median() if len(settled) else np.nan,
            'closer than line %': 100 * settled['closer than line'].dropna().astype(float).mean()
            if settled['closer than line'].notna().any() else np.nan,
            'over %': 100 * (settled['actual'] > settled['line']).mean() if len(settled) else np.nan})
    g = games.get('games', pd.DataFrame())
    if len(g):
        known = g[g['winner called'].notna()]
        out.update({'games': len(g), 'winners called': int(known['winner called'].astype(bool).sum()),
                    'games scored': len(known),
                    'mean total miss': known['total error'].abs().mean() if len(known) else np.nan})
    return out
