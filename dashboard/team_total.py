"""H3 (docs/hipotezy_wyceny.md): Superbet's team totals against its own player points lines. One code for the
backtests (backtest/team_total.py: the registry's test; backtest/ablation.py: the gap as a model input).

At one read of a game, per team:

    T       the team's points by Superbet's team-total ladder (HOME_TOTAL / AWAY_TOTAL: the line where the
            margin-free Over chance is 50%, interpolated; else TOTAL and SPREAD)
    S       the sum of the medians of the team's player PTS lines (line + the margin-free chance's normal
            quantile × PTS_SD(line))
    others  what the team's other players usually score: their points over the team's last OTHERS_GAMES games
            / OTHERS_GAMES (a game a player missed counts 0), for players whose latest team it is, without a PTS
            line at this read and not Out in RotoWire's latest version (play_pct ≤ OUT_MAX_PCT)
    gap     T − S − others − OFFSET. Above 0: the team total says the team scores more than its players' lines
            add up to, so the lines are low (Over); below 0: Under.

Recognition (30 nights to 2026-11-20, docs/hipotezy_wyceny.md H3): the players' results follow the gap
(correlation 0.26 with their points minus their lines), the team's result doesn't (0.04): the team total is right,
the players' lines are off.

The gap is shared out over the team's PTS lines in proportion to each player's median (shift = gap × median / S):
the player's points by the team total.
"""
from statistics import NormalDist
from typing import Dict, Iterable, Optional

import numpy as np
import pandas as pd

OTHERS_GAMES = 10
OUT_MAX_PCT = 25            # RotoWire's chance to play at or below which a player counts as out (metrics.rotowire_team)
OFFSET = 0.0                # points: the gap's mean on the recognition nights, fixed with D (set below)
MIN_GAP = 6.0               # points: H3's rule lists a team's PTS lines from this |gap| on
STAT = 'PTS'
TEAM_COLUMNS = ['event_id', 'team', 'T', 'S', 'n', 'others', 'gap']


def pts_sd(line) -> np.ndarray:
    """The spread of a player's points around his PTS line (Superbet 2026/27: 5.3 at lines up to 10, 8.2 above 25)."""
    return 3.5 + 0.2 * np.asarray(line, dtype=float)


def over_chance(over_odds, under_odds) -> np.ndarray:
    o, u = 1 / np.asarray(over_odds, dtype=float), 1 / np.asarray(under_odds, dtype=float)
    return o / (o + u)


def pts_median(line, over_odds, under_odds) -> np.ndarray:
    """The points where the margin-free Over chance would be 50%."""
    p = np.clip(over_chance(over_odds, under_odds), 0.02, 0.98)
    z = np.array([NormalDist().inv_cdf(x) for x in np.atleast_1d(p)])
    return np.asarray(line, dtype=float) + z * pts_sd(line)


def ladder_median(lines, p_over) -> float:
    """The line where the Over chance is 50% on a ladder (lines and their margin-free Over chances), by linear
    interpolation between the two nearest rungs (extrapolated past the end; NaN with fewer than two rungs)."""
    t = pd.DataFrame({'line': lines, 'p': p_over}).dropna().drop_duplicates('line').sort_values('line')
    if len(t) < 2:
        return np.nan
    x, y = t['line'].values, t['p'].values
    below = np.where(y >= 0.5)[0]
    i = below[-1] if len(below) else 0
    i = min(i, len(x) - 2)
    if y[i] == y[i + 1]:
        return float((x[i] + x[i + 1]) / 2)
    return float(x[i] + (0.5 - y[i]) * (x[i + 1] - x[i]) / (y[i + 1] - y[i]))


def _ou_median(odds: pd.DataFrame, market: str) -> float:
    t = odds[odds['market'] == market].pivot_table(index='line', columns='side', values='odds', aggfunc='last')
    if not {'over', 'under'} <= set(t.columns):
        return np.nan
    t = t.dropna()
    return ladder_median(t.index.values, over_chance(t['over'], t['under']))


