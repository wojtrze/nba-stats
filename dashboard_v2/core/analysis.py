"""The few calculations v2 adds to the old dashboard's metrics/models/tracking (pure pandas, tested in
test_v2_analysis.py)."""
from typing import Iterable, Optional

import numpy as np
import pandas as pd

from metrics import (LEGACY, SUPERBET_STANDARD, side_profit as metrics_side_profit, side_result, team_rotation,
                     with_without_matrix)
from tracking import PROP_KEY, settle_props

GAP_LABELS = ['line 15%+ under avg', '5–15% under', 'within 5%', '5–15% over', 'line 15%+ over avg']


# --- settled lines vs the players' averages ---

def pregame_average(logs: pd.DataFrame, rows: pd.DataFrame) -> pd.DataFrame:
    """rows (player_id, game_date, bet_type) with the player's average of that stat over the games played
    strictly before game_date: 'pre avg', 'pre avg L10', 'pre sd' (the spread of those games) and 'pre games'.
    logs: prepare_logs output, already cut to the seasons and game types to average over."""
    out = rows.assign(**{'pre avg': np.nan, 'pre avg L10': np.nan, 'pre sd': np.nan, 'pre games': 0})
    if rows.empty or logs.empty:
        return out
    logs = logs.assign(player_id=logs['player_id_ESPN'].astype('Int64')).sort_values('Date')
    for stat in set(rows['bet_type']) & set(logs.columns):
        through = logs[['player_id', 'Date']].copy()
        by_player = logs.groupby('player_id')[stat]
        through['pre avg'] = by_player.transform(lambda s: s.expanding().mean())
        through['pre avg L10'] = by_player.transform(lambda s: s.rolling(10, min_periods=1).mean())
        through['pre sd'] = by_player.transform(lambda s: s.expanding().std())
        through['pre games'] = logs.groupby('player_id').cumcount() + 1
        mask = (rows['bet_type'] == stat) & rows['player_id'].notna() & rows['game_date'].notna()
        part = rows.loc[mask, ['player_id', 'game_date']].astype({'player_id': 'Int64'})
        part['game_date'] = pd.to_datetime(part['game_date'])
        if part.empty:
            continue
        # the last game before the date: its running averages are the averages going into the game
        merged = pd.merge_asof(part.reset_index().sort_values('game_date'),
                               through.sort_values('Date'), left_on='game_date', right_on='Date', by='player_id',
                               allow_exact_matches=False, direction='backward').set_index('index')
        for col in ['pre avg', 'pre avg L10', 'pre sd', 'pre games']:
            out.loc[merged.index, col] = merged[col]
    out['pre games'] = out['pre games'].fillna(0).astype(int)
    return out


def toward(df: pd.DataFrame, reference: str) -> pd.DataFrame:
    """The side a reference number points to ('Over' when it's above the line, None when equal or unknown), and
    how that side did: win / loss / push, NaN until the line is settled. Adds '<reference> side' and
    '<reference> result'."""
    ref = df[reference]
    side = pd.Series(np.select([ref > df['line'], ref < df['line']], ['Over', 'Under'], ''), index=df.index)
    side = side.where(ref.notna() & (side != ''))
    margin = (df['actual'] - df['line']) * np.where(side == 'Over', 1, -1)
    result = side_result(margin, side.notna() & (df['status'] == 'settled'))
    return df.assign(**{f'{reference} side': side, f'{reference} result': result})


def side_profit(df: pd.DataFrame, reference: str, profile: str = LEGACY) -> pd.Series:
    """Profit per unit of betting the side `reference` points to, at that side's opening odds (metrics.side_profit
    under the cost profile)."""
    odds = np.where(df[f'{reference} side'] == 'Over', df['over_odds'], df['under_odds'])
    return metrics_side_profit(df[f'{reference} result'], odds, profile)


def gap_bucket(line: pd.Series, average: pd.Series) -> pd.Series:
    """How far the line sits from the average, as a share of the average (GAP_LABELS)."""
    gap = (line - average) / average.where(average > 0)
    return pd.cut(gap, [-np.inf, -0.15, -0.05, 0.05, 0.15, np.inf], labels=GAP_LABELS)


