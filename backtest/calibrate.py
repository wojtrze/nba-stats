"""Fit the props model's calibration (metrics.calibrate) on the 2022/23 backtest and check it on unseen games.

    python -m backtest.calibrate        # after python -m backtest.run

Fits a, b, c, d of sigmoid(a·logit(market) + b·(logit(model) − logit(market)) + c·[Over] + d) on Nov–Jan,
reports how the fit does on Feb–May (games it never saw), then refits on the whole season and writes the
coefficients the dashboards use to data/backtest/calibration.json, and the report to
data/backtest/2022_calibration.md.
"""
import argparse
import json
import os
from datetime import date
from typing import Dict, Tuple

import numpy as np
import pandas as pd

import backtest  # noqa: F401  (puts dashboard/ on the path)
from backtest.run import MIN_GAMES, OUT_DIR, markdown, rate_row
from metrics import IDENTITY_CALIBRATION
from models import CALIBRATION_FILE

LINES_FILE = os.path.join(OUT_DIR, '2022_lines.csv')
SPLIT = pd.Timestamp('2023-02-01')       # fit before, check from this date on
COEFS = ['a', 'b', 'c', 'd']


def _logit(p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def _sigmoid(z):
    return 1 / (1 + np.exp(-z))


def features(market, model, over) -> np.ndarray:
    """The columns a, b, c, d multiply (metrics.calibrate)."""
    m = np.where(np.isnan(market), 0.5, market)
    return np.column_stack([_logit(m), _logit(model) - _logit(m), np.asarray(over, dtype=float), np.ones(len(m))])


def apply(coef: Dict, market, model, over) -> np.ndarray:
    """metrics.calibrate on arrays."""
    return _sigmoid(features(market, model, over) @ np.array([coef[k] for k in COEFS]))


def fit(X: np.ndarray, y: np.ndarray, iterations: int = 50) -> np.ndarray:
    """Logistic regression by Newton's method (no intercept added: X carries its own column of ones)."""
    beta = np.zeros(X.shape[1])
    for _ in range(iterations):
        p = _sigmoid(X @ beta)
        hessian = X.T @ (X * (p * (1 - p))[:, None])
        step = np.linalg.solve(hessian, X.T @ (y - p))
        beta += step
        if np.abs(step).max() < 1e-10:
            break
    return beta


def sides(t: pd.DataFrame) -> pd.DataFrame:
    """One row per line and side, decided lines only (pushes out): market, model (raw), over, won, odds."""
    rows = []
    for side, won in (('Over', t['actual'] > t['line']), ('Under', t['actual'] < t['line'])):
        market = t['market over %'] / 100 if side == 'Over' else 1 - t['market over %'] / 100
        rows.append(pd.DataFrame({'game_date': t['game_date'], 'line_id': t.index, 'side': side,
                                  'market': market, 'model': t[f'raw {side.lower()} %'] / 100,
                                  'low': t[f'raw {side.lower()} low %'] / 100,
                                  'over': side == 'Over', 'won': won.astype(float),
                                  'odds': t['over_odds'] if side == 'Over' else t['under_odds']}))
    s = pd.concat(rows, ignore_index=True)
    decided = t.index[t['actual'] != t['line']]
    return s[s['line_id'].isin(decided) & s['model'].notna() & s['odds'].notna()]


def fit_coefficients(s: pd.DataFrame) -> Dict:
    beta = fit(features(s['market'].values, s['model'].values, s['over'].values), s['won'].values)
    return dict(zip(COEFS, map(float, beta)))


def scores(s: pd.DataFrame, p: np.ndarray) -> Dict:
    """Log loss and Brier score of chances p for the rows of s (lower is better)."""
    y, p = s['won'].values, np.clip(p, 1e-4, 1 - 1e-4)
    return {'log loss': float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean()),
            'Brier': float(((p - y) ** 2).mean())}


def picks(t: pd.DataFrame, coef: Dict) -> pd.DataFrame:
    """Each line's pick under the calibration: the side with the bigger calibrated edge, its odds and signal."""
    out = {}
    for side in ('Over', 'Under'):
        market = t['market over %'] / 100 if side == 'Over' else 1 - t['market over %'] / 100
        odds = t['over_odds'] if side == 'Over' else t['under_odds']
        p = apply(coef, market.values, t[f'raw {side.lower()} %'].values / 100, np.full(len(t), side == 'Over'))
        low = apply(coef, market.values, t[f'raw {side.lower()} low %'].values / 100, np.full(len(t), side == 'Over'))
        out[side] = pd.DataFrame({'p': p, 'edge': p - 1 / odds.values, 'edge low': low - 1 / odds.values,
                                  'odds': odds.values}, index=t.index)
    over_better = out['Over']['edge'] >= out['Under']['edge']
    best = out['Over'].where(over_better, out['Under'])
    signal = np.select([best['edge low'] > 0, best['edge'] > 0], ['🟢', '🟡'], '')
    return best.assign(side=np.where(over_better, 'Over', 'Under'), signal=signal)


