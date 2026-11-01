"""Can an edge threshold earn 5★? The admission procedure for decisions.ADMITTED_THRESHOLD (docs §8.1).

    python -m backtest.threshold_admission [--until YYYY-MM-DD]

The 🟢 threshold of backtest/calibrate.py is chosen on the same held-out nights it's judged on, so it doesn't
qualify. Here the two steps get separate nights:

  1. Choose, on the saved Superbet lines of nights up to D: the calibration is fitted there (calibrate.FITTED) and
     the threshold is the smallest candidate edge after tax (edge net pp) whose bets made money after the 12% stake
     tax over at least MIN_CHOOSE_BETS bets and MIN_CHOOSE_NIGHTS nights.
  2. Judge it on the nights after D, which neither step has seen (at least MIN_JUDGED_NIGHTS). The bets are what
     decisions.player_decision would offer: per game, the best line without 🔴 whose edge net pp clears the
     threshold. Admitted when the low end of the after-tax ROI's 95% range is above 0, or the mean after-tax CLV
     is above 0 with its low end above 0 (bets with a valid close, tracking.closing_props).

Ranges are 95% from resampling whole nights. D defaults to the last night that leaves MIN_JUDGED_NIGHTS after it.
The report never sets ADMITTED_THRESHOLD: that's done by hand after reading it. Writes
data/backtest/threshold_admission.md.
"""
import argparse
import logging
import os
from typing import Dict, Optional

import numpy as np
import pandas as pd

import backtest  # noqa: F401  (puts dashboard/ on the path)
from backtest.ablation import night_bootstrap
from backtest.calibrate import apply, fit_coefficients, sides
from backtest.run import OUT_DIR, markdown
from metrics import COST_PROFILES, SUPERBET_STANDARD
from safe_io import atomic_write_text

log = logging.getLogger(__name__)

REPORT_FILE = os.path.join(OUT_DIR, 'threshold_admission.md')
CANDIDATES = (0, 1, 2, 3, 5, 8)          # edge net pp, smallest first
MIN_CHOOSE_BETS = 50
MIN_CHOOSE_NIGHTS = 10
MIN_JUDGED_NIGHTS = 20
TAX = COST_PROFILES[SUPERBET_STANDARD]


def bets(t: pd.DataFrame, coef: Dict, threshold: float) -> pd.DataFrame:
    """Per game and night, the line player_decision would offer at `threshold`: the best side by calibrated
    chance, edge net pp = chance − the after-tax break-even, kept when ≥ threshold and its expected return after
    tax > 0; no 🔴 (saved signal); the game's best by expected return. Adds side, p, odds, edge net pp, won (NaN on
    a push) and profit std (per unit, after tax)."""
    out = {}
    for side in ('Over', 'Under'):
        market = (t['market over %'] / 100 if side == 'Over' else 1 - t['market over %'] / 100).values
        odds = (t['over_odds'] if side == 'Over' else t['under_odds']).values
        p = apply(coef, market, t[f'raw {side.lower()} %'].values / 100, np.full(len(t), side == 'Over'))
        out[side] = pd.DataFrame({'p': p, 'odds': odds, 'ev': p * TAX * odds - 1}, index=t.index)
    over = out['Over']['ev'] >= out['Under']['ev']
    best = out['Over'].where(over, out['Under']).assign(side=np.where(over, 'Over', 'Under'))
    best['edge net pp'] = 100 * (best['p'] - 1 / (TAX * best['odds']))
    d = pd.concat([t, best], axis=1)
    clean = d['saved signal'].fillna('') != '🔴' if 'saved signal' in d else True
    d = d[clean & (d['edge net pp'] >= threshold) & (d['ev'] > 0) & d['odds'].notna()]
    d = d.sort_values('ev', ascending=False, kind='stable').drop_duplicates(['game_date', 'home', 'away'])
    margin = (d['actual'] - d['line']) * np.where(d['side'] == 'Over', 1, -1)
    d = d.assign(won=np.where(margin == 0, np.nan, margin > 0))
    return d.assign(**{'profit std': np.select([d['won'] == 1, d['won'] == 0], [TAX * d['odds'] - 1, -1.0], 0.0)})


def rates(b: pd.DataFrame) -> Dict:
    decided = b[b['won'].notna()]
    nights = decided['game_date'].values
    roi = 100 * decided['profit std'].values
    low, high = night_bootstrap(nights, roi)
    row = {'bets': len(decided), 'nights': int(decided['game_date'].nunique()),
           'won %': 100 * decided['won'].mean() if len(decided) else np.nan,
           'ROI after tax %': roi.mean() if len(decided) else np.nan, 'ROI low': low, 'ROI high': high}
    if 'clv % std' in b:
        clv = b[b['clv % std'].notna()]
        c_low, c_high = night_bootstrap(clv['game_date'].values, clv['clv % std'].values)
        row |= {'bets with a close': len(clv), 'CLV after tax %': clv['clv % std'].mean() if len(clv) else np.nan,
                'CLV low': c_low, 'CLV high': c_high}
    return row


