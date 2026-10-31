"""Fit the props model's calibration (metrics.calibrate) and its 🟢 threshold, and check both on unseen lines.

    python -m backtest.calibrate                 # after python -m backtest.run
    python -m backtest.calibrate --no-superbet   # the 2022/23 lines only (as before Superbet lines were saved)

Fits a and b of sigmoid(a·logit(market) + b·(logit(model) − logit(market)) + c·[Over] + d) on two sources (c and d,
the Over/Under bias and offset, are kept at 0: see FITTED):
Unibet's 2022/23 lines (the backtest) and every settled Superbet line saved by daily_snapshot.py (its last fetch
before tip-off, with the raw chances saved alongside). Only chances of the current model (nightly.MODEL_VERSION)
are used: a Superbet line's own if that version priced it, else its replay (daily_snapshot.py --reprice); the
2022/23 lines when backtest.run was run with it. The held-out check fits on the earlier part of each source
(2022: Nov–Jan; Superbet: all but the latest HOLD_OUT share of nights) and scores the rest. The 🟢 threshold is the
smallest edge (GREEN_CANDIDATES) whose held-out Superbet picks span MIN_GREEN_NIGHTS+ nights and MIN_GREEN_BETS+
bets and whose hit rate's 95% range lies above their break-even; none = no 🟢. It's chosen on the same held-out
nights it's judged on and re-chosen as nights settle, so it is exploratory, not a proven advantage.
Then everything is refitted for the dashboards: data/backtest/calibration.json (coefficients, green_edge_pp and
superbet_through, the last settled night used) and the report data/backtest/calibration.md. The report ends with
the game markets: their model isn't calibrated, so it tracks how its chances do against the margin-free price.

refresh() refits when a newer Superbet night has settled or the model version changed; daily_snapshot.py calls
it before pricing a fetch.
"""
import argparse
import json
import logging
import os
import sys
from datetime import date
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

import backtest  # noqa: F401  (puts dashboard/ on the path)
from backtest.run import MIN_GAMES, OUT_DIR, markdown, rate_row
from metrics import IDENTITY_CALIBRATION, no_vig_pairs, prop_signal, wilson_interval
from models import CALIBRATION_FILE
from nightly import MODEL_VERSION
from safe_io import atomic_write_text, locked

log = logging.getLogger(__name__)

LINES_FILE = os.path.join(OUT_DIR, '2022_lines.csv')
REPORT_FILE = os.path.join(OUT_DIR, 'calibration.md')
SPLIT = pd.Timestamp('2023-02-01')       # 2022: fit before, check from this date on
HOLD_OUT = 0.3                           # Superbet: the latest share of nights kept for the check
GREEN_CANDIDATES = (1, 2, 3, 4, 5)       # edge thresholds (pp) tried for 🟢, smallest first
MIN_GREEN_BETS = 50
MIN_GREEN_NIGHTS = 10                    # one or two nights are one or two slates of correlated lines, not evidence
COEFS = ['a', 'b', 'c', 'd']
# the coefficients fitted; the rest stay 0. The Over/Under bias (c) and offset (d) are left out: on Unibet 2022/23
# they helped (Overs were overpriced there), on the unseen Superbet nights they made the chances worse than the price,
# and fitted per bookmaker they were worse still (backtest/ablation.py, "calibration form")
FITTED = ['a', 'b']
# 2022_lines.csv written before backtest.run saved model_version: its raw chances are those of this version
# (price_props' chances haven't changed since it was generated, at 954ac54)
LEGACY_2022_VERSION = '2026-10-26'


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


# --- the lines: 2022/23 backtest and settled Superbet snapshots, in one shape ---