def strategy_rows(t: pd.DataFrame, coef: Dict) -> pd.DataFrame:
    calibrated = picks(t, coef)
    under = pd.Series('Under', index=t.index)
    rows = {"Always Under": (under, t['under_odds']),
            "Uncalibrated model pick, edge > 0": (t['best side'].where(t['edge pp'] > 0), t['pick odds']),
            "Uncalibrated model pick, 🟢": (t['best side'].where(t['signal'] == '🟢'), t['pick odds']),
            "Calibrated pick, edge > 0": (calibrated['side'].where(calibrated['edge'] > 0), calibrated['odds']),
            "Calibrated pick, 🟢": (calibrated['side'].where(calibrated['signal'] == '🟢'), calibrated['odds'])}
    return pd.DataFrame([{'strategy': name, **rate_row(t, side, odds)} for name, (side, odds) in rows.items()])


def calibration_table(s: pd.DataFrame, p: np.ndarray, width: float = 0.05) -> pd.DataFrame:
    """Rows grouped by predicted chance: how many, the average prediction, how often they won."""
    low = (np.floor(p / width) * width * 100).round().astype(int)
    d = s.assign(p=p, chance=[f"{x}–{x + round(100 * width)}%" for x in low], low=low)
    g = d.groupby(['low', 'chance'])
    return pd.DataFrame({'rows': g.size(), 'predicted %': 100 * g['p'].mean(),
                         'won %': 100 * g['won'].mean()}).reset_index().drop(columns='low')


def evaluate(t: pd.DataFrame) -> Tuple[Dict, str]:
    """Fit on the lines before SPLIT, score the lines from SPLIT on; returns (held-out metrics, report)."""
    train, test = t[t['game_date'] < SPLIT], t[t['game_date'] >= SPLIT]
    s_train, s_test = sides(train), sides(test)
    coef = fit_coefficients(s_train)
    args = s_test['market'].values, s_test['model'].values, s_test['over'].values
    candidates = {'Market (margin-free price)': s_test['market'].values,
                  'Uncalibrated model': s_test['model'].values,
                  'Calibrated model': apply(coef, *args)}
    score_rows = pd.DataFrame([{'chances': name, **scores(s_test, p)} for name, p in candidates.items()])
    report = [f"## Held-out check: fitted on {train['game_date'].min():%b %d} – {SPLIT - pd.Timedelta(days=1):%b %d} "
              f"({len(train)} lines), scored on {SPLIT:%b %d} – {test['game_date'].max():%b %d} ({len(test)} lines)",
              "", "Coefficients fitted on the first part: " + ", ".join(f"{k} = {v:.3f}" for k, v in coef.items()),
              "", "### How well the chances predict the results (lower is better)", "",
              markdown(score_rows, '{:.4f}'),
              "", "### Betting the unseen lines (1 unit each, at the line's odds)", "",
              markdown(strategy_rows(test, coef)),
              "", "### Calibration of the calibrated model on the unseen lines (both sides of every line)", "",
              markdown(calibration_table(s_test, candidates['Calibrated model']))]
    held_out = {'fit on': f"{train['game_date'].min():%Y-%m-%d} – {SPLIT - pd.Timedelta(days=1):%Y-%m-%d}",
                'scored on': f"{SPLIT:%Y-%m-%d} – {test['game_date'].max():%Y-%m-%d}",
                'coefficients': coef, 'scores': score_rows.set_index('chances').to_dict('index')}
    return held_out, "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--lines', default=LINES_FILE)
    parser.add_argument('--out', default=CALIBRATION_FILE)
    args = parser.parse_args()

    t = pd.read_csv(args.lines, parse_dates=['game_date'])
    t = t[(t['variant'] == 'none') & t['main'] & (t['games'] >= MIN_GAMES)].reset_index(drop=True)
    held_out, report = evaluate(t)
    everything = sides(t)
    coef = fit_coefficients(everything)
    result = {'coefficients': coef, 'fitted_on': date.today().isoformat(),
              'source': "Unibet 2022/23 main lines, players with 5+ games, backtest variant 'none'",
              'rows': int(len(everything)), 'lines': int(everything['line_id'].nunique()), 'held_out': held_out,
              'identity': IDENTITY_CALIBRATION}
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    text = "\n".join(["# Calibration of the props model on 2022/23", "",
                      "The model's chance for a side is mapped to sigmoid(a·logit(market) + b·(logit(model) − "
                      "logit(market)) + c·[Over] + d): a = weight of the bookmaker's margin-free chance, b = weight "
                      "of the model's opinion beyond it, c = Over/Under bias, d = offset. Identity: a = b = 1, "
                      "c = d = 0.", "", report, "",
                      "## Coefficients used by the dashboards (fitted on the whole season)", "",
                      ", ".join(f"{k} = {v:.3f}" for k, v in coef.items()) +
                      f" ({result['lines']} lines, {result['rows']} line sides)", ""])
    with open(os.path.join(os.path.dirname(args.out), '2022_calibration.md'), 'w', encoding='utf-8') as f:
        f.write(text)
    print(text)


if __name__ == '__main__':
    main()
