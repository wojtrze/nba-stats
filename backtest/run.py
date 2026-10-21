"""Backtest the props model (models.price_props, unchanged) on Unibet's 2022/23 lines.

    python -m backtest.run                       # both variants, the whole season
    python -m backtest.run --since 2022-11-10 --until 2022-11-20 --variant none

Every line on date D is priced from the games before D only, as the dashboard would have seen it that morning.
There are no historical game odds, so the implied-team-total factor stays 1; the matchup factor works for
players with a known position. Variants for tonight's lineup:
  none      no lineup information (the dashboard without RotoWire)
  absences  every rotation player who didn't play that night is "out" (perfect injury news: an upper bound)

Writes data/backtest/2022_lines.csv (every line, priced and settled) and data/backtest/2022_summary.md.
"""
import argparse
import logging
import os
import time
from typing import Dict, List

import numpy as np
import pandas as pd

import backtest  # noqa: F401  (puts dashboard/ on the path)
from backtest.data_2022 import load_lines_2022, load_logs_2022
from metrics import absence_adjustments, grouped_rates, wilson_interval
from models import prepare_logs, price_props
from tracking import calibration, edge_bucket

log = logging.getLogger(__name__)

OUT_DIR = os.path.join('data', 'backtest')
# the dashboard hides players with fewer games by default (Today's props, "Min games")
MIN_GAMES = 5
# a rotation player for the absences variant: this many minutes per game over the team's last 10 games
ROTATION_MPG, ROTATION_GAMES = 15, 10
# RotoWire's lineup columns (loaders.LINEUP_COLUMNS; loaders needs a Streamlit runtime)
LINEUP_COLUMNS = ['game_date', 'tip_et', 'away', 'home', 'team', 'side', 'lineup_status', 'role', 'pos', 'name',
                  'rotowire_id', 'play_pct', 'injury', 'player_id_ESPN']
KEEP = ['game_date', 'name', 'name_ESPN', 'player_id_ESPN', 'team', 'home', 'away', 'bet_type', 'line', 'main',
        'over_odds', 'under_odds', 'games', 'avg', 'avg L5', 'lineup adj', 'adj avg', 'matchup', 'proj avg',
        'over % L10', 'under % L10', 'best side', 'model %', 'market %', 'break-even %', 'edge pp', 'edge low',
        'pick odds', 'signal']


def known_absences(logs: pd.DataFrame, day: pd.Timestamp, teams) -> pd.DataFrame:
    """Rotation players (ROTATION_MPG+ over the team's last ROTATION_GAMES games before `day`) who didn't play on
    `day`, in RotoWire's format (role may_not_play, 0% to play), so metrics.rotowire_team reads them as out."""
    rows = []
    for team in teams:
        before = logs[(logs['team'] == team) & (logs['Date'] < day)]
        recent = before[before['game_id'].isin(before.drop_duplicates('game_id')['game_id'].tail(ROTATION_GAMES))]
        minutes = recent.groupby('player_id_ESPN')['MIN'].sum() / max(recent['game_id'].nunique(), 1)
        rotation = set(minutes[minutes >= ROTATION_MPG].index)
        played = set(logs.loc[(logs['team'] == team) & (logs['Date'] == day), 'player_id_ESPN'])
        rows += [{'team': team, 'role': 'may_not_play', 'play_pct': 0, 'player_id_ESPN': p,
                  'lineup_status': 'expected', 'injury': 'Out', 'name': str(p)} for p in rotation - played]
    return pd.DataFrame(rows, columns=LINEUP_COLUMNS)


