"""What would have to change for a player line to reach break-even after tax (no Streamlit, tested in
test_whatif.py). The Props page's "What would have to change" tab shows these numbers.

Every number goes back through the pricing the Props table uses (models.line_sides): our chance is calibrated mostly
from Superbet's own margin-free price (metrics.calibrate), so higher odds lower the price's chance and ours with it,
and a different line at the same odds moves our chance only by the model's share. Holding our chance fixed would
overstate what a better price does.

Nothing here is a decision: break-even after tax is the finish line the user chose for these views, not a threshold
checked on unseen nights (decisions.ADMITTED_THRESHOLD).
"""
import math
from typing import Dict, Optional

import numpy as np
import pandas as pd

from metrics import ACTIVE_PROFILE, break_even, expected_return_100
from models import line_sides

MIN_GAMES = 5            # fewer games give no spread worth dividing by
MAX_ODDS = 10.0
LINE_REACH_SD = 3        # how far (in the player's spreads) needed_line searches


def gap_in_spreads(proj_avg, line, sd, games=None) -> float:
    """How far our expectation is from the line, in the player's game-to-game spreads: (proj avg − line) / sd.
    NaN without a usable spread (sd missing or 0, or fewer than MIN_GAMES games when games is given)."""
    if pd.isna(proj_avg) or pd.isna(line) or pd.isna(sd) or sd <= 0 or (games is not None and games < MIN_GAMES):
        return np.nan
    return (proj_avg - line) / sd


def _odds(side: str, side_odds: float, other_odds: float):
    return (side_odds, other_odds) if side == 'Over' else (other_odds, side_odds)


def evaluate(values: pd.Series, line: float, proj_avg: float, side: str, side_odds: float, other_odds: float,
             coef: Optional[Dict], profile: str = ACTIVE_PROFILE) -> Dict:
    """One side of a line priced as the Props table prices it: p win % (calibrated), market % (margin-free),
    break-even % (after the cost profile, with the push chance), distance pp (p win − break-even) and ev net 100.
    NaNs when the side can't be priced."""
    over, under = _odds(side, side_odds, other_odds)
    sides, _, push = line_sides(values, line, proj_avg, over, under, coef)
    v = sides.get(side)
    if v is None or pd.isna(v['p_win']):
        return dict.fromkeys(['p win %', 'market %', 'break-even %', 'distance pp', 'ev net 100'], np.nan)
    be = 100 * float(break_even(v['odds'], profile, push))
    return {'p win %': 100 * v['p_win'], 'market %': 100 * v['market'], 'break-even %': be,
            'distance pp': 100 * v['p_win'] - be,
            'ev net 100': float(expected_return_100(v['p_win'], v['odds'], profile, push))}


def needed_odds(values, line, proj_avg, side, side_odds, other_odds, coef, profile: str = ACTIVE_PROFILE
                ) -> Optional[float]:
    """The lowest odds (2 decimals) for the side at which its expected return after costs is above 0, with the
    other side's odds unchanged; the current odds when it already is; None when even MAX_ODDS isn't enough."""
    ev = lambda o: evaluate(values, line, proj_avg, side, o, other_odds, coef, profile)['ev net 100']
    if pd.isna(ev(side_odds)):
        return None
    if ev(side_odds) > 0:
        return float(side_odds)
    if not ev(MAX_ODDS) > 0:
        return None
    low, high = float(side_odds), MAX_ODDS
    while high - low > 0.002:
        mid = (low + high) / 2
        low, high = (low, mid) if ev(mid) > 0 else (mid, high)
    found = math.ceil(high * 100 - 1e-9) / 100
    while not ev(found) > 0:                         # rounding to 2 decimals can land just short
        found = round(found + 0.01, 2)
    return found


def needed_line(values, line, proj_avg, side, side_odds, other_odds, coef, sd, profile: str = ACTIVE_PROFILE
                ) -> Optional[float]:
    """The nearest line in the side's favour (lower for Over, higher for Under, in whole steps so x.5 stays x.5)
    whose expected return after costs is above 0 at the same odds; None within LINE_REACH_SD spreads. A line
    Superbet doesn't offer at these odds: an estimate of how far off the price would have to be."""
    step = -1.0 if side == 'Over' else 1.0
    reach = LINE_REACH_SD * (sd if pd.notna(sd) and sd > 0 else 1.0)
    candidate = float(line)
    while True:
        candidate += step
        if abs(candidate - line) > reach or candidate < 0:
            return None
        if evaluate(values, candidate, proj_avg, side, side_odds, other_odds, coef, profile)['ev net 100'] > 0:
            return candidate