def choose(t: pd.DataFrame, coef: Dict, candidates=CANDIDATES) -> tuple:
    """(the threshold chosen on t, the scan of every candidate)."""
    scan = pd.DataFrame([{'edge net pp ≥': c, **rates(bets(t, coef, c))} for c in candidates])
    ok = scan[(scan['bets'] >= MIN_CHOOSE_BETS) & (scan['nights'] >= MIN_CHOOSE_NIGHTS)
              & (scan['ROI after tax %'] > 0)]
    return (float(ok['edge net pp ≥'].iloc[0]) if len(ok) else None), scan


def default_until(t: pd.DataFrame) -> Optional[pd.Timestamp]:
    nights = sorted(t['game_date'].unique())
    enough = len(nights) >= MIN_CHOOSE_NIGHTS + MIN_JUDGED_NIGHTS
    return pd.Timestamp(nights[-MIN_JUDGED_NIGHTS - 1]) if enough else None


def admit(t: pd.DataFrame, until=None, closing: Optional[pd.DataFrame] = None) -> Dict:
    """The procedure on Superbet lines t (calibrate.superbet_lines, with event_id for the closes). Returns
    {'admitted' (the threshold or None), 'why', 'until', 'threshold', 'scan', 'judged'}."""
    out = {'admitted': None, 'threshold': None, 'scan': pd.DataFrame(), 'judged': None}
    until = pd.Timestamp(until) if until is not None else default_until(t)
    out['until'] = until
    nights = t['game_date'].nunique() if len(t) else 0
    if until is None:
        return out | {'why': f"too few nights: {nights} of the {MIN_CHOOSE_NIGHTS + MIN_JUDGED_NIGHTS} it needs "
                             f"({MIN_CHOOSE_NIGHTS} to choose on, {MIN_JUDGED_NIGHTS} after them to judge on)"}
    early, later = t[t['game_date'] <= until], t[t['game_date'] > until]
    if early['game_date'].nunique() < MIN_CHOOSE_NIGHTS or later['game_date'].nunique() < MIN_JUDGED_NIGHTS:
        return out | {'why': f"too few nights: {early['game_date'].nunique()} to choose on (needs "
                             f"{MIN_CHOOSE_NIGHTS}), {later['game_date'].nunique()} to judge on (needs "
                             f"{MIN_JUDGED_NIGHTS})"}
    coef = fit_coefficients(sides(early))
    threshold, scan = choose(early, coef)
    out |= {'threshold': threshold, 'scan': scan}
    if threshold is None:
        return out | {'why': "no candidate made money after tax on the nights it was chosen on"}
    judged = bets(later, coef, threshold)
    if closing is not None and len(judged) and 'event_id' in judged:
        from tracking import add_clv
        judged = add_clv(judged.assign(pick=judged['side']), closing)
    result = rates(judged)
    out['judged'] = result
    roi_ok = result['ROI low'] > 0
    clv_ok = result.get('CLV after tax %', np.nan) > 0 and result.get('CLV low', np.nan) > 0
    if roi_ok or clv_ok:
        return out | {'admitted': threshold, 'why': "the after-tax " + ("ROI" if roi_ok else "CLV") +
                      "'s range is above 0 on the nights after the choice"}
    return out | {'why': "on the nights after the choice neither the after-tax ROI's nor CLV's range is above 0"}


def report(t: pd.DataFrame, until=None, closing: Optional[pd.DataFrame] = None) -> str:
    r = admit(t, until, closing)
    text = ["# Admitting an edge threshold (5★)", "", __doc__.split("\n\n", 2)[2].strip(), "",
            f"Superbet lines: {len(t)} over {t['game_date'].nunique() if len(t) else 0} nights."
            + (f" Chosen on nights up to {r['until']:%b %d %Y}, judged on the later ones." if r['until'] is not None
               else ""), "",
            f"**Result: {'admitted, edge net pp ≥ %g' % r['admitted'] if r['admitted'] is not None else 'none'}** "
            f"({r['why']}).", ""]
    if len(r['scan']):
        text += ["## Choosing (nights up to D)", "", markdown(r['scan']), ""]
    if r['judged'] is not None:
        text += [f"## Judging edge net pp ≥ {r['threshold']:g} (nights after D)", "",
                 markdown(pd.DataFrame([r['judged']])), ""]
    return "\n".join(text)


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument('--until', help="D, the last night to choose on (default: leaves %d nights to judge on)"
                        % MIN_JUDGED_NIGHTS)
    args = parser.parse_args()
    from backtest.calibrate import _superbet_sources
    from espn_scraper import CURRENT_SEASON, SEASONS
    from espn_scraper.storage import load_games, load_player_gamelogs, read_snapshot, snapshot_file
    from models import prepare_logs
    from tracking import closing_props
    read = lambda name: read_snapshot(snapshot_file(CURRENT_SEASON, name)) \
        if os.path.exists(snapshot_file(CURRENT_SEASON, name)) else pd.DataFrame()
    t = _superbet_sources(prepare_logs(load_player_gamelogs(sorted(SEASONS))), load_games(sorted(SEASONS)))
    text = report(t, args.until, closing_props(read('superbet_prop_quotes'), read('superbet_event_fetches')))
    atomic_write_text(REPORT_FILE, text)
    print(text)


if __name__ == '__main__':
    main()
