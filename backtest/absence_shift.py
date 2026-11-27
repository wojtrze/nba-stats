"""H10 (docs/hipotezy_wyceny.md): a regular ruled Out and his teammates' lines, the rule of the Overview's "Big
chances vs Superbet" window (dashboard/absence_window.py).

    python -m backtest.absence_shift [--d YYYY-MM-DD] [--skip-2022]

  1. History (Unibet 2022/23, data/backtest/2022_lines.csv, variant 'absences': every rotation player who didn't
     play is known to be out, an upper bound on the news). A line counts when a regular (news.MIN_MINUTES+ over
     his last 10 games) of the player's team sat that night; side = the direction of the line's lineup adj, its
     size = |lineup adj| / avg. Won − price (margin-free) and ROI after tax by game without him no. (1, 2–3, 4+:
     the lowest of the team's absent regulars) and size (10%+, 20%+), with 95% ranges from resampling nights.
  2. Superbet: the rule exactly as the window applies it (absence_window.out_tonight from the night's RotoWire
     versions, absence_window.signal_rows: each listed teammate line at its first scheduled read once Out was known,
     on the side of its change), counted and judged as backtest/mispricing_eval's signals: once per game, player,
     bet and side, only when the next read still had the same line and odds not worse, after-tax CLV and ROI with
     99% ranges, the registry's verdict. Plus won − price on the settled signals.

Nights up to D are recognition (descriptive: the rule was fixed before looking at them, D = the day it was
written); nights after D decide (at least 10). Writes data/backtest/absence_shift.md and absence_shift.json (what
the Overview's window says about the record). The status in mispricing_status.json is set by hand.
"""
import argparse
import json
import logging
import os
from typing import Dict

import numpy as np
import pandas as pd

import backtest  # noqa: F401  (puts dashboard/ on the path)
from absence_window import MAX_GAME_NO, MIN_SHARE, missed_in_a_row, out_tonight, signal_rows
from backtest.mispricing_eval import TAX, economic, signals
from backtest.run import OUT_DIR, markdown
from metrics import add_combined_stats
from news import _night, lineup_versions, offers, player_ids, regulars_by_night
from safe_io import atomic_write_text

log = logging.getLogger(__name__)

REPORT_FILE = os.path.join(OUT_DIR, 'absence_shift.md')
SUMMARY_FILE = os.path.join(OUT_DIR, 'absence_shift.json')
LINES_2022 = os.path.join(OUT_DIR, '2022_lines.csv')
D = '2026-11-19'
SIZES = (MIN_SHARE, 0.20)
GROUPS = (('1', 1, 1), ('2–3', 2, MAX_GAME_NO), (f'{MAX_GAME_NO + 1}+', MAX_GAME_NO + 1, 10 ** 6))


def night_range(nights: np.ndarray, values: np.ndarray, level: float = 0.95, n: int = 2000, seed: int = 0):
    """The mean's range from resampling whole nights."""
    if len(values) == 0:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    by_night = pd.Series(values).groupby(nights)
    sums, counts = by_night.sum().values, by_night.size().values
    picks = rng.integers(0, len(sums), size=(n, len(sums)))
    means = sums[picks].sum(axis=1) / counts[picks].sum(axis=1)
    return tuple(np.percentile(means, [50 * (1 - level), 50 * (1 + level)]))


def scored(s: pd.DataFrame) -> Dict:
    """Lines, nights, won %, price %, won − price pp (95% range) and ROI after tax % of settled sides (won, price
    0–1, odds, night)."""
    if s.empty:
        return {'lines': 0, 'nights': 0}
    diff = 100 * (s['won'] - s['price'])
    low, high = night_range(s['night'].values, diff.values)
    return {'lines': len(s), 'nights': s['night'].nunique(), 'won %': 100 * s['won'].mean(),
            'price %': 100 * s['price'].mean(), 'won − price pp': diff.mean(), 'low': low, 'high': high,
            'ROI after tax %': 100 * np.where(s['won'] == 1, TAX * s['odds'] - 1, -1.0).mean()}


# --- 1. history: Unibet 2022/23 ---