# --- how often odds moved that much before tip-off ---

PATH_KEY = ['event_id', 'name_ESPN', 'bet_type']


def odds_paths(snapshots: pd.DataFrame, quotes: pd.DataFrame) -> pd.DataFrame:
    """Per line (PATH_KEY) offered before tip-off: night (US-Eastern date), its first line and odds, and the highest
    Over and Under odds seen later at that same first line (max over / max under). snapshots: superbet_props;
    quotes: superbet_prop_quotes (only changes, tip-off taken from the snapshots of the same game)."""
    cols = ['fetched_at'] + PATH_KEY + ['line', 'over_odds', 'under_odds']
    frames = [snapshots[cols + ['start_time']]] if len(snapshots) else []
    if len(quotes) and len(snapshots):
        tips = snapshots.drop_duplicates('event_id', keep='last').set_index('event_id')['start_time']
        frames.append(quotes[cols].assign(start_time=quotes['event_id'].map(tips)))
    if not frames:
        return pd.DataFrame(columns=PATH_KEY + ['night', 'first line', 'first over', 'first under', 'max over',
                                                'max under'])
    rows = pd.concat(frames, ignore_index=True).dropna(subset=['start_time', 'line', 'over_odds', 'under_odds'])
    at, tip = pd.to_datetime(rows['fetched_at'], utc=True), pd.to_datetime(rows['start_time'], utc=True)
    rows = rows[at < tip].assign(at=at[at < tip], tip=tip[at < tip]).sort_values('at', kind='stable')
    first = rows.drop_duplicates(PATH_KEY, keep='first').set_index(PATH_KEY)
    rows = rows.join(first[['line']].rename(columns={'line': 'first line'}), on=PATH_KEY)
    same = rows[rows['line'] == rows['first line']]
    best = same.groupby(PATH_KEY)[['over_odds', 'under_odds']].max()
    out = first[['line', 'over_odds', 'under_odds', 'tip']].rename(
        columns={'line': 'first line', 'over_odds': 'first over', 'under_odds': 'first under'})
    out = out.join(best.rename(columns={'over_odds': 'max over', 'under_odds': 'max under'}))
    out['night'] = out['tip'].dt.tz_convert('US/Eastern').dt.tz_localize(None).dt.normalize()
    return out.drop(columns='tip').reset_index()


def move_share(paths: pd.DataFrame, stat: str, side: str, ratio: float) -> Dict:
    """Among lines of `stat`, the share whose odds for `side` rose at least `ratio`-fold (needed / now) at the same
    line before tip-off: {'share', 'lines', 'nights'}; share NaN without lines."""
    part = paths[paths['bet_type'] == stat]
    if part.empty:
        return {'share': np.nan, 'lines': 0, 'nights': 0}
    s = 'over' if side == 'Over' else 'under'
    rose = part[f'max {s}'] >= ratio * part[f'first {s}'] - 1e-9
    return {'share': 100 * float(rose.mean()), 'lines': len(part), 'nights': int(part['night'].nunique())}


# --- the whole night: every line's gap and distance, the lines nearest to break-even ---

def night_gaps(table: pd.DataFrame) -> pd.DataFrame:
    """The priced lines (models.price_props) with gap sd (gap_in_spreads per line: NaN without a usable spread or
    with fewer than MIN_GAMES games) and distance pp (p win % − break-even net %: how far the evaluated side is
    from break-even after costs; the table's edge net pp, named for these views)."""
    sd = pd.to_numeric(table['sd'], errors='coerce')
    usable = (sd > 0) & (pd.to_numeric(table['games'], errors='coerce') >= MIN_GAMES)
    gap = (pd.to_numeric(table['proj avg'], errors='coerce') - pd.to_numeric(table['line'], errors='coerce')) / sd
    return table.assign(**{'gap sd': gap.where(usable),
                           'distance pp': table['p win %'] - table['break-even net %']})