def price_season(logs: pd.DataFrame, lines: pd.DataFrame, variant: str) -> pd.DataFrame:
    """price_props for every date, from the games before it; then the result of each line's pick."""
    no_odds = pd.DataFrame(columns=['event_id', 'market', 'side', 'line', 'odds'])
    no_games = pd.DataFrame(columns=['home', 'away'])
    priced = []
    for day, today in lines.groupby('game_date'):
        before = logs[logs['Date'] < day]
        if before.empty:
            continue
        teams = set(today['home']) | set(today['away'])
        lineups = known_absences(logs, day, teams) if variant == 'absences' else \
            pd.DataFrame(columns=LINEUP_COLUMNS)
        table = price_props(today.drop(columns=['game_date', 'main', 'file_actual', 'player_ESPN', 'closed_date']),
                            before, lineups, no_odds, no_games, adjust=absence_adjustments)
        priced.append(table.assign(game_date=day, main=today['main'].values))
    table = pd.concat(priced, ignore_index=True).rename(columns={'player_id': 'player_id_ESPN'})
    table = table[[c for c in KEEP if c in table]]
    return settle(table, logs)


def settle(table: pd.DataFrame, logs: pd.DataFrame) -> pd.DataFrame:
    """actual (from the logs), and per line the pick's result and profit per unit (pushes return the stake)."""
    stats = sorted(set(table['bet_type']))
    played = logs[['player_id_ESPN', 'Date'] + stats].rename(columns={'Date': 'game_date'})
    table = table.merge(played, on=['player_id_ESPN', 'game_date'], how='left')
    table['actual'] = [row[t] for t, (_, row) in zip(table['bet_type'], table[stats].iterrows())]
    table = table.drop(columns=stats)
    return table.assign(**side_result(table, table['best side'], table['pick odds'], 'pick'))


def side_result(table: pd.DataFrame, side: pd.Series, odds: pd.Series, prefix: str) -> Dict[str, pd.Series]:
    """'<prefix> result' (win / loss / push, NaN without a side) and '<prefix> profit' for betting `side`."""
    margin = (table['actual'] - table['line']) * np.where(side == 'Over', 1, -1)
    result = pd.Series(np.select([margin > 0, margin < 0], ['win', 'loss'], 'push'), index=table.index, dtype=object)
    result = result.where(side.isin(['Over', 'Under']))
    profit = pd.Series(np.select([result == 'win', result == 'loss'], [odds - 1, -1.0], 0.0), index=table.index)
    return {f'{prefix} result': result, f'{prefix} profit': profit.where(result.notna())}


# --- summary ---

def strategies(t: pd.DataFrame) -> Dict[str, tuple]:
    """Each strategy as (side, odds) per line; NaN side = no bet on that line."""
    over, under = pd.Series('Over', index=t.index), pd.Series('Under', index=t.index)
    toward = lambda ref: pd.Series(np.select([t[ref] > t['line'], t[ref] < t['line']], ['Over', 'Under'], ''),
                                   index=t.index).replace('', np.nan)
    odds_of = lambda side: pd.Series(np.where(side == 'Over', t['over_odds'], t['under_odds']), index=t.index)
    pick = t['best side']
    favourite = pd.Series(np.where(t['over_odds'] < t['under_odds'], 'Over', 'Under'), index=t.index)
    out = {"Always Under": under, "Always Over": over, "Bookmaker's favourite side": favourite,
           "Toward the season average": toward('avg'), "Toward the last-5 average": toward('avg L5'),
           "Toward proj avg": toward('proj avg'), "Model pick (every line)": pick,
           "Model pick, edge > 0 (🟢 or 🟡)": pick.where(t['edge pp'] > 0),
           "Model pick, 🟢 only": pick.where(t['signal'] == '🟢')}
    return {name: (side, odds_of(side)) for name, side in out.items()}


def rate_row(t: pd.DataFrame, side: pd.Series, odds: pd.Series) -> Dict:
    r = side_result(t, side, odds, 'x')
    decided = r['x result'].isin(['win', 'loss'])
    wins, n = int((r['x result'] == 'win').sum()), int(decided.sum())
    low, high = wilson_interval(wins, n)
    return {'bets': n, 'hit %': 100 * wins / n if n else np.nan, 'ci low %': 100 * low, 'ci high %': 100 * high,
            'ROI %': 100 * r['x profit'][decided].mean() if n else np.nan, 'avg odds': odds[decided].mean()}