def absent_regulars(logs: pd.DataFrame) -> pd.DataFrame:
    """Per team and date: the lowest game-without-him no. among the team's regulars who sat (team, night, game_no)."""
    logs = logs.assign(MIN=pd.to_numeric(logs['MIN'], errors='coerce'))
    nights = sorted(logs['Date'].unique())
    regulars = regulars_by_night(logs, nights)
    rows = []
    for night in nights:
        before = logs[logs['Date'] < night]
        if before.empty:
            continue
        team_now = before.sort_values('Date').groupby('player_id_ESPN')['team'].last()
        today = logs[logs['Date'] == night]
        played = set(today.loc[today['MIN'] > 0, 'player_id_ESPN'])
        for team in set(today['team']):
            sat = [p for p in regulars.get(night, ()) if team_now.get(p) == team and p not in played]
            if sat:
                rows.append({'team': team, 'night': night,
                             'game_no': 1 + min(missed_in_a_row(before, p, team, night) for p in sat)})
    return pd.DataFrame(rows, columns=['team', 'night', 'game_no'])


def history_2022(lines: pd.DataFrame, logs: pd.DataFrame) -> pd.DataFrame:
    """Won − price of the side toward the lineup adj by game no. and size (the table of part 1)."""
    t = lines[(lines['variant'] == 'absences')].dropna(subset=['actual', 'over_odds', 'under_odds', 'lineup adj'])
    t = t[(t['lineup adj'] != 0) & (t['actual'] != t['line'])]
    t = t.assign(night=pd.to_datetime(t['game_date'])).merge(absent_regulars(logs), on=['team', 'night'])
    over = t['lineup adj'] > 0
    o, u = 1 / t['over_odds'], 1 / t['under_odds']
    t = t.assign(won=np.where(over, t['actual'] > t['line'], t['actual'] < t['line']).astype(float),
                 price=np.where(over, o / (o + u), u / (o + u)), odds=np.where(over, t['over_odds'], t['under_odds']),
                 size=t['lineup adj'].abs() / t['avg'].clip(lower=1))
    rows = []
    for name, lo, hi in GROUPS:
        for size in SIZES:
            s = t[t['game_no'].between(lo, hi) & (t['size'] >= size)]
            rows.append({'game without him': name, 'size ≥ %': 100 * size, **scored(s)})
    return pd.DataFrame(rows)


# --- 2. Superbet ---

def superbet_signals(versions: Dict, offered: pd.DataFrame, logs: pd.DataFrame, team_of: Dict) -> pd.DataFrame:
    """The rule's outputs on every night with RotoWire versions (mispricing_eval's outputs format)."""
    frames = []
    regulars = regulars_by_night(logs, list(versions))
    for night, saved in versions.items():
        before = logs[logs['Date'] < night]
        out = out_tonight(saved, before, night, regulars.get(night, set()))
        tonight = offered[_night(offered['tip']) == night]
        if out.empty or tonight.empty:
            continue
        frames.append(signal_rows(night, out, tonight, before, team_of))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def evaluate(outputs: pd.DataFrame, offered: pd.DataFrame, logs: pd.DataFrame, d, closing=None) -> Dict:
    """{period: economic row + won − price} for 'recognition' (nights ≤ d) and 'evaluation'; also 'first game'
    (game no. 1 only) per period."""
    d = pd.Timestamp(d)
    settled = set(logs['Date'].unique())
    sig = signals(outputs[outputs['night'].isin(settled)], offered, logs, closing) if len(outputs) else outputs
    covered = pd.Series(_night(offered['tip']).unique())
    covered = covered[covered.isin(settled)]
    result = {}
    for period, keep in (('recognition', lambda n: n <= d), ('evaluation', lambda n: n > d)):
        nights = int(keep(covered).sum())
        for part, pick in (('all', lambda s: s), ('first game', lambda s: s[s['game_no'] == 1])):
            s = pick(sig[keep(sig['night'])]) if len(sig) else sig
            row = economic(s, nights)
            done = s[(s['taken'] == 'yes') & s['won'].notna()] if len(s) else s
            if len(done):
                row['won − price pp'] = 100 * (done['won'] - done['price %'] / 100).mean()
            result[f'{period} · {part}'] = row
    return result


