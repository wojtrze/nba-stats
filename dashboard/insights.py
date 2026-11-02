"""Curiosities of a settled night and players' streaks against Superbet's lines, for the Overview (no Streamlit,
tested in test_insights.py).

A night's curiosities compare what we expected before tip-off (nightly.night_props' proj_avg, the games'
projected scores) with what happened. A streak is how many of a player's latest saved Superbet lines in a stat
all went the same way (Over or Under), judged at the last line before tip-off."""
from typing import Dict

import numpy as np
import pandas as pd

# the stats a night's surprises are told for, in this order (ARP = PRA)
SURPRISE_STATS = ['PTS', 'REB', 'AST', '3PM', 'ARP']
# the stats streaks are counted in: the main ones and their sums, not fouls or attempts
STREAK_STATS = ['PTS', 'REB', 'AST', '3PM', 'ARP', 'PR', 'PA', 'RA']
MIN_STREAK = 4


def night_curiosities(props: pd.DataFrame, games: pd.DataFrame, spot_on: int = 5) -> Dict:
    """props: nightly.night_props of the night(s); games: night_games(...)['games']. Returns
    'surprises' (per SURPRISE_STATS stat the settled line with the largest |actual − proj_avg|, biggest first),
    'spot_on' (the `spot_on` settled lines of those stats with the smallest |actual − proj_avg|),
    'line_miss' (the settled line farthest from Superbet's line, or None), 'best_total' and 'best_margin' (the game
    whose projected total / margin was closest, or None). Lines without a projection are left out."""
    out = {'surprises': pd.DataFrame(), 'spot_on': pd.DataFrame(), 'line_miss': None, 'best_total': None,
           'best_margin': None}
    if len(props):
        settled = props[(props['status'] == 'settled') & props['bet_type'].isin(SURPRISE_STATS)]
        projected = settled[settled['proj_avg'].notna()].assign(
            miss=lambda d: (d['actual'] - d['proj_avg']).abs())
        if len(projected):
            worst = projected.sort_values('miss', ascending=False).drop_duplicates('bet_type')
            out['surprises'] = worst.sort_values('miss', ascending=False).reset_index(drop=True)
            out['spot_on'] = projected.sort_values(['miss', 'bet_type'], kind='stable').head(spot_on) \
                .reset_index(drop=True)
        if len(settled):
            far = (settled['actual'] - settled['line']).abs()
            out['line_miss'] = settled.loc[far.idxmax()]
    if len(games) and 'total error' in games:
        known = games[games['total error'].notna()]
        if len(known):
            out['best_total'] = known.loc[known['total error'].abs().idxmin()]
            out['best_margin'] = known.loc[known['margin error'].abs().idxmin()]
    return out


def line_streaks(settled: pd.DataFrame, min_len: int = MIN_STREAK) -> pd.DataFrame:
    """Each player's current run against Superbet's lines in each STREAK_STATS stat. settled: tracking.settle_props
    of the saved lines (one per player, stat and game). A line's side is the result against the last line before
    tip-off (else the line): Over, Under or push; void, pending and unresolved lines are skipped, a push ends a
    run. Runs of at least min_len: player_id, name, bet_type, side, n, since / until (game dates), last line."""
    columns = ['player_id', 'name', 'bet_type', 'side', 'n', 'since', 'until', 'last line']
    if settled.empty:
        return pd.DataFrame(columns=columns)
    lines = settled[(settled['status'] == 'settled') & settled['bet_type'].isin(STREAK_STATS)
                    & settled['player_id'].notna()]
    line = lines['last line'].fillna(lines['line']) if 'last line' in lines else lines['line']
    lines = lines.assign(judged=line, side=np.sign(lines['actual'] - line).map({1: 'Over', -1: 'Under', 0: 'push'}))
    rows = []
    for (player, stat), part in lines.sort_values('game_date', kind='stable').groupby(['player_id', 'bet_type']):
        sides = part['side'].tolist()
        last = sides[-1]
        if last == 'push':
            continue
        n = next((i for i, s in enumerate(reversed(sides)) if s != last), len(sides))
        if n >= min_len:
            run = part.iloc[-n:]
            rows.append({'player_id': player, 'name': run['name'].iloc[-1], 'bet_type': stat, 'side': last,
                         'n': n, 'since': run['game_date'].iloc[0], 'until': run['game_date'].iloc[-1],
                         'last line': run['judged'].iloc[-1]})
    out = pd.DataFrame(rows, columns=columns)
    return out.sort_values(['n', 'until'], ascending=False, kind='stable').reset_index(drop=True)


def tonight_streaks(streaks: pd.DataFrame, tonight: pd.DataFrame) -> pd.DataFrame:
    """The streaks of players who have that stat's line tonight. tonight: priced props (player_id, bet_type, line,
    name, event_id, name_ESPN; stars when rated). Adds 'tonight line' and the line's keys; tonight's name (ESPN's
    spelling) replaces Superbet's."""
    if streaks.empty or tonight.empty:
        return streaks.iloc[0:0].assign(**{'tonight line': pd.Series(dtype=float)})
    keep = [c for c in ['player_id', 'bet_type', 'line', 'name', 'event_id', 'name_ESPN', 'stars'] if c in tonight]
    lines = tonight[keep].dropna(subset=['player_id']).drop_duplicates(['player_id', 'bet_type']) \
        .rename(columns={'line': 'tonight line', 'name': 'tonight name'})
    lines['player_id'] = lines['player_id'].astype('Int64')
    out = streaks.assign(player_id=streaks['player_id'].astype('Int64')).merge(lines, on=['player_id', 'bet_type'])
    out['name'] = out['tonight name'].fillna(out['name'])
    return out.drop(columns='tonight name').reset_index(drop=True)
