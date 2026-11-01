"""Slicing the backtest's priced lines (data/backtest/2022_lines.csv) for the dashboard's strategy tester and
player view. No Streamlit, tested in test_backtest.py."""
from typing import Iterable, Optional

import numpy as np
import pandas as pd

from backtest.run import MIN_GAMES, side_result, strategies

# what the tester can bet on each line: a backtest.run.strategies name
BET_ON = {'model': "Model pick (every line)", 'average': "Toward the season average", 'under': "Always Under",
          'over': "Always Over"}


def add_stars(t: pd.DataFrame) -> pd.DataFrame:
    """t with 'stars' (Int64): shortlist.night_stars of the model's pick on each night's main lines of players with
    MIN_GAMES+ games (per variant), ranked by its expected return (model % × pick odds), as tonight's stars are;
    NA for the other lines."""
    from backtest.shortlist import night_stars
    rated = t['main'].astype(bool) & (t['games'] >= MIN_GAMES) & t['model %'].notna() & t['pick odds'].notna()
    out = pd.Series(pd.NA, index=t.index, dtype='Int64')
    variant = t['variant'] if 'variant' in t else pd.Series(0, index=t.index)
    for _, part in t[rated].groupby(variant[rated]):
        out[part.index] = night_stars(part, part['model %'] * part['pick odds']).astype('Int64')
    return t.assign(stars=out)


def filter_lines(t: pd.DataFrame, since=None, until=None, players: Iterable = (), stats: Iterable = (),
                 stars: Iterable = (), min_edge: Optional[float] = None, min_games: int = 0,
                 main_only: bool = True) -> pd.DataFrame:
    """The lines matching every filter given. players: name_ESPN; stars: 0–4 or 'none' (no rating, add_stars);
    min_edge: the model's edge in pp (of its own pick), so it also narrows the other strategies to lines the model
    likes."""
    keep = t['games'] >= min_games
    if main_only:
        keep &= t['main'].astype(bool)
    if since is not None:
        keep &= t['game_date'] >= pd.Timestamp(since)
    if until is not None:
        keep &= t['game_date'] <= pd.Timestamp(until)
    if players:
        keep &= t['name_ESPN'].isin(list(players))
    if stats:
        keep &= t['bet_type'].isin(list(stats))
    if stars:
        keep &= t['stars'].astype(object).where(t['stars'].notna(), 'none').isin(list(stars))
    if min_edge is not None:
        keep &= t['edge pp'] >= min_edge
    return t[keep]


def bets(t: pd.DataFrame, bet_on: str = 'model', side: Optional[str] = None) -> pd.DataFrame:
    """The lines with a bet under the strategy `bet_on` (BET_ON key), optionally only its Over or Under bets:
    adds 'bet side', 'bet odds', 'bet result' (win / loss / push) and 'bet profit' (per unit)."""
    if t.empty:
        return t.assign(**{'bet side': [], 'bet odds': [], 'bet result': [], 'bet profit': []})
    chosen, odds = strategies(t)[BET_ON[bet_on]]
    out = t.assign(**{'bet side': chosen, 'bet odds': odds}, **side_result(t, chosen, odds, 'bet'))
    out = out[out['bet side'].isin([side] if side else ['Over', 'Under'])]
    return out


def totals(b: pd.DataFrame) -> dict:
    """Bets decided (pushes left out), hit %, profit in units, ROI % and the 95% range of the hit rate."""
    from metrics import wilson_interval
    decided = b[b['bet result'].isin(['win', 'loss'])]
    wins, n = int((decided['bet result'] == 'win').sum()), len(decided)
    low, high = wilson_interval(wins, n)
    profit = b['bet profit'].sum()
    staked = b['bet result'].isin(['win', 'loss', 'push']).sum()
    return {'bets': n, 'pushes': int((b['bet result'] == 'push').sum()), 'hit %': 100 * wins / n if n else np.nan,
            'ci low %': 100 * low, 'ci high %': 100 * high, 'profit': profit,
            'ROI %': 100 * profit / staked if staked else np.nan,
            'break-even %': 100 * (1 / decided['bet odds']).mean() if n else np.nan}


def cumulative(b: pd.DataFrame) -> pd.DataFrame:
    """Per game date: bets, profit that day and the running total (units)."""
    daily = b.groupby('game_date').agg(bets=('bet profit', 'size'), profit=('bet profit', 'sum')).reset_index()
    return daily.assign(total=daily['profit'].cumsum())


def lines_summary(t: pd.DataFrame, by='bet_type') -> pd.DataFrame:
    """How the lines themselves resolved, per group: lines, how often the result went over (pushes left out),
    the average line, the average result and the average miss (actual − line)."""
    decided = t[t['actual'] != t['line']]
    g = t.groupby(by)
    return pd.DataFrame({'lines': g.size(),
                         'over %': 100 * decided.groupby(by).apply(lambda d: (d['actual'] > d['line']).mean()),
                         'avg line': g['line'].mean(), 'avg actual': g['actual'].mean(),
                         'actual − line': g.apply(lambda d: (d['actual'] - d['line']).mean())}).reset_index()
