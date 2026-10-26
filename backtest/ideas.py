"""Candidate changes to the props model, scored against the current one on the 2022/23 lines (exploratory).

    python -m backtest.ideas      # after python -m backtest.run --out data/backtest/2022_lines_components.csv

Every candidate changes how the model turns the player's games into a chance; everything else stays as in
metrics.prop_probability (the market prior worth 10 games, the projection's adjustments, the average of the hit
rate and the distribution). Each is calibrated the way the dashboards are (backtest/calibrate.py's FITTED: a and b)
on Nov–Jan and scored on Feb–May, on exactly the lines the current model is scored on. The score is the log loss
difference from the current model per line side, with a 95% range from resampling whole nights.

Candidates:
- count distribution: a negative binomial (Poisson when the player's results vary less than their average) with the
  player's own spread, for low-count stats (3PM), for every count stat but PTS (3PM, AST, REB), or for all stats;
- recency: the average, spread and hit rate weighted toward recent games (half-life 5, 10 or 20 games), the
  projection's adjustments applied to the weighted average;
- distribution only: the hit-rate half dropped (the ablation found it adds nothing).

Several candidates are tried on the same nights, so the best of them looks better than it is: a candidate is worth
taking to Superbet only if its range is clearly below 0, and kept only if it holds there too. Writes
data/backtest/ideas_2022.md.
"""
import argparse
import logging
import math
import os
import sys
from typing import Callable, Dict, List

import numpy as np
import pandas as pd

import backtest  # noqa: F401  (puts dashboard/ on the path)
from backtest.ablation import COMPONENTS_2022, PRIOR_GAMES, _loss, chance, eligible, night_bootstrap
from backtest.calibrate import FITTED, _logit, _sigmoid, fit, scores, split
from backtest.run import OUT_DIR, markdown, rate_row
from safe_io import atomic_write_text

log = logging.getLogger(__name__)

REPORT = os.path.join(OUT_DIR, 'ideas_2022.md')
HALF_LIVES = (5, 10, 20)
LOW_COUNT = {'3PM'}
COUNT_STATS = {'3PM', 'AST', 'REB'}


# --- the candidates' distributions ---

def count_over(mean: np.ndarray, var: np.ndarray, line: np.ndarray) -> np.ndarray:
    """P(X > line) for a count with this mean and variance: negative binomial when var > mean, else Poisson
    (lines are half points, so X > line means X ≥ floor(line) + 1)."""
    mean = np.clip(np.asarray(mean, dtype=float), 1e-6, None)
    var = np.asarray(var, dtype=float)
    k_max = np.floor(np.asarray(line, dtype=float)).astype(int)
    nb = var > mean * 1.0001
    r = np.where(nb, mean ** 2 / np.where(nb, var - mean, 1.0), np.inf)
    q = np.where(nb, 1 - mean / np.where(nb, var, 1.0), 0.0)      # NB: pmf(k+1) / pmf(k) = (k + r) / (k + 1) · q
    # pmf(0) and the step pmf(k+1)/pmf(k) for both families
    log_p0 = np.where(nb, np.where(nb, r, 1.0) * np.log(np.clip(1 - q, 1e-12, None)), -mean)
    pmf = np.exp(log_p0)
    cdf = pmf.copy()
    for k in range(int(k_max.max()) if len(k_max) else 0):
        step = np.where(nb, (k + np.where(nb, r, 0.0)) / (k + 1) * q, mean / (k + 1))
        pmf = pmf * step
        cdf = cdf + np.where(k + 1 <= k_max, pmf, 0.0)
    return np.clip(1 - cdf, 0.0, 1.0)


def _combine(t: pd.DataFrame, side: str, over: np.ndarray, hit: bool, n=None, hits=None) -> np.ndarray:
    """The side's chance from P(over) like metrics.prop_probability: the distribution pulled toward the market as if
    it were worth PRIOR_GAMES games, averaged with the pulled hit rate (hit=True). n / hits: the (effective) games
    and the side's hits, default the season's."""
    market = (t['market over %'] / 100 if side == 'Over' else 1 - t['market over %'] / 100).values
    n = t['games'].values.astype(float) if n is None else np.asarray(n, dtype=float)
    if hits is None:
        hits = (t['over %' if side == 'Over' else 'under %'] * t['games'] / 100).round().values
    shrunk = (hits + PRIOR_GAMES * market) / (n + PRIOR_GAMES)
    weight = n / (n + PRIOR_GAMES)
    side_p = over if side == 'Over' else 1 - over
    dist = np.where(t['games'].values >= 3, weight * side_p + (1 - weight) * market, np.nan)
    if not hit:
        return np.where(np.isnan(dist), shrunk, dist)
    return np.where(np.isnan(dist), shrunk, (shrunk + dist) / 2)


