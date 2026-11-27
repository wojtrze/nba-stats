"""Would an extra calibration term help? Held-out test of terms beyond a and b (plan B1, 27.11).

    python -m backtest.calibration_terms

The live calibration (backtest/calibrate.py) is sigmoid(a·logit(market) + b·(logit(model) − logit(market))), with
c and d held at 0. Each variant below adds terms and is fitted on the fit part of a source and scored on its held-out
part (calibrate.split: Superbet's latest HOLD_OUT of nights, 2022/23 from SPLIT on):

  over    a signed Over/Under bias: +1 for an Over side, −1 for an Under side
  small   the same sign, only on lines of 1.5 or less
  b_main  an extra weight on the model's opinion for the main stats (PTS, PA, PR, PRA, RA)

A term is adopted only when, on the Superbet held-out nights, (a) the log loss against 'base a,b' improves with the
top of its 95% night-bootstrap range below 0, and (b) the 4★ lines it ranks don't win less over their price than the
base's. 2022/23 is shown as a check that a gain isn't a Superbet artefact. 4★ here is approximate: per line the side
with the higher expected return after the 12% tax, then decisions.star_levels (top 5% of the night, the player's best
line, one per game). The report never changes the calibration: that's done by hand after reading it. Writes
data/backtest/calibration_terms.md.
"""
import argparse
import logging
import os
import sys
from typing import Dict, List

import numpy as np
import pandas as pd

import backtest  # noqa: F401  (puts dashboard/ on the path)
from backtest import calibrate as C
from backtest.ablation import night_bootstrap
from backtest.run import OUT_DIR, markdown
from safe_io import atomic_write_text

log = logging.getLogger(__name__)

REPORT_FILE = os.path.join(OUT_DIR, 'calibration_terms.md')
MAIN_STATS = {'PTS', 'PA', 'PR', 'ARP', 'RA'}
SMALL_LINE = 1.5
TAX_KEEP = 0.88                          # Superbet keeps 12% of the stake
BASE = 'base a,b'
VARIANTS = {BASE: ['a', 'b'], '+over': ['a', 'b', 'over'], '+small': ['a', 'b', 'small'],
            '+over+small': ['a', 'b', 'over', 'small'], '+b_main': ['a', 'b', 'b_main'],
            '+all': ['a', 'b', 'over', 'small', 'b_main']}


def line_sides(t: pd.DataFrame) -> pd.DataFrame:
    """calibrate.sides with each line's bet_type, line, event_id and name_ESPN (2022 lines without event_id get one
    from date and home team)."""
    if 'event_id' not in t:
        t = t.assign(event_id=t['game_date'].astype(str) + t['home'].astype(str))
    s = C.sides(t)
    rows = t.loc[s['line_id']]
    return s.assign(**{col: rows[col].values for col in ('bet_type', 'line', 'event_id', 'name_ESPN')})


def features(s: pd.DataFrame, terms: List[str]) -> np.ndarray:
    """The columns of `terms` for line sides s."""
    lm = C._logit(s['market'].values)
    diff = C._logit(s['model'].values) - lm
    sign = np.where(s['over'].values, 1.0, -1.0)
    cols = {'a': lm, 'b': diff, 'over': sign, 'small': sign * (s['line'].values <= SMALL_LINE),
            'b_main': diff * s['bet_type'].isin(MAIN_STATS).values}
    return np.column_stack([cols[k] for k in terms])


def log_loss(y: np.ndarray, p: np.ndarray) -> np.ndarray:
    """Per-row log loss."""
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def four_star(s: pd.DataFrame, p: np.ndarray) -> pd.DataFrame:
    """The approximate 4★ sides of line sides s under chances p (see the module doc)."""
    from decisions import star_levels
    d = s.assign(p=p, ev=p * TAX_KEEP * s['odds'] - 1)
    d = d.sort_values('ev', ascending=False).drop_duplicates('line_id')
    d = d.sort_values(['game_date', 'ev'], ascending=[True, False], kind='stable')
    night = d.groupby('game_date')['game_date']
    d['pct'] = 100 * (night.cumcount() + 1) / night.transform('size')
    best = ~d[['game_date', 'name_ESPN']].duplicated()
    level = star_levels(d['pct'], pd.Series(True, index=d.index), best, d['game_date'], d['event_id'])
    return d[level == 4]