def settle_lines(snapshots: pd.DataFrame, logs: pd.DataFrame, games: pd.DataFrame,
                 average_logs: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """tracking.settle_props (every snapshotted line as first offered before tip-off, settled) plus that
    snapshot's over/under odds and proj_avg, the player's pre-game averages (from average_logs, default logs),
    the side toward the pre-game average and toward proj_avg with their results and profit, the line error
    (actual − line) and the line's gap to the average."""
    settled = settle_props(snapshots, logs, games)
    if settled.empty:
        return settled
    fetched = pd.to_datetime(snapshots['fetched_at'], utc=True)
    first = snapshots[fetched < pd.to_datetime(snapshots['start_time'], utc=True)] \
        .sort_values('fetched_at').drop_duplicates(PROP_KEY, keep='first')
    extra = [c for c in ['over_odds', 'under_odds', 'proj_avg'] if c in first]
    first = first.assign(game=first['away'].str.upper() + ' @ ' + first['home'].str.upper())
    settled = settled.merge(first[['name', 'game', 'bet_type', 'start_time'] + extra]
                            .drop_duplicates(['name', 'game', 'bet_type', 'start_time']),
                            on=['name', 'game', 'bet_type', 'start_time'], how='left')
    if 'proj_avg' not in settled:
        settled['proj_avg'] = np.nan
    settled = pregame_average(average_logs if average_logs is not None else logs, settled)
    settled = toward(toward(settled, 'pre avg'), 'proj_avg')
    for reference in ('pre avg', 'proj_avg'):
        settled[f'{reference} profit'] = side_profit(settled, reference)
        settled[f'{reference} profit std'] = side_profit(settled, reference, SUPERBET_STANDARD)
    settled['line error'] = (settled['actual'] - settled['line']).where(settled['status'] == 'settled')
    settled['gap'] = gap_bucket(settled['line'], settled['pre avg'])
    # our expectation's distance from the line in the player's spreads (whatif.gap_in_spreads)
    usable = (settled['pre games'] >= GAP_MIN_GAMES) & (settled['pre sd'] > 0)
    settled['gap sd'] = ((settled['proj_avg'] - settled['line']) / settled['pre sd']).where(usable)
    return settled


# --- the look-back of the what-if tab: lines by their gap in the player's spreads ---

GAP_MIN_GAMES = 5
SD_EDGES = [-np.inf, -1.0, -0.5, 0.5, 1.0, np.inf]
SD_LABELS = ['≤ −1', '−1 … −0.5', '−0.5 … +0.5', '+0.5 … +1', '≥ +1']


def sd_group(gap_sd: pd.Series) -> pd.Series:
    """The gap in spreads as one of SD_LABELS."""
    return pd.cut(gap_sd, SD_EDGES, labels=SD_LABELS)


def _side_price(df: pd.DataFrame, side: pd.Series) -> pd.Series:
    """The margin-free chance (%) of `side` from each row's over/under odds."""
    over, under = 1 / df['over_odds'], 1 / df['under_odds']
    p_over = 100 * over / (over + under)
    return pd.Series(np.where(side == 'Over', p_over, 100 - p_over), index=df.index)


def last_game_line(settled: pd.DataFrame, player_id, stat: str, before) -> Optional[dict]:
    """The player's settled line of `stat` from his last game before `before` (a date): line, proj_avg, gap sd,
    side (toward our expectation), actual, result and return per 100 staked after tax at that line's odds (the
    toward-side's profit, SUPERBET_STANDARD). None when there's no such line."""
    if settled.empty:
        return None
    mine = settled[(settled['player_id'].astype('Int64') == int(player_id)) & (settled['bet_type'] == stat)
                   & (settled['status'] == 'settled')
                   & (pd.to_datetime(settled['game_date']) < pd.Timestamp(before).normalize())]
    if mine.empty:
        return None
    r = mine.sort_values('game_date').iloc[-1]
    return {'game_date': r['game_date'], 'game': r.get('game'), 'line': r['line'], 'proj_avg': r['proj_avg'],
            'gap sd': r['gap sd'], 'side': r['proj_avg side'], 'actual': r['actual'],
            'result': r['proj_avg result'],
            'return 100': 100 * r['proj_avg profit std'] if pd.notna(r['proj_avg profit std']) else np.nan}


def _night_range(won: pd.Series, price: pd.Series, nights: pd.Series, draws: int = 1000, seed: int = 7):
    """95% range of mean(won − price) from resampling whole nights."""
    diff = (won - price).groupby(nights.values).agg(['sum', 'size'])
    if len(diff) < 2:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, len(diff), size=(draws, len(diff)))
    sums, sizes = diff['sum'].values[pick].sum(axis=1), diff['size'].values[pick].sum(axis=1)
    est = sums / sizes
    return float(np.percentile(est, 2.5)), float(np.percentile(est, 97.5))