def count_candidate(stats: set) -> Callable:
    """The current model with a count distribution for the lines of `stats` (normal for the rest)."""
    def side_chance(t: pd.DataFrame, side: str) -> np.ndarray:
        base = chance(t, side, t['proj avg'])
        use = t['bet_type'].isin(stats).values
        if not use.any():
            return base
        # the player's variance, scaled with the projection (a count's spread grows with its mean)
        ratio = (t['proj avg'] / t['avg'].where(t['avg'] > 0)).fillna(1.0)
        var = t['sd'].fillna(0).values ** 2 * ratio.values
        over = count_over(t['proj avg'].values, var, t['line'].values)
        return np.where(use, _combine(t, side, over, hit=True), base)
    return side_chance


def distribution_only(t: pd.DataFrame, side: str) -> np.ndarray:
    return chance(t, side, t['proj avg'], hit=False)


def _normal_over(mean, sd, line):
    z = (np.asarray(line, dtype=float) - np.asarray(mean, dtype=float)) / np.clip(np.asarray(sd, dtype=float), 0.5, None)
    return 1 - 0.5 * (1 + np.vectorize(math.erf)(z / math.sqrt(2)))


def recency_candidate(half_life: int) -> Callable:
    """The current model with the average, spread and hit rate weighted toward recent games (columns from
    recency_features); the projection's adjustments (proj avg / avg) are applied to the weighted average."""
    def side_chance(t: pd.DataFrame, side: str) -> np.ndarray:
        h = f'h{half_life}'
        ratio = (t['proj avg'] / t['avg'].where(t['avg'] > 0)).fillna(1.0)
        over = _normal_over(t[f'ew mean {h}'] * ratio, t[f'ew sd {h}'], t['line'])
        hits = t[f'ew over {h}'] if side == 'Over' else t[f'ew n {h}'] - t[f'ew over {h}']
        return _combine(t, side, over, hit=True, n=t[f'ew n {h}'].values, hits=hits.values)
    return side_chance


# --- recency features from the games before each line ---

def recency_features(lines: pd.DataFrame, logs: pd.DataFrame, half_lives=HALF_LIVES) -> pd.DataFrame:
    """Per line, from the player's games of that stat before its date (what backtest.run priced it from): the
    weighted mean, sd, effective games and weighted Over hits for each half-life (weight 0.5 ** (games ago / h))."""
    cols = {f'{k} h{h}': np.full(len(lines), np.nan) for h in half_lives for k in ('ew mean', 'ew sd', 'ew n', 'ew over')}
    cols['check games'] = np.zeros(len(lines))
    by_player = {pid: g.sort_values(['Date', 'game_id']) for pid, g in logs.groupby('player_id_ESPN')}
    for i, row in enumerate(lines.itertuples(index=False)):
        games = by_player.get(row.player_id_ESPN)
        if games is None:
            continue
        values = games.loc[games['Date'] < row.game_date, row.bet_type].dropna().values.astype(float)
        cols['check games'][i] = len(values)
        if not len(values):
            continue
        age = np.arange(len(values))[::-1]
        for h in half_lives:
            w = 0.5 ** (age / h)
            mean = np.sum(w * values) / w.sum()
            cols[f'ew mean h{h}'][i] = mean
            cols[f'ew sd h{h}'][i] = math.sqrt(np.sum(w * (values - mean) ** 2) / w.sum()) * \
                math.sqrt(len(values) / max(len(values) - 1, 1))
            n_eff = w.sum() ** 2 / np.sum(w ** 2)
            cols[f'ew n h{h}'][i] = n_eff
            cols[f'ew over h{h}'][i] = n_eff * np.sum(w * (values > row.line)) / w.sum()
    return lines.assign(**cols)


# --- scoring ---

def _sides(t: pd.DataFrame, side_chance: Callable) -> pd.DataFrame:
    rows = []
    for side, won in (('Over', t['actual'] > t['line']), ('Under', t['actual'] < t['line'])):
        market = t['market over %'] / 100 if side == 'Over' else 1 - t['market over %'] / 100
        rows.append(pd.DataFrame({'game_date': t['game_date'].values, 'line_id': t.index, 'side': side,
                                  'bet_type': t['bet_type'].values, 'market': market.values,
                                  'model': side_chance(t, side), 'won': won.astype(float).values,
                                  'odds': (t['over_odds'] if side == 'Over' else t['under_odds']).values}))
    s = pd.concat(rows, ignore_index=True)
    return s[s['line_id'].isin(t.index[t['actual'] != t['line']])].reset_index(drop=True)