def picks_frame(t: pd.DataFrame) -> pd.DataFrame:
    """The model's decided picks in the shape metrics/tracking expect (is_hit, odds, result, model_pct)."""
    d = t[t['pick result'].isin(['win', 'loss'])]
    return d.assign(is_hit=d['pick result'] == 'win', odds=d['pick odds'], result=d['pick result'],
                    model_pct=d['model %'], month=d['game_date'].dt.strftime('%Y-%m'),
                    **{'edge bucket': edge_bucket(d['edge pp']), 'signal': d['signal'].replace('', 'none')})


def markdown(df: pd.DataFrame, floats: str = '{:.1f}') -> str:
    cols = list(df.columns)
    fmt = lambda v: floats.format(v) if isinstance(v, (float, np.floating)) and not pd.isna(v) else \
        ('–' if pd.isna(v) else str(v))
    return "\n".join(["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
                     + ["| " + " | ".join(fmt(v) for v in row) + " |" for row in df.itertuples(index=False)])


def summary(results: Dict[str, pd.DataFrame], reports: List[Dict]) -> str:
    parts = ["# 2022/23 backtest of the props model", "",
             f"Unibet's 2022/23 player lines, each priced by `models.price_props` from the games before its date "
             f"only. Main lines (the most balanced price per player, stat and game) of players with {MIN_GAMES}+ "
             f"games. Pushes are left out; ROI is per unit at the line's odds; ci = 95% Wilson interval.", ""]
    for report in reports:
        parts += ["- " + ", ".join(f"{k}: {v}" for k, v in report.items())]
    for variant, table in results.items():
        t = table[table['main'] & (table['games'] >= MIN_GAMES)]
        parts += ["", f"## Variant: {variant}", "", f"{len(t)} lines, {t['game_date'].nunique()} dates.", "",
                  "### Strategies on the same lines", ""]
        rows = [{'strategy': name, **rate_row(t, side, odds)} for name, (side, odds) in strategies(t).items()]
        parts.append(markdown(pd.DataFrame(rows)))
        picks = picks_frame(t)
        for title, by in (("By signal", 'signal'), ("By edge (pp)", 'edge bucket'), ("By bet type", 'bet_type'),
                          ("By side", 'best side'), ("By month", 'month')):
            parts += ["", f"### Model pick – {title.lower()}", "", markdown(grouped_rates(picks, by))]
        cal = calibration(picks)
        parts += ["", "### Calibration: model % vs how often the pick won", "", markdown(cal)]
    return "\n".join(parts) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--variant', choices=['none', 'absences', 'both'], default='both')
    parser.add_argument('--since', type=pd.Timestamp)
    parser.add_argument('--until', type=pd.Timestamp)
    parser.add_argument('--out', default=os.path.join(OUT_DIR, '2022_lines.csv'))
    args = parser.parse_args()

    logs, logs_report = load_logs_2022()
    lines, lines_report = load_lines_2022(logs)
    logs = prepare_logs(logs)
    if args.since is not None:
        lines = lines[lines['game_date'] >= args.since]
    if args.until is not None:
        lines = lines[lines['game_date'] <= args.until]
    variants = ['none', 'absences'] if args.variant == 'both' else [args.variant]
    results = {}
    for variant in variants:
        t0 = time.monotonic()
        results[variant] = price_season(logs, lines, variant).assign(variant=variant)
        log.info("%s: %d lines priced in %.0f s", variant, len(results[variant]), time.monotonic() - t0)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    pd.concat(results.values(), ignore_index=True).to_csv(args.out, index=False)
    text = summary(results, [logs_report, lines_report])
    with open(os.path.join(os.path.dirname(args.out), '2022_summary.md'), 'w', encoding='utf-8') as f:
        f.write(text)
    print(text)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    main()