def gap_groups(settled: pd.DataFrame) -> pd.DataFrame:
    """Settled lines by their gap in spreads (SD_LABELS), betting the side toward our expectation: lines, nights,
    won % (pushes left out), price % (that side's margin-free chance at the line's odds), won − price pp with a 95%
    range from resampling whole nights, and the return per 100 staked after tax."""
    cols = ['group', 'lines', 'nights', 'won %', 'price %', 'won − price pp', 'low pp', 'high pp', 'return 100']
    d = settled[settled['proj_avg result'].isin(['win', 'loss']) & settled['gap sd'].notna()
                & settled['over_odds'].notna() & settled['under_odds'].notna()]
    if d.empty:
        return pd.DataFrame(columns=cols)
    d = d.assign(group=sd_group(d['gap sd']), won=100.0 * (d['proj_avg result'] == 'win'),
                 price=_side_price(d, d['proj_avg side']))
    rows = []
    for group, part in d.groupby('group', observed=True):
        low, high = _night_range(part['won'], part['price'], part['game_date'])
        rows.append({'group': group, 'lines': len(part), 'nights': part['game_date'].nunique(),
                     'won %': part['won'].mean(), 'price %': part['price'].mean(),
                     'won − price pp': part['won'].mean() - part['price'].mean(), 'low pp': low, 'high pp': high,
                     'return 100': 100 * part['proj_avg profit std'].mean()})
    return pd.DataFrame(rows, columns=cols)


def side_rates(settled: pd.DataFrame, by, reference: str) -> pd.DataFrame:
    """Per group: lines decided, how often the side toward `reference` won (pushes left out) and its ROI."""
    decided = settled[settled[f'{reference} result'].isin(['win', 'loss'])]
    if decided.empty:
        return pd.DataFrame(columns=[by, 'lines', 'hit %', 'ROI %', 'ROI % std'])
    grouped = decided.groupby(by, observed=True)
    out = {'lines': grouped.size(),
           'hit %': 100 * grouped[f'{reference} result'].apply(lambda r: (r == 'win').mean()),
           'ROI %': 100 * grouped[f'{reference} profit'].mean()}
    if f'{reference} profit std' in decided:
        out['ROI % std'] = 100 * grouped[f'{reference} profit std'].mean()
    return pd.DataFrame(out).reset_index()


# --- a player's with/without row ---

def teammate_impact(logs: pd.DataFrame, player_id, team: str, stat: str, out_ids: Iterable = (),
                    min_games: int = 3, min_minutes: float = 10) -> pd.DataFrame:
    """The player's row of the with/without matrix against every rotation teammate: their stat with and without
    the teammate (inside the teammate's stint), the games behind each, the change (without − with) and whether
    the teammate is out tonight. Sorted by the size of the change; empty without teammates."""
    rotation = team_rotation(logs, team, min_games, min_minutes)
    mates = [p for p in rotation.index if p != player_id]
    out_ids = set(out_ids)
    mates += [p for p in out_ids if p not in mates and p != player_id]
    if not mates:
        return pd.DataFrame(columns=['teammate_id', 'teammate', 'with', 'without', 'n_with', 'n_without', 'change',
                                     'out tonight'])
    part = logs[logs['player_id_ESPN'].isin(set(mates) | {player_id})]
    m = with_without_matrix(part, [player_id], mates, stat)
    names = logs.groupby('player_id_ESPN')['player_display_name'].last()
    row = pd.DataFrame({'teammate_id': mates, 'teammate': [names.get(p, str(p)) for p in mates],
                        'with': m['with'].loc[player_id].values, 'without': m['without'].loc[player_id].values,
                        'n_with': m['n_with'].loc[player_id].values, 'n_without': m['n_without'].loc[player_id].values,
                        'change': m['delta'].loc[player_id].values})
    row['out tonight'] = row['teammate_id'].isin(out_ids)
    return row.sort_values('change', key=lambda c: c.abs(), ascending=False, na_position='last') \
        .reset_index(drop=True)


# --- a team's games ---

def team_game_log(games: pd.DataFrame, team: str) -> pd.DataFrame:
    """One row per game of the team, oldest first: date, opponent, home/away, points, margin, win, possessions
    and per-game offensive / defensive rating and pace (possessions = FGA + 0.44·FTA + TO − OREB)."""
    sides = []
    for side, other in (('home', 'away'), ('away', 'home')):
        g = games[games[side] == team]
        poss = g[f'{side}_FGA'] + 0.44 * g[f'{side}_FTA'] + g[f'{side}_TO'] - g[f'{side}_OREB']
        opp_poss = g[f'{other}_FGA'] + 0.44 * g[f'{other}_FTA'] + g[f'{other}_TO'] - g[f'{other}_OREB']
        sides.append(pd.DataFrame({
            'game_id': g['game_id'], 'date': g['date'], 'season_id': g['season_id'],
            'season_type': g['season_type'], 'opp': g[other], 'location': side, 'pts': g[f'{side}_score'],
            'opp_pts': g[f'{other}_score'], 'poss': poss, 'opp_poss': opp_poss}))
    log = pd.concat(sides).sort_values('date').reset_index(drop=True)
    log['margin'] = log['pts'] - log['opp_pts']
    log['win'] = log['margin'] > 0
    log['off_rtg'] = 100 * log['pts'] / log['poss']
    log['def_rtg'] = 100 * log['opp_pts'] / log['opp_poss']
    log['pace'] = (log['poss'] + log['opp_poss']) / 2
    return log