def report(history: pd.DataFrame, result: Dict, d) -> str:
    text = ["# H10: a regular ruled Out and his teammates' lines", "", __doc__.split("\n\n", 2)[2].strip(), ""]
    text += [f"## Superbet: evaluation (nights after {d}) decides, recognition (up to {d}) describes", "",
             markdown(pd.DataFrame([{'period': k, **v} for k, v in result.items()])), ""]
    if history is not None:
        text += ["## History: Unibet 2022/23 (known absences, an upper bound)", "",
                 "A side needs about 8–11 pp over the price after tax.", "", markdown(history), ""]
    return "\n".join(text)


def summary(history: pd.DataFrame, result: Dict, d) -> Dict:
    """What the Overview's window says about the record (plain numbers, JSON-safe)."""
    clean = lambda v: None if v is None or (isinstance(v, float) and np.isnan(v)) else \
        (v.item() if isinstance(v, np.generic) else v)
    out = {'d': str(pd.Timestamp(d).date()), 'updated': pd.Timestamp.now(tz='UTC').isoformat(timespec='minutes')}
    for key, row in result.items():
        out[key] = {k: clean(row.get(k)) for k in ('nights', 'signals', 'settled', 'won %', 'won − price pp',
                                                   'ROI after tax %', 'with a close', 'CLV after tax %', 'CLV low',
                                                   'CLV high', 'verdict', 'why')}
    if history is not None and len(history):
        first = history[(history['game without him'] == '1') & (history['size ≥ %'] == 100 * MIN_SHARE)].iloc[0]
        out['2022'] = {k: clean(first.get(k)) for k in ('lines', 'nights', 'won − price pp', 'low', 'high',
                                                         'ROI after tax %')}
    return out


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument('--d', default=D, help="D, the last recognition night (default %(default)s)")
    parser.add_argument('--skip-2022', action='store_true', help="leave out the 2022/23 history (slow)")
    args = parser.parse_args()
    from espn_scraper import SEASONS
    from espn_scraper.storage import load_player_gamelogs, load_snapshot
    from name_resolver import NameResolver
    from tracking import closing_props
    read = load_snapshot

    history = None
    if not args.skip_2022 and os.path.exists(LINES_2022):
        from backtest.data_2022 import load_logs_2022
        logs_2022, _ = load_logs_2022()
        logs_2022 = logs_2022.assign(Date=pd.to_datetime(logs_2022['Date']))
        history = history_2022(pd.read_csv(LINES_2022, low_memory=False), logs_2022)
        log.info("2022/23 history done")

    logs = load_player_gamelogs(sorted(SEASONS))
    logs = add_combined_stats(logs[logs['season_type'] != 'pre'].assign(Date=lambda x: pd.to_datetime(x['Date'])))
    logs['player_id_ESPN'] = logs['player_id_ESPN'].astype('Int64')
    logs['MIN'] = pd.to_numeric(logs['MIN'], errors='coerce')
    props, quotes, fetches = read('superbet_props'), read('superbet_prop_quotes'), read('superbet_event_fetches')
    offered = offers(props, quotes, fetches)
    offered = offered[offered['source'] == 'schedule'].copy()
    offered['player_id_ESPN'] = player_ids(offered, props, logs)
    versions = lineup_versions(NameResolver(logs).add_ids(read('rotowire_lineups')))
    team_of = logs.sort_values('Date').drop_duplicates('player_id_ESPN', keep='last') \
        .set_index('player_id_ESPN')['team'].to_dict()
    outputs = superbet_signals(versions, offered, logs, team_of)
    log.info("%d rule outputs on %d nights", len(outputs), outputs['night'].nunique() if len(outputs) else 0)
    result = evaluate(outputs, offered, logs, args.d, closing_props(quotes, fetches))
    text = report(history, result, args.d)
    atomic_write_text(REPORT_FILE, text)
    atomic_write_text(SUMMARY_FILE, json.dumps(summary(history, result, args.d), indent=2, ensure_ascii=False))
    print(text)


if __name__ == '__main__':
    main()