def lines_2022(path: str = LINES_FILE, version: str = MODEL_VERSION) -> pd.DataFrame:
    """The backtest's main lines of players with MIN_GAMES+ games (variant 'none') priced by model `version`,
    source '2022'. Empty when the backtest was run with another version (run it again)."""
    t = pd.read_csv(path, parse_dates=['game_date'])
    priced_by = t['model_version'].astype(str) if 'model_version' in t else LEGACY_2022_VERSION
    t = t[(t['variant'] == 'none') & t['main'] & (t['games'] >= MIN_GAMES) & (priced_by == version)]
    return t.assign(source='2022').reset_index(drop=True)


def superbet_lines(snapshots: pd.DataFrame, logs: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    """Every saved Superbet line judged by its last fetch before tip-off, settled against the stats, in the
    backtest's columns (game_date, line, actual, over/under odds, market over %, raw over/under %) with the saved
    edge and signal; source 'superbet'. Only lines saved with the raw chances; voids and pending games left out.
    logs: prepare_logs output; games: games.csv rows (date parsed)."""
    from nightly import et_night
    from tracking import PROP_KEY, settle_props
    columns = ['raw_over_pct', 'raw_under_pct', 'market_over_pct']
    if snapshots.empty or not set(columns) <= set(snapshots.columns):
        return pd.DataFrame()
    fetched = pd.to_datetime(snapshots['fetched_at'], utc=True)
    rows = snapshots[(fetched < pd.to_datetime(snapshots['start_time'], utc=True))
                     & snapshots[columns].notna().all(axis=1)].sort_values('fetched_at', kind='stable')
    last = rows.drop_duplicates(PROP_KEY, keep='last').reset_index(drop=True)
    if last.empty:
        return pd.DataFrame()
    settled = settle_props(snapshots, logs, games, bets=last)       # keeps the order of the bets it's given
    t = last.assign(game_date=et_night(last['start_time']), actual=settled['actual'].values,
                    status=settled['status'].values)
    t = t[t['status'] == 'settled']
    return pd.DataFrame({'game_date': t['game_date'], 'bet_type': t['bet_type'], 'line': t['line'],
                         'actual': t['actual'], 'over_odds': t['over_odds'], 'under_odds': t['under_odds'],
                         'market over %': t['market_over_pct'], 'raw over %': t['raw_over_pct'],
                         'raw under %': t['raw_under_pct'], 'saved edge pp': t['edge_pp'],
                         'saved signal': t['signal'], 'source': 'superbet'}).reset_index(drop=True)


# --- game markets: not calibrated yet; the report tracks how the game model's chances hold up ---

GAME_CALIBRATION_MIN = 300               # settled main-line outcomes (over GAME_CALIBRATION_NIGHTS+) before a fit
GAME_CALIBRATION_NIGHTS = 10


def game_lines(snapshots: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    """Every game outcome that was Superbet's main line, judged by its last fetch before tip-off and settled:
    game_date, market, side, line, odds, market % (margin-free, from the two sides of the same fetch), model %
    (saved with the fetch), edge pp and won (1 / 0; pushes and pending games left out)."""
    from nightly import et_night
    from tracking import GAME_KEY, settle_games
    if snapshots.empty or 'model_pct' not in snapshots:
        return pd.DataFrame()
    s = snapshots.copy()
    # the two sides of one market in one fetch: a handicap's are -x and +x, the rest share the line
    s['market %'] = 100 * no_vig_pairs(s, by=('fetched_at', 'event_id'))
    fetched = pd.to_datetime(s['fetched_at'], utc=True)
    last = s[fetched < pd.to_datetime(s['start_time'], utc=True)].sort_values('fetched_at', kind='stable')         .drop_duplicates(GAME_KEY, keep='last').reset_index(drop=True)
    if last.empty:
        return pd.DataFrame()
    settled = settle_games(snapshots, games, bets=last)
    t = last.assign(game_date=et_night(last['start_time']), result=settled['result'].values,
                    main=settled['main'].values)
    t = t[t['main'] & t['result'].isin(['win', 'loss']) & t['model_pct'].notna() & t['market %'].notna()]
    return pd.DataFrame({'game_date': t['game_date'], 'market': t['market'], 'side': t['side'], 'line': t['line'],
                         'odds': t['odds'], 'market %': t['market %'], 'model %': t['model_pct'],
                         'edge pp': t['edge_pp'], 'won': (t['result'] == 'win').astype(float)}).reset_index(drop=True)


def game_report(t: pd.DataFrame) -> str:
    """How the game model's chances did on settled main lines next to the margin-free price, and how its
    positive and +5 pp edges did as bets."""
    lines = ["## Game markets (not calibrated)", ""]
    if t.empty:
        return "\n".join(lines + ["No settled main-line game outcomes with the model's chance saved yet.", ""])
    nights = t['game_date'].nunique()
    lines += [f"{len(t)} settled main-line outcomes on {nights} nights ({_period(t)}); a calibration is fitted from "
              f"{GAME_CALIBRATION_MIN}+ outcomes on {GAME_CALIBRATION_NIGHTS}+ nights. Until then game outcomes get "
              f"no 🟢 / 🟡 and no stake: the model's edges are estimates for research.", "",
              "How well the chances predict the results (lower is better; both sides of each market count, so "
              "the rows aren't independent):", ""]
    candidates = {'Market (margin-free price)': t['market %'].values / 100, 'Game model': t['model %'].values / 100}
    lines += [markdown(pd.DataFrame([{'chances': n, **scores(t, p)} for n, p in candidates.items()]), '{:.4f}'), "",
              "Betting every outcome whose model edge reached the threshold (1 unit at the saved odds):", ""]
    rows = []
    for name, keep in (("edge > 0", t['edge pp'] > 0), ("edge ≥ +5 pp (the old 🟢)", t['edge pp'] >= 5)):
        part = t[keep]
        wins, n = int(part['won'].sum()), len(part)
        low, high = wilson_interval(wins, n)
        rows.append({'bets': name, 'n': n, 'nights': part['game_date'].nunique(),
                     'expected %': part['model %'].mean(), 'hit %': 100 * wins / n if n else np.nan,
                     'ci low %': 100 * low, 'ci high %': 100 * high,
                     'break-even %': (100 / part['odds']).mean() if n else np.nan,
                     'ROI %': 100 * (part['won'] * part['odds'] - 1).mean() if n else np.nan})
    lines += [markdown(pd.DataFrame(rows)), "", "By market:", ""]
    by = pd.DataFrame([{'market': market, 'outcomes': len(g),
                        'model log loss': scores(g, g['model %'].values / 100)['log loss'],
                        'market log loss': scores(g, g['market %'].values / 100)['log loss']}
                       for market, g in t.groupby('market')])
    return "\n".join(lines + [markdown(by, '{:.4f}'), ""])


def split(t: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """(fit part, held-out part) of one source's lines: 2022 at SPLIT, Superbet at its latest HOLD_OUT of nights."""
    if t.empty:
        return t, t
    if t['source'].iloc[0] == '2022':
        return t[t['game_date'] < SPLIT], t[t['game_date'] >= SPLIT]
    nights = sorted(t['game_date'].unique())
    held = set(nights[len(nights) - max(1, round(HOLD_OUT * len(nights))):]) if len(nights) > 1 else set()
    return t[~t['game_date'].isin(held)], t[t['game_date'].isin(held)]


def sides(t: pd.DataFrame) -> pd.DataFrame:
    """One row per line and side, decided lines only (pushes out): market, model (raw), over, won, odds."""
    rows = []
    for side, won in (('Over', t['actual'] > t['line']), ('Under', t['actual'] < t['line'])):
        market = t['market over %'] / 100 if side == 'Over' else 1 - t['market over %'] / 100
        rows.append(pd.DataFrame({'game_date': t['game_date'], 'line_id': t.index, 'side': side,
                                  'market': market, 'model': t[f'raw {side.lower()} %'] / 100,
                                  'over': side == 'Over', 'won': won.astype(float),
                                  'odds': t['over_odds'] if side == 'Over' else t['under_odds']}))
    s = pd.concat(rows, ignore_index=True)
    decided = t.index[t['actual'] != t['line']]
    return s[s['line_id'].isin(decided) & s['model'].notna() & s['odds'].notna()]


def fit_coefficients(s: pd.DataFrame, fitted=FITTED) -> Dict:
    """a, b, c, d of the calibration fitted on line sides s; coefficients not in `fitted` are 0."""
    keep = [COEFS.index(k) for k in fitted]
    beta = fit(features(s['market'].values, s['model'].values, s['over'].values)[:, keep], s['won'].values)
    return {k: float(beta[fitted.index(k)]) if k in fitted else 0.0 for k in COEFS}


def scores(s: pd.DataFrame, p: np.ndarray) -> Dict:
    """Log loss and Brier score of chances p for the rows of s (lower is better)."""
    y, p = s['won'].values, np.clip(p, 1e-4, 1 - 1e-4)
    return {'log loss': float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean()),
            'Brier': float(((p - y) ** 2).mean())}


def picks(t: pd.DataFrame, coef: Dict, green_edge: Optional[float] = None) -> pd.DataFrame:
    """Each line's pick under the calibration: the side with the bigger calibrated edge (pp), its chance (p),
    odds and signal (metrics.prop_signal with green_edge)."""
    out = {}
    for side in ('Over', 'Under'):
        market = t['market over %'] / 100 if side == 'Over' else 1 - t['market over %'] / 100
        odds = t['over_odds'] if side == 'Over' else t['under_odds']
        p = apply(coef, market.values, t[f'raw {side.lower()} %'].values / 100, np.full(len(t), side == 'Over'))
        out[side] = pd.DataFrame({'p': p, 'edge': 100 * (p - 1 / odds.values), 'odds': odds.values}, index=t.index)
    over_better = out['Over']['edge'] >= out['Under']['edge']
    best = out['Over'].where(over_better, out['Under'])
    return best.assign(side=np.where(over_better, 'Over', 'Under'), signal=prop_signal(best['edge'], green_edge))


def _scan_row(t: pd.DataFrame, chosen: pd.DataFrame, keep: pd.Series) -> Dict:
    row = rate_row(t, chosen['side'].where(keep), chosen['odds'])
    decided = keep & (t['actual'] != t['line'])
    return {'expected %': 100 * chosen.loc[keep, 'p'].mean() if keep.any() else np.nan, **row,
            'break-even %': 100 * (1 / chosen.loc[decided, 'odds']).mean() if decided.any() else np.nan,
            'nights': int(t.loc[keep, 'game_date'].nunique())}


def threshold_scan(t: pd.DataFrame, coef: Dict, thresholds=(0,) + GREEN_CANDIDATES) -> pd.DataFrame:
    """Betting every line whose calibrated edge is above each threshold: bets, expected % (the calibrated chance),
    hit %, its 95% range, ROI, the bets' average break-even % and the nights they're on. Cumulative: a line at +3 pp
    counts for 0, 1, 2 and 3."""
    chosen = picks(t, coef)
    rows = [{'edge ≥ pp': thr, **_scan_row(t, chosen, chosen['edge'] > thr if thr == 0 else chosen['edge'] >= thr)}
            for thr in thresholds]
    return pd.DataFrame(rows)


def choose_green_edge(t: pd.DataFrame, coef: Dict, candidates=GREEN_CANDIDATES, min_bets: int = MIN_GREEN_BETS,
                      min_nights: int = MIN_GREEN_NIGHTS) -> Optional[float]:
    """The smallest candidate edge whose picks on t (held-out lines) number at least min_bets over at least
    min_nights nights, paid (ROI > 0) and won clearly more often than their odds need (the low end of the hit
    rate's 95% range above the average break-even); None when none did. A lucky night or a thin sample can't pass."""
    if t.empty:
        return None
    scan = threshold_scan(t, coef, tuple(candidates))
    ok = scan[(scan['bets'] >= min_bets) & (scan['nights'] >= min_nights) & (scan['ROI %'] > 0)
              & (scan['ci low %'] > scan['break-even %'])]
    return float(ok['edge ≥ pp'].iloc[0]) if len(ok) else None


def strategy_rows(t: pd.DataFrame, coef: Dict) -> pd.DataFrame:
    calibrated = picks(t, coef)
    rows = {"Always Under": (pd.Series('Under', index=t.index), t['under_odds']),
            "Always Over": (pd.Series('Over', index=t.index), t['over_odds']),
            "Calibrated pick, every line": (calibrated['side'], calibrated['odds']),
            "Calibrated pick, edge > 0": (calibrated['side'].where(calibrated['edge'] > 0), calibrated['odds'])}
    return pd.DataFrame([{'strategy': name, **rate_row(t, side, odds)} for name, (side, odds) in rows.items()])


def calibration_table(s: pd.DataFrame, p: np.ndarray, width: float = 0.05) -> pd.DataFrame:
    """Rows grouped by predicted chance: how many, the average prediction, how often they won."""
    low = (np.floor(p / width) * width * 100).round().astype(int)
    d = s.assign(p=p, chance=[f"{x}–{x + round(100 * width)}%" for x in low], low=low)
    g = d.groupby(['low', 'chance'])
    return pd.DataFrame({'rows': g.size(), 'predicted %': 100 * g['p'].mean(),
                         'won %': 100 * g['won'].mean()}).reset_index().drop(columns='low')


def _period(t: pd.DataFrame) -> str:
    return f"{t['game_date'].min():%b %d %Y} – {t['game_date'].max():%b %d %Y}" if len(t) else "–"


SOURCE_NAMES = {'2022': "Unibet 2022/23", 'superbet': "Superbet 2026/27"}


def evaluate(sources: Dict[str, pd.DataFrame]) -> Tuple[Dict, Optional[float], str]:
    """Fit on the earlier part of every source, score each source's held-out part; the 🟢 threshold from the
    Superbet held-out lines. Returns (held-out metrics, green_edge_pp, report)."""
    parts = {name: split(t) for name, t in sources.items() if len(t)}
    train = pd.concat([sides(fit_part) for fit_part, _ in parts.values()], ignore_index=True)
    coef = fit_coefficients(train)
    report = ["## Held-out check", "",
              "Coefficients fitted on the earlier lines of every source: "
              + ", ".join(f"{k} = {v:.3f}" for k, v in coef.items()), ""]
    held_out = {'coefficients': coef, 'sources': {}}
    for name, (fit_part, test) in parts.items():
        label = SOURCE_NAMES[name]
        report += [f"### {label}: fitted on {_period(fit_part)} ({len(fit_part)} lines), "
                   f"scored on {_period(test)} ({len(test)} lines)", ""]
        if test.empty:
            report += ["Not enough nights to hold any out yet.", ""]
            continue
        s_test = sides(test)
        args = s_test['market'].values, s_test['model'].values, s_test['over'].values
        candidates = {'Market (margin-free price)': s_test['market'].values,
                      'Uncalibrated model': s_test['model'].values, 'Calibrated model': apply(coef, *args)}
        score_rows = pd.DataFrame([{'chances': n, **scores(s_test, p)} for n, p in candidates.items()])
        report += ["How well the chances predict the results (lower is better):", "", markdown(score_rows, '{:.4f}'),
                   "", "Betting the unseen lines (1 unit each, at the line's odds):", "",
                   markdown(strategy_rows(test, coef)), "",
                   "Signal efficiency: every line whose calibrated edge reaches the threshold (cumulative):", "",
                   markdown(threshold_scan(test, coef)), "",
                   "Calibration on the unseen lines (both sides of every line):", "",
                   markdown(calibration_table(s_test, candidates['Calibrated model'])), ""]
        held_out['sources'][name] = {'fit on': _period(fit_part), 'scored on': _period(test),
                                     'scores': score_rows.set_index('chances').to_dict('index')}
    superbet_test = parts.get('superbet', (pd.DataFrame(), pd.DataFrame()))[1]
    green = choose_green_edge(superbet_test, coef)
    report += ["### 🟢 threshold", "",
               (f"🟢 from an edge of +{green:g} pp: the smallest of {', '.join(f'+{c:g}' for c in GREEN_CANDIDATES)} "
                f"pp whose picks on the unseen Superbet lines numbered {MIN_GREEN_BETS}+ over {MIN_GREEN_NIGHTS}+ "
                f"nights, paid, and won more often than break-even even at the low end of the 95% range."
                if green is not None
                else f"No 🟢: none of the thresholds {', '.join(f'+{c:g}' for c in GREEN_CANDIDATES)} pp had "
                     f"{MIN_GREEN_BETS}+ picks over {MIN_GREEN_NIGHTS}+ unseen Superbet nights that won more often "
                     f"than break-even at the low end of the 95% range. Lines with a positive edge get 🟡 (an "
                     f"estimated edge, not a validated one)."),
               "", f"Selection policy: one bet per line (its last fetch before tip-off), the calibrated pick's side, "
                   f"1 unit at that fetch's odds. The threshold is chosen on the same held-out nights it's judged "
                   f"on, among {len(GREEN_CANDIDATES)} candidates, and re-chosen as nights settle: exploratory, "
                   f"not a proven betting advantage.", ""]
    return held_out, green, "\n".join(report)


def calibrate(sources: Dict[str, pd.DataFrame], out: str = CALIBRATION_FILE,
              game_outcomes: Optional[pd.DataFrame] = None) -> Dict:
    """evaluate, then refit on everything and write `out` (calibration.json) and the report next to it, with
    game_report(game_outcomes) at the end when given."""
    held_out, green, report = evaluate(sources)
    everything = pd.concat([sides(t) for t in sources.values() if len(t)], ignore_index=True)
    coef = fit_coefficients(everything)
    superbet = sources.get('superbet', pd.DataFrame())
    through = f"{superbet['game_date'].max():%Y-%m-%d}" if len(superbet) else None
    counts = {SOURCE_NAMES[n]: int(len(t)) for n, t in sources.items() if len(t)}
    result = {'coefficients': coef, 'green_edge_pp': green, 'superbet_through': through, 'model_version': MODEL_VERSION,
              'fitted_on': date.today().isoformat(),
              'source': "Unibet 2022/23 main lines (players with 5+ games, backtest variant 'none') and every "
                        "settled Superbet line (last fetch before tip-off)",
              'lines': counts, 'rows': int(len(everything)), 'held_out': held_out, 'identity': IDENTITY_CALIBRATION}
    atomic_write_text(out, json.dumps(result, indent=2))
    text = "\n".join(["# Calibration of the props model", "",
                      "The model's chance for a side is mapped to sigmoid(a·logit(market) + b·(logit(model) − "
                      "logit(market)) + c·[Over] + d): a = weight of the bookmaker's margin-free chance, b = weight "
                      "of the model's opinion beyond it, c = Over/Under bias, d = offset. Identity: a = b = 1, "
                      "c = d = 0. Lines: " + ", ".join(f"{k} {v}" for k, v in counts.items()) + ".", "",
                      "How to read b: it's how much of the model's disagreement with the price held up on past "
                      "lines (b = 0.1 keeps a tenth of it). It calibrates the model's point chance only; it says "
                      "nothing about whether the model's 95% range (edge low) is right, and a well-calibrated chance "
                      "close to the price is not a betting edge.", "", report,
                      "## Used by the dashboards (fitted on every line)", "",
                      ", ".join(f"{k} = {v:.3f}" for k, v in coef.items()) + f" ({len(everything)} line sides); "
                      + (f"🟢 from +{green:g} pp" if green is not None else "no 🟢")
                      + (f"; Superbet lines through {through}" if through else ""), ""]
                     + ([game_report(game_outcomes)] if game_outcomes is not None else []))
    atomic_write_text(os.path.join(os.path.dirname(out), os.path.basename(REPORT_FILE)), text)
    return {**result, 'report': text}


def _superbet_sources(logs: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    """superbet_lines of every saved line priced by the current model (nightly.priced_by)."""
    from espn_scraper import CURRENT_SEASON
    from espn_scraper.storage import snapshot_file
    from nightly import priced_by
    def read(name):
        path = snapshot_file(CURRENT_SEASON, name)
        return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()
    return superbet_lines(priced_by(read('superbet_props'), read('superbet_props_replay')), logs, games)


def _game_sources(games: pd.DataFrame) -> Optional[pd.DataFrame]:
    """game_lines of the saved Superbet game odds; None when they can't be read or settled (the props calibration
    goes on without the game report)."""
    from espn_scraper import CURRENT_SEASON
    from espn_scraper.storage import read_snapshot, snapshot_file
    path = snapshot_file(CURRENT_SEASON, 'superbet_game_odds')
    try:
        return game_lines(read_snapshot(path), games) if os.path.exists(path) else pd.DataFrame()
    except Exception as e:
        log.warning("Game markets left out of the report: %s", e)
        return None


def refresh(logs: pd.DataFrame, games: pd.DataFrame, out: str = CALIBRATION_FILE,
            lines_file: str = LINES_FILE) -> bool:
    """Refit (calibrate) when a Superbet night newer than the file's superbet_through has settled, or the file was
    fitted for another model version. logs: prepare_logs output; games: games.csv rows (date parsed). True when
    refitted; errors are logged, not raised (the old file stays). Without Superbet lines of the current model
    (after a version change, before --reprice) nothing is refitted and the reason is logged."""
    try:
        with locked(out):           # two processes refreshing at once: the second finds the first's refit
            return _refresh(logs, games, out, lines_file)
    except Exception as e:
        log.error("Calibration refresh failed, keeping the old one: %s", e)
        return False


def _refresh(logs: pd.DataFrame, games: pd.DataFrame, out: str, lines_file: str) -> bool:
    saved = {}
    if os.path.exists(out):
        with open(out, encoding='utf-8') as f:
            saved = json.load(f)
    superbet = _superbet_sources(logs, games)
    if superbet.empty:
        log.warning("No settled Superbet lines priced by model %s: run daily_snapshot.py --reprice; "
                    "calibration not refitted", MODEL_VERSION)
        return False
    newest = f"{superbet['game_date'].max():%Y-%m-%d}"
    same_model = saved.get('model_version') == MODEL_VERSION
    if same_model and saved.get('superbet_through') and newest <= saved['superbet_through']:
        return False
    sources = {'2022': lines_2022(lines_file) if os.path.exists(lines_file) else pd.DataFrame(),
               'superbet': superbet}
    result = calibrate(sources, out, _game_sources(games))
    log.info("Calibration refitted through %s: %s, 🟢 from %s", newest, result['coefficients'],
             result['green_edge_pp'])
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--lines', default=LINES_FILE)
    parser.add_argument('--out', default=CALIBRATION_FILE)
    parser.add_argument('--no-superbet', action='store_true', help="fit on the 2022/23 lines only")
    args = parser.parse_args()

    sources, game_outcomes = {'2022': lines_2022(args.lines)}, None
    if not args.no_superbet:
        from espn_scraper import SEASONS
        from espn_scraper.storage import load_games, load_player_gamelogs
        from models import prepare_logs
        games = load_games(sorted(SEASONS))
        sources['superbet'] = _superbet_sources(prepare_logs(load_player_gamelogs(sorted(SEASONS))), games)
        game_outcomes = _game_sources(games)
    report = calibrate(sources, args.out, game_outcomes)['report']
    sys.stdout.reconfigure(errors='replace')   # a Windows console's code page lacks − and 🟢
    print(report)


if __name__ == '__main__':
    main()