def nearest(table: pd.DataFrame, values_of, coef: Optional[Dict], n: int = 5,
            profile: str = ACTIVE_PROFILE) -> pd.DataFrame:
    """The n lines of night_gaps output with an evaluated side closest to break-even after costs (highest
    distance pp first), with needed odds (needed_odds for that side; NaN when even MAX_ODDS isn't enough).
    values_of(row): the player's games of the line's stat, as the table priced them."""
    rows = table[table['side'].isin(['Over', 'Under']) & table['distance pp'].notna()]
    rows = rows.sort_values('distance pp', ascending=False, kind='stable').head(n).copy()
    needed = []
    for _, r in rows.iterrows():
        side_odds, other = (r['over_odds'], r['under_odds']) if r['side'] == 'Over' else \
            (r['under_odds'], r['over_odds'])
        found = needed_odds(values_of(r), float(r['line']), r['proj avg'], r['side'], float(side_odds),
                            float(other), coef, profile)
        needed.append(np.nan if found is None else found)
    return rows.assign(**{'needed odds': needed}).reset_index(drop=True)


# --- the lineup: a teammate sits (or plays after all) ---

def lineup_projection(row: pd.Series, logs: pd.DataFrame, out_ids, stat: Optional[str] = None) -> Dict:
    """Our expectation for the row's player with `out_ids` absent, built as price_props builds it: lineup adj =
    metrics.absence_adjustments over the player's and those teammates' own games (logs without topped-up rows),
    proj avg = (avg + lineup adj) × pace factor × matchup factor (the row's)."""
    from metrics import absence_adjustments
    stat = stat or row['bet_type']
    pid = row['player_id']
    out_ids = [o for o in out_ids if o != pid]
    adj = 0.0
    if out_ids and stat in logs:
        part = logs[logs['player_id_ESPN'].isin(set(out_ids) | {pid})]
        adj = float(absence_adjustments(part, [pid], tuple(sorted(out_ids)), [stat]).loc[pid, stat])
    factors = row['pace factor'] * row['matchup factor']
    return {'lineup adj': adj, 'proj avg': (row['avg'] + adj) * factors}


def price_lineup(row: pd.Series, values: pd.Series, logs: pd.DataFrame, out_ids, coef: Optional[Dict],
                 profile: str = ACTIVE_PROFILE) -> Dict:
    """The row's line priced again (models.price_line, the side chosen as the table chooses it) with our
    expectation for `out_ids` absent, at Superbet's current odds and line: the price_line columns plus lineup adj,
    proj avg, gap sd and distance pp. The price is held as it is: Superbet usually moves it too when the news comes."""
    from models import price_line
    proj = lineup_projection(row, logs, out_ids)
    priced = price_line(values, row['line'], proj['proj avg'], row['over_odds'], row['under_odds'], coef, profile)
    return priced | proj | {'gap sd': gap_in_spreads(proj['proj avg'], row['line'], row['sd'], row['games']),
                            'distance pp': priced['p win %'] - priced['break-even net %']}


def single_absences(row: pd.Series, values: pd.Series, logs: pd.DataFrame, out_now, mates, coef: Optional[Dict],
                    profile: str = ACTIVE_PROFILE) -> pd.DataFrame:
    """For each of `mates` not already in out_now (nor the player): the line priced as if he also sat
    (price_lineup with out_now + him) and the games the player played without him (inside his stint), highest
    distance to break-even first. Columns: teammate_id, games without, proj avg, side, p win %, distance pp,
    ev net 100."""
    from metrics import stint_games
    cols = ['teammate_id', 'games without', 'proj avg', 'side', 'p win %', 'distance pp', 'ev net 100']
    rows = []
    for mate in mates:
        if mate in out_now or mate == row['player_id']:
            continue
        p = price_lineup(row, values, logs, list(out_now) + [mate], coef, profile)
        games = stint_games(logs, row['player_id'], mate)
        rows.append({'teammate_id': mate, 'games without': int((~games['teammate_played']).sum()),
                     'proj avg': p['proj avg'], 'side': p['side'], 'p win %': p['p win %'],
                     'distance pp': p['distance pp'], 'ev net 100': p['ev net 100']})
    return pd.DataFrame(rows, columns=cols).sort_values('distance pp', ascending=False, na_position='last') \
        .reset_index(drop=True)