def evaluate(t: pd.DataFrame, source: str) -> pd.DataFrame:
    """One row per variant of VARIANTS for one source's lines: coefficients, held-out log loss and its difference
    to the base with a 95% range, and the 4★ count, won %, price %, won − price (with range) and after-tax ROI."""
    fit_part, test = C.split(t)
    tr, te = line_sides(fit_part), line_sides(test)
    y = te['won'].values
    base_loss, rows = None, []
    for name, terms in VARIANTS.items():
        beta = C.fit(features(tr, terms), tr['won'].values)
        p = C._sigmoid(features(te, terms) @ beta)
        loss = log_loss(y, p)
        base_loss = loss if base_loss is None else base_loss
        lo, hi = night_bootstrap(te['game_date'].values, loss - base_loss)
        top = four_star(te, p)
        above = 100 * (top['won'] - top['market'])
        x_lo, x_hi = night_bootstrap(top['game_date'].values, above.values)
        rows.append({'source': source, 'variant': name,
                     'coefficients': ' '.join(f'{k}={v:+.3f}' for k, v in zip(terms, beta)),
                     'held-out log loss': loss.mean(), 'Δ vs base': (loss - base_loss).mean(),
                     'Δ low': lo, 'Δ high': hi, '4★ lines': len(top), '4★ won %': 100 * top['won'].mean(),
                     '4★ price %': 100 * top['market'].mean(), '4★ won − price': above.mean(),
                     'won − price low': x_lo, 'won − price high': x_hi,
                     '4★ after tax %': 100 * (top['won'] * TAX_KEEP * top['odds'] - 1).mean()})
    out = pd.DataFrame(rows)
    out.attrs['period'] = (f"fit {fit_part['game_date'].min():%Y-%m-%d}…{fit_part['game_date'].max():%Y-%m-%d} "
                           f"({len(fit_part)} lines), held out {test['game_date'].min():%Y-%m-%d}…"
                           f"{test['game_date'].max():%Y-%m-%d} ({len(test)} lines); market log loss "
                           f"{log_loss(y, te['market'].values).mean():.4f}")
    return out


def verdicts(superbet: pd.DataFrame) -> pd.DataFrame:
    """Per variant of the Superbet rows: (a) log loss better with the range below 0, (b) 4★ won − price not below
    the base's, and adopted = both."""
    base = superbet.loc[superbet['variant'] == BASE, '4★ won − price'].iloc[0]
    rows = superbet[superbet['variant'] != BASE]
    return pd.DataFrame({'variant': rows['variant'],
                         '(a) log loss': np.where(rows['Δ high'] < 0, 'pass', 'fail'),
                         '(b) 4★ won − price': np.where(rows['4★ won − price'] >= base, 'pass', 'fail'),
                         'adopt': np.where((rows['Δ high'] < 0) & (rows['4★ won − price'] >= base), 'yes', 'no')})


def report(sources: Dict[str, pd.DataFrame]) -> str:
    """The markdown report of evaluate per non-empty source and the Superbet verdicts."""
    parts = ["# Extra calibration terms, held out", "",
             "Each variant fitted on the fit part and scored on unseen nights (see backtest/calibration_terms.py). "
             "Δ = log loss minus the base's (negative is better); ranges are 95% from resampling whole nights. "
             "4★ is approximate and small: read its won − price range, not just the mean.", ""]
    results = {}
    for source, t in sources.items():
        if t is None or t.empty:
            continue
        results[source] = r = evaluate(t, source)
        parts += [f"## {C.SOURCE_NAMES.get(source, source)}", "", r.attrs['period'], "",
                  markdown(r.drop(columns='source').round(4), floats='{:.4g}'), ""]
    if 'superbet' in results:
        parts += ["## Verdict (Superbet held-out nights)", "", markdown(verdicts(results['superbet'])), "",
                  "The live calibration is changed by hand only (calibrate.FITTED and features), never by this "
                  "report.", ""]
    return "\n".join(parts)


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    argparse.ArgumentParser(description=__doc__.split("\n")[0]).parse_args()
    from espn_scraper import SEASONS
    from espn_scraper.storage import load_games, load_player_gamelogs
    from models import prepare_logs
    superbet = C._superbet_sources(prepare_logs(load_player_gamelogs(sorted(SEASONS))), load_games(sorted(SEASONS)))
    lines_2022 = C.lines_2022() if os.path.exists(C.LINES_FILE) else pd.DataFrame()
    text = report({'superbet': superbet, '2022': lines_2022})
    atomic_write_text(REPORT_FILE, text)
    sys.stdout.reconfigure(errors='replace')   # a Windows console's code page lacks − and ★
    print(text)


if __name__ == '__main__':
    main()