def _calibrated(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    """Fitted in the dashboards' form (FITTED: a·logit(market) + b·(logit(model) − logit(market)))."""
    assert FITTED == ['a', 'b'], "scored in the form the dashboards use"
    design = lambda s: np.column_stack([_logit(s['market'].values),
                                        _logit(s['model'].values) - _logit(s['market'].values)])
    return _sigmoid(design(test) @ fit(design(train), train['won'].values))


def compare(lines: pd.DataFrame, candidates: Dict[str, Callable]) -> Dict[str, pd.DataFrame]:
    """Each candidate fitted on the earlier lines, scored on the later ones against the current model (the first
    candidate): log loss, difference per line side with its night range, the same on 3PM lines only, and betting."""
    fit_part, test_part = split(lines)
    results, bets = [], []
    base_loss = None
    for name, side_chance in candidates.items():
        train, test = _sides(fit_part, side_chance), _sides(test_part, side_chance)
        p = _calibrated(train, test)
        loss = _loss(test['won'].values, p)
        if base_loss is None:
            base_loss = loss
        diff = loss - base_loss
        low, high = night_bootstrap(test['game_date'].values, diff)
        low_count = test['bet_type'].isin(LOW_COUNT).values
        lc_low, lc_high = night_bootstrap(test['game_date'].values[low_count], diff[low_count])
        market_loss = _loss(test['won'].values, test['market'].values)
        results.append({'candidate': name, 'log loss': loss.mean(), 'vs market': (loss - market_loss).mean(),
                        'vs current': diff.mean(), 'range low': low, 'range high': high,
                        'vs current, 3PM': diff[low_count].mean(), '3PM low': lc_low, '3PM high': lc_high})
        s = test.assign(p=p, edge=p - 1 / test['odds'])
        best = s.sort_values('edge', ascending=False).drop_duplicates('line_id').set_index('line_id') \
            .reindex(test_part.index)
        side = best['side'].where(best['edge'] > 0)
        bets.append({'candidate': name, **rate_row(test_part, side, best['odds'])})
    return {'scores': pd.DataFrame(results), 'betting': pd.DataFrame(bets), 'fit': fit_part, 'test': test_part}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--lines', default=COMPONENTS_2022)
    parser.add_argument('--out', default=REPORT)
    args = parser.parse_args()
    from backtest.data_2022 import load_logs_2022
    from models import prepare_logs

    t = pd.read_csv(args.lines, parse_dates=['game_date'])
    lines = eligible(t[(t['variant'] == 'none') & t['main']]).assign(source='2022')
    logs, _ = load_logs_2022()
    lines = recency_features(lines, prepare_logs(logs))
    mismatch = int((lines['check games'] != lines['games']).sum())
    log.info("recency features: %d of %d lines rebuilt with a different game count", mismatch, len(lines))

    candidates = {"Current model": lambda t_, side: chance(t_, side, t_['proj avg']),
                  "Distribution only (no hit rate)": distribution_only,
                  "Count distribution: 3PM": count_candidate(LOW_COUNT),
                  "Count distribution: 3PM, AST, REB": count_candidate(COUNT_STATS),
                  "Count distribution: every stat": count_candidate({'PTS', 'REB', 'AST', '3PM', 'ARP'})}
    candidates |= {f"Recency, half-life {h} games": recency_candidate(h) for h in HALF_LIVES}
    result = compare(lines, candidates)
    fit_part, test_part = result['fit'], result['test']
    text = "\n".join([
        "# Candidate changes to the props model, on Unibet 2022/23 (exploratory)", "",
        f"Calibrated (a, b) on {fit_part['game_date'].min():%b %d} – {fit_part['game_date'].max():%b %d %Y} "
        f"({len(fit_part)} lines), scored on {test_part['game_date'].min():%b %d} – "
        f"{test_part['game_date'].max():%b %d %Y} ({len(test_part)} lines, {test_part['game_date'].nunique()} "
        f"nights), every candidate on the same lines. Recency features rebuilt from the 2022/23 logs: "
        f"{mismatch} of {len(lines)} lines with a game count different from the backtest's.", "",
        "*vs current* = the candidate's log loss minus the current model's, per line side (below 0 = better), with "
        "the 95% range from resampling whole nights; *3PM* the same on 3PM lines only. Several candidates are "
        "tried on the same nights, so treat a small gain as noise.", "",
        markdown(result['scores'], '{:.4f}'), "",
        "Betting each candidate's positive-edge picks on those lines (1 unit at the line's odds):", "",
        markdown(result['betting']), ""])
    atomic_write_text(args.out, text)
    sys.stdout.reconfigure(errors='replace')
    print(text)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    main()
