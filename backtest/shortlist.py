"""Does ranking a night's lines pick better sides than the price says? The evidence behind decisions.shortlist.

    python -m backtest.shortlist             # after python -m backtest.run

No line clears Superbet's 12% stake tax (metrics.COST_PROFILES), so the dashboards' decision is 'don't bet' every
night. The question here is the relative one: among tonight's lines, are the ones the model ranks first better
than the rest? Two rank keys are compared, each choosing its own side of a line:

    ev            the side with the higher expected return (p × odds), ranked by it: what models.price_props shows
    disagreement  the side whose calibrated chance is furthest above the margin-free price, ranked by that gap

The calibration (a, b) is fitted on the earlier part of each source and the lines are scored on the later part
(2022/23: Nov–Jan / Feb–May; Superbet: all but the latest 30% of nights / those nights, as backtest/calibrate.py
splits them). Pushes are left out. 'won − price pp' is how much more often the chosen sides won than the
margin-free price said: 0 = the ranking knows nothing the price doesn't. ROI is per unit at the line's odds,
before and after the tax. The shortlist rows apply decisions.shortlist's rules (no 🔴, one line per game and one
per player). Writes data/backtest/shortlist.md.
"""
import logging
import os
from typing import Dict

import numpy as np
import pandas as pd

import backtest  # noqa: F401  (puts dashboard/ on the path)
from backtest.calibrate import apply, fit_coefficients, lines_2022, sides, split
from backtest.run import OUT_DIR, markdown
from metrics import COST_PROFILES, SUPERBET_STANDARD, wilson_interval
from safe_io import atomic_write_text

log = logging.getLogger(__name__)

REPORT_FILE = os.path.join(OUT_DIR, 'shortlist.md')
KEYS = ('ev', 'disagreement')
BUCKETS = [0, .02, .05, .10, .25, .50, 1.0]
BUCKET_NAMES = ['top 2%', '2–5%', '5–10%', '10–25%', '25–50%', 'bottom 50%']
SHORTLIST_SIZES = (3, 5, 10)
TAX = COST_PROFILES[SUPERBET_STANDARD]


def chosen_sides(t: pd.DataFrame, coef: Dict, key: str) -> pd.DataFrame:
    """Each line's side under the rank key, with its calibrated chance p, the margin-free price's chance, odds,
    the key's score and whether it won (pushes are NaN)."""
    out = {}
    for side in ('Over', 'Under'):
        market = (t['market over %'] / 100 if side == 'Over' else 1 - t['market over %'] / 100).values
        odds = (t['over_odds'] if side == 'Over' else t['under_odds']).values
        p = apply(coef, market, t[f'raw {side.lower()} %'].values / 100, np.full(len(t), side == 'Over'))
        out[side] = pd.DataFrame({'p': p, 'market': market, 'odds': odds,
                                  'score': p * odds if key == 'ev' else 100 * (p - market)}, index=t.index)
    over = out['Over']['score'] >= out['Under']['score']
    best = out['Over'].where(over, out['Under'])
    margin = (t['actual'] - t['line']) * np.where(over, 1, -1)
    return best.assign(side=np.where(over, 'Over', 'Under'), won=np.where(margin == 0, np.nan, margin > 0))


def scored(t: pd.DataFrame, coef: Dict, key: str) -> pd.DataFrame:
    """t's decided lines with the key's side and the line's rank within its night (1 = best; pct 0–1)."""
    d = pd.concat([t, chosen_sides(t, coef, key)], axis=1)
    d = d[d['won'].notna() & d['odds'].notna()].copy()
    d['night pct'] = d.groupby('game_date')['score'].rank(ascending=False, pct=True, method='first')
    return d


def rates(part: pd.DataFrame) -> Dict:
    wins, n = int(part['won'].sum()), len(part)
    low, high = wilson_interval(wins, n)
    profit = np.where(part['won'] == 1, part['odds'] - 1, -1.0)
    taxed = np.where(part['won'] == 1, TAX * part['odds'] - 1, -1.0)
    return {'lines': n, 'nights': int(part['game_date'].nunique()),
            'won %': 100 * wins / n if n else np.nan, 'ci low %': 100 * low, 'ci high %': 100 * high,
            'price said %': 100 * part['market'].mean() if n else np.nan,
            'won − price pp': 100 * (wins / n - part['market'].mean()) if n else np.nan,
            'ROI %': 100 * profit.mean() if n else np.nan, 'ROI after tax %': 100 * taxed.mean() if n else np.nan}


def bucket_table(d: pd.DataFrame) -> pd.DataFrame:
    """rates() per bucket of the night rank."""
    bucket = pd.cut(d['night pct'], BUCKETS, labels=BUCKET_NAMES)
    return pd.DataFrame([{'rank in the night': name, **rates(d[bucket == name])} for name in BUCKET_NAMES])


def night_shortlist(d: pd.DataFrame, size: int) -> pd.DataFrame:
    """decisions.shortlist's rules on scored lines: no 🔴, best line per game and per player, `size` per night."""
    signal = 'saved signal' if 'saved signal' in d else 'signal'
    if signal in d:
        d = d[d[signal].fillna('') != '🔴']
    d = d.sort_values(['game_date', 'score'], ascending=[True, False], kind='stable')
    d = d.drop_duplicates(['game_date', 'home', 'away']).drop_duplicates(['game_date', 'name_ESPN'])
    return d.groupby('game_date', sort=False).head(size)


def shortlist_table(d: pd.DataFrame) -> pd.DataFrame:
    rows = [{'lines bet': f"shortlist, top {size} a night", **rates(night_shortlist(d, size))}
            for size in SHORTLIST_SIZES]
    return pd.DataFrame(rows + [{'lines bet': "every line (the key's side)", **rates(d)}])


def report(sources: Dict[str, pd.DataFrame]) -> str:
    parts = {name: split(t) for name, t in sources.items() if len(t)}
    coef = fit_coefficients(pd.concat([sides(fit_part) for fit_part, _ in parts.values()], ignore_index=True))
    text = ["# Ranking a night's lines: the evidence behind the shortlist", "",
            __doc__.split("\n\n", 2)[2].strip(), "",
            "Calibration fitted on the earlier lines: " + ", ".join(f"{k} = {v:.3f}" for k, v in coef.items()), ""]
    for name, (_, test) in parts.items():
        if test.empty:
            continue
        label = {'2022': "Unibet 2022/23", 'superbet': "Superbet 2026/27"}[name]
        for key in KEYS:
            d = scored(test, coef, key)
            text += [f"## {label}, key '{key}': {len(d)} unseen lines, {d['game_date'].nunique()} nights", "",
                     markdown(bucket_table(d)), "", markdown(shortlist_table(d)), ""]
    return "\n".join(text)


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    from backtest.calibrate import _superbet_sources
    from espn_scraper import SEASONS
    from espn_scraper.storage import load_games, load_player_gamelogs
    from models import prepare_logs
    games = load_games(sorted(SEASONS))
    sources = {'2022': lines_2022(),
               'superbet': _superbet_sources(prepare_logs(load_player_gamelogs(sorted(SEASONS))), games)}
    text = report(sources)
    atomic_write_text(REPORT_FILE, text)
    print(text)


if __name__ == '__main__':
    main()