def team_points(odds: pd.DataFrame) -> Dict[str, float]:
    """{'home': points, 'away': points} of one game's markets at a read (rows: market, side, line, odds)."""
    home, away = _ou_median(odds, 'HOME_TOTAL'), _ou_median(odds, 'AWAY_TOTAL')
    if pd.isna(home) or pd.isna(away):
        total = _ou_median(odds, 'TOTAL')
        s = odds[odds['market'] == 'SPREAD']
        h = s[s['side'] == 'home'][['line', 'odds']].rename(columns={'odds': 'home'})
        a = s[s['side'] == 'away'].assign(line=lambda x: -x['line'])[['line', 'odds']].rename(columns={'odds': 'away'})
        t = h.merge(a, on='line').dropna()
        # home covers handicap h when margin + h > 0, away when margin < -h: P(away) falls with h, 50% at -margin
        margin = -ladder_median(t['line'].values, over_chance(t['away'], t['home'])) if len(t) else np.nan
        if pd.isna(home):
            home = (total + margin) / 2
        if pd.isna(away):
            away = (total - margin) / 2
    return {'home': home, 'away': away}


def others_points(before: pd.DataFrame, team: str, exclude: Iterable, team_of: Dict) -> float:
    """What the team's players outside `exclude` usually score: their points over the team's last OTHERS_GAMES
    games / OTHERS_GAMES. before: player games before the night (team, Date, PTS, player_id_ESPN)."""
    games = before[before['team'] == team]
    dates = np.sort(games['Date'].unique())[-OTHERS_GAMES:]
    if len(dates) == 0:
        return np.nan
    recent = games[games['Date'].isin(dates)]
    exclude = set(int(p) for p in exclude if pd.notna(p))
    mine = recent[[team_of.get(p) == team and int(p) not in exclude for p in recent['player_id_ESPN']]]
    return float(mine['PTS'].sum() / len(dates))


def out_ids(version: Optional[pd.DataFrame]) -> set:
    """Players RotoWire's version (with player_id_ESPN) gives a chance to play of OUT_MAX_PCT or less."""
    if version is None or version.empty:
        return set()
    pct = pd.to_numeric(version['play_pct'], errors='coerce')
    return set(version.loc[(pct <= OUT_MAX_PCT) & version['player_id_ESPN'].notna(), 'player_id_ESPN'].astype(int))


def team_gaps(lines: pd.DataFrame, odds: pd.DataFrame, before: pd.DataFrame, team_of: Dict,
              out: Iterable = (), home: str = None, away: str = None) -> pd.DataFrame:
    """TEAM_COLUMNS for one game at one read. lines: the game's lines at the read (bet_type, line, over_odds,
    under_odds, player_id_ESPN); odds: its game markets at the read; before: player games before the night; out:
    RotoWire's out players; home / away: the teams."""
    pts = lines[(lines['bet_type'] == STAT) & lines['player_id_ESPN'].notna()]
    pts = pts.assign(team=pts['player_id_ESPN'].map(team_of),
                     median=pts_median(pts['line'], pts['over_odds'], pts['under_odds']) if len(pts) else [])
    totals = team_points(odds)
    event = lines['event_id'].iloc[0] if len(lines) else None
    rows = []
    for where, team in (('home', home), ('away', away)):
        mine = pts[pts['team'] == team]
        if mine.empty or pd.isna(totals[where]):
            continue
        others = others_points(before, team, set(mine['player_id_ESPN']) | set(out), team_of)
        S = float(mine['median'].sum())
        rows.append({'event_id': event, 'team': team, 'T': totals[where], 'S': S, 'n': len(mine), 'others': others,
                     'gap': totals[where] - S - others - OFFSET})
    return pd.DataFrame(rows, columns=TEAM_COLUMNS)


def line_shifts(lines: pd.DataFrame, gaps: pd.DataFrame, team_of: Dict) -> pd.Series:
    """Each PTS line's share of its team's gap (gap × median / S), 0 for other lines and teams without a gap."""
    out = pd.Series(0.0, index=lines.index)
    if gaps.empty:
        return out
    pts = (lines['bet_type'] == STAT) & lines['player_id_ESPN'].notna()
    team = lines.loc[pts, 'player_id_ESPN'].map(team_of)
    g = gaps.set_index('team')
    median = pts_median(lines.loc[pts, 'line'], lines.loc[pts, 'over_odds'], lines.loc[pts, 'under_odds'])
    share = median / team.map(g['S']).values
    out.loc[pts] = np.nan_to_num(team.map(g['gap']).values * share)
    return out
