"""Which parts of the props model carry information beyond the price: a ladder of models scored on the same lines.

    python -m backtest.ablation              # after python -m backtest.run --out data/backtest/2022_lines_components.csv
    python -m backtest.ablation --refresh    # price the Superbet lines again (else the saved components are reused)

Each rung adds one piece to the one before, and every rung is fitted and scored the same way, on the same lines:
the calibration form of metrics.calibrate (a, b, c, d) is fitted on the earlier part of each source and scored on
the later part, which nothing was chosen on (2022/23: Nov–Jan / Feb–May; Superbet: all but the latest 30% of nights
/ those nights, as backtest/calibrate.py splits them).

    1. Market (margin-free price)            the bookmaker's chance, nothing fitted
    2. + Over/Under bias                      a, c, d fitted on the market alone
    3. Hit rate                               the player's hit rate, pulled toward the market (10 games' worth)
    4. Distribution around the average        a normal around the season average with the player's spread
    5. Hit rate + distribution                3 and 4 averaged: the model without tonight's adjustments
    6. + absences                             the distribution around adj avg (RotoWire's out teammates)
    7. + implied team total                   × the game's pace factor (Superbet only: no 2022 game odds)
    8. + matchup = the full model             × the matchup factor: proj avg, what the dashboards price

The 2022/23 oracle (every absent rotation player known, backtest variant 'absences') is an upper bound for rung 6,
reported apart from the realistic ladder.

The score is the log loss on both sides of every decided line (pushes out) and its difference from the market's,
with a 95% range from resampling whole nights (lines of one night share games, players and news, so they aren't
independent evidence). Betting is reported apart: each rung's picks with a positive calibrated edge, 1 unit at the
line's odds. Writes data/backtest/ablation.md.
"""
import argparse
import logging
import math
import os
import sys
from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd

import backtest  # noqa: F401  (puts dashboard/ on the path)
from backtest.calibrate import _logit, _sigmoid, fit, scores, split
from backtest.run import MIN_GAMES, OUT_DIR, markdown, rate_row

log = logging.getLogger(__name__)

COMPONENTS_2022 = os.path.join(OUT_DIR, '2022_lines_components.csv')
REPORT = os.path.join(OUT_DIR, 'ablation.md')
PRIOR_GAMES = 10          # metrics.prop_probability's market prior
BOOTSTRAP = 1000
# what a line needs for every rung: the player's numbers, both odds and the settled result
COLUMNS = ['game_date', 'bet_type', 'line', 'actual', 'over_odds', 'under_odds', 'market over %', 'raw over %',
           'games', 'over %', 'under %', 'sd', 'avg', 'adj avg', 'pace factor', 'matchup factor', 'proj avg']


# --- the rungs: a side's chance from the line's components, as metrics.prop_probability computes it ---

def _normal_cdf(x):
    return 0.5 * (1 + np.vectorize(math.erf)(np.asarray(x, dtype=float) / math.sqrt(2)))


def chance(t: pd.DataFrame, side: str, mean: Optional[pd.Series] = None, hit: bool = True) -> np.ndarray:
    """The model's chance that `side` wins: the hit rate pulled toward the market (hit), the normal distribution
    around `mean` pulled the same way (mean given), or their average (both). The distribution needs 3+ games;
    with fewer, the hit rate stands in, as in metrics.prop_probability."""
    market = t['market over %'] / 100 if side == 'Over' else 1 - t['market over %'] / 100
    n = t['games'].astype(float)
    hits = (t['over %' if side == 'Over' else 'under %'] * n / 100).round()
    shrunk = (hits + PRIOR_GAMES * market) / (n + PRIOR_GAMES)
    if mean is None:
        return shrunk.values
    whole = (t['line'] % 1 == 0)
    cut = t['line'] + np.where(whole, 0.5 if side == 'Over' else -0.5, 0.0)
    over = 1 - _normal_cdf((cut - mean) / t['sd'].clip(lower=0.5))
    weight = n / (n + PRIOR_GAMES)
    dist = (weight * (over if side == 'Over' else 1 - over) + (1 - weight) * market).where(n >= 3)
    if not hit:
        return dist.fillna(shrunk).values
    return ((shrunk + dist) / 2).fillna(shrunk).values


def _rungs() -> List[Dict]:
    """name, the side's chance (None = the market), whether the model's opinion is fitted (b), sources it applies to."""
    pace = lambda t: t['adj avg'] * t['pace factor'].fillna(1.0)
    return [
        {'name': "1. Market (margin-free price)", 'chance': None, 'fit': False},
        {'name': "2. + Over/Under bias", 'chance': None, 'fit': True},
        {'name': "3. Hit rate", 'chance': lambda t, s: chance(t, s)},
        {'name': "4. Distribution around the average", 'chance': lambda t, s: chance(t, s, t['avg'], hit=False)},
        {'name': "5. Hit rate + distribution", 'chance': lambda t, s: chance(t, s, t['avg'])},
        {'name': "6. + absences", 'chance': lambda t, s: chance(t, s, t['adj avg'])},
        {'name': "7. + implied team total", 'chance': lambda t, s: chance(t, s, pace(t))},
        {'name': "8. + matchup = the full model", 'chance': lambda t, s: chance(t, s, t['proj avg'])},
    ]


def sides(t: pd.DataFrame, side_chance: Optional[Callable]) -> pd.DataFrame:
    """Both sides of every decided line: game_date, line_id, side, market, model (the rung's chance; the market's
    for rungs 1–2), over, won, odds."""
    rows = []
    for side, won in (('Over', t['actual'] > t['line']), ('Under', t['actual'] < t['line'])):
        market = t['market over %'] / 100 if side == 'Over' else 1 - t['market over %'] / 100
        model = market.values if side_chance is None else side_chance(t, side)
        rows.append(pd.DataFrame({'game_date': t['game_date'].values, 'line_id': t.index, 'side': side,
                                  'market': market.values, 'model': model, 'over': side == 'Over',
                                  'won': won.astype(float).values,
                                  'odds': (t['over_odds'] if side == 'Over' else t['under_odds']).values}))
    s = pd.concat(rows, ignore_index=True)
    return s[s['line_id'].isin(t.index[t['actual'] != t['line']])].reset_index(drop=True)


def _features(s: pd.DataFrame, with_model: bool) -> np.ndarray:
    m = _logit(s['market'].values)
    cols = [m, _logit(s['model'].values) - m] if with_model else [m]
    return np.column_stack(cols + [s['over'].values.astype(float), np.ones(len(s))])


def fit_and_predict(train: pd.DataFrame, test: pd.DataFrame, rung: Dict) -> np.ndarray:
    """The rung's calibrated chance for test's rows, fitted on train's (rung 1: the market itself)."""
    if rung['chance'] is None and not rung.get('fit'):
        return test['market'].values
    with_model = rung['chance'] is not None
    beta = fit(_features(train, with_model), train['won'].values)
    return _sigmoid(_features(test, with_model) @ beta)


def _loss(won: np.ndarray, p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return -(won * np.log(p) + (1 - won) * np.log(1 - p))


def night_bootstrap(nights: np.ndarray, diff: np.ndarray, reps: int = BOOTSTRAP, seed: int = 0):
    """95% range of the mean of diff when whole nights are resampled (with replacement)."""
    frame = pd.DataFrame({'night': nights, 'diff': diff}).groupby('night')['diff'].agg(['sum', 'size'])
    if len(frame) < 2:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    picks = rng.integers(0, len(frame), size=(reps, len(frame)))
    means = frame['sum'].values[picks].sum(axis=1) / frame['size'].values[picks].sum(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def picks(test_lines: pd.DataFrame, test_sides: pd.DataFrame, p: np.ndarray) -> pd.DataFrame:
    """Each test line's side with the bigger calibrated edge and its odds; side NaN where neither edge is positive."""
    s = test_sides.assign(p=p, edge=p - 1 / test_sides['odds'])
    best = s.sort_values('edge', ascending=False).drop_duplicates('line_id').set_index('line_id')
    best = best.reindex(test_lines.index)
    return pd.DataFrame({'side': best['side'].where(best['edge'] > 0), 'odds': best['odds']}, index=test_lines.index)


def ladder(lines: pd.DataFrame, rungs: List[Dict]) -> Dict[str, pd.DataFrame]:
    """Every rung fitted on the earlier lines and scored on the later ones: 'scores' (log loss, Brier, difference
    from the market with its night-bootstrap range) and 'betting' (positive-edge picks)."""
    fit_part, test_part = split(lines)
    score_rows, bet_rows = [], []
    market_loss = None
    for rung in rungs:
        train, test = sides(fit_part, rung['chance']), sides(test_part, rung['chance'])
        keep_train, keep_test = train['model'].notna(), test['model'].notna()
        train, test = train[keep_train], test[keep_test]
        p = fit_and_predict(train, test, rung)
        loss = _loss(test['won'].values, p)
        if market_loss is None:
            market_loss = pd.Series(loss, index=test.index)
        diff = loss - market_loss.reindex(test.index).values
        low, high = night_bootstrap(test['game_date'].values, diff)
        score_rows.append({'model': rung['name'], **scores(test, p), 'vs market': float(np.mean(diff)),
                           'range low': low, 'range high': high})
        chosen = picks(test_part, test, p)
        bet = rate_row(test_part, chosen['side'], chosen['odds'])
        decided = chosen['side'].notna() & (test_part['actual'] != test_part['line'])
        bet_rows.append({'model': rung['name'], **bet,
                         'break-even %': 100 * (1 / chosen.loc[decided, 'odds']).mean() if decided.any() else np.nan})
    return {'scores': pd.DataFrame(score_rows), 'betting': pd.DataFrame(bet_rows),
            'fit': fit_part, 'test': test_part}


# --- the lines ---

def eligible(t: pd.DataFrame) -> pd.DataFrame:
    """Lines every rung can price: MIN_GAMES+ games, both odds, the market's chance, a result."""
    t = t.dropna(subset=['actual', 'over_odds', 'under_odds', 'market over %', 'avg', 'proj avg'])
    return t[t['games'] >= MIN_GAMES].reset_index(drop=True)


def lines_2022(path: str = COMPONENTS_2022) -> Dict[str, pd.DataFrame]:
    """The 2022/23 backtest's main lines: 'none' (no lineup knowledge) and 'absences' (the oracle)."""
    t = pd.read_csv(path, parse_dates=['game_date'])
    t = t[t['main']]
    return {variant: eligible(part).assign(source='2022') for variant, part in t.groupby('variant')}


def superbet_components(refresh: bool = False) -> pd.DataFrame:
    """Every saved Superbet line judged by its last fetch before tip-off, priced again with the current model as of
    that fetch (nightly.recompute_props, full table) and settled. Saved as superbet_props_components.csv (with
    model_version) and reused while the model version and the lines are the same."""
    from espn_scraper import CURRENT_SEASON, SEASONS
    from espn_scraper.storage import load_games, load_player_gamelogs, snapshot_file
    from models import MODEL_VERSION, prepare_logs
    from name_resolver import NameResolver
    from nightly import et_night, lineups_before_tip, recompute_props
    from tracking import PROP_KEY, settle_props

    cache = snapshot_file(CURRENT_SEASON, 'superbet_props_components')
    snaps = pd.read_csv(snapshot_file(CURRENT_SEASON, 'superbet_props'))
    fetched = pd.to_datetime(snaps['fetched_at'], utc=True)
    last = snaps[fetched < pd.to_datetime(snaps['start_time'], utc=True)].sort_values('fetched_at', kind='stable') \
        .drop_duplicates(PROP_KEY, keep='last').reset_index(drop=True)
    if not refresh and os.path.exists(cache):
        saved = pd.read_csv(cache, parse_dates=['game_date'])
        if len(saved) and (saved['model_version'] == MODEL_VERSION).all() and len(saved) == len(last):
            return saved
    logs = prepare_logs(load_player_gamelogs(sorted(SEASONS)))
    games = load_games(sorted(SEASONS))
    resolver = NameResolver(logs)
    lines = resolver.add_ids(last.drop(columns=['player_id_ESPN'], errors='ignore'), team_cols=('home', 'away'))
    rotowire = resolver.add_ids(pd.read_csv(snapshot_file(CURRENT_SEASON, 'rotowire_lineups')))
    odds = pd.read_csv(snapshot_file(CURRENT_SEASON, 'superbet_game_odds'))
    priced = []
    for (fetched_at, night), rows in lines.groupby(['fetched_at', et_night(lines['start_time'])]):
        lineups = lineups_before_tip(rotowire, night, pd.Timestamp(fetched_at) + pd.Timedelta(seconds=1))
        priced.append(recompute_props(rows, logs, games, lineups, odds[odds['fetched_at'] == fetched_at],
                                      et_night(pd.Series([fetched_at])).iloc[0], full=True))
    table = pd.concat(priced).sort_index()
    settled = settle_props(snaps, logs, games, bets=last)
    out = table.assign(game_date=et_night(last['start_time']), actual=settled['actual'].values,
                       status=settled['status'].values, model_version=MODEL_VERSION)
    out = out[[c for c in COLUMNS + ['status', 'model_version'] if c in out]]
    out.to_csv(cache, index=False)
    return pd.read_csv(cache, parse_dates=['game_date'])


# --- the report ---

def section(title: str, lines: pd.DataFrame, rungs: List[Dict], note: str = '') -> List[str]:
    result = ladder(lines, rungs)
    fit_part, test_part = result['fit'], result['test']
    head = [f"## {title}", "",
            f"Fitted on {fit_part['game_date'].min():%b %d %Y} – {fit_part['game_date'].max():%b %d %Y} "
            f"({len(fit_part)} lines, {fit_part['game_date'].nunique()} nights), scored on "
            f"{test_part['game_date'].min():%b %d %Y} – {test_part['game_date'].max():%b %d %Y} "
            f"({len(test_part)} lines, {test_part['game_date'].nunique()} nights)." + (f" {note}" if note else ""), ""]
    if test_part['game_date'].nunique() < 10:
        head += [f"Only {test_part['game_date'].nunique()} scored nights: the ranges are wide and the ranking can "
                 f"change as nights settle.", ""]
    return head + ["How well each model predicts the unseen lines (lower is better; *vs market* = its log loss minus "
                   "the market's per line side, with the 95% range from resampling whole nights; a range below 0 "
                   "means it beat the price):", "", markdown(result['scores'], '{:.4f}'), "",
                   "Betting its positive-edge picks on those lines (1 unit each at the line's odds; a separate "
                   "question from the predictions above):", "", markdown(result['betting']), ""]


def report(sources: Dict[str, pd.DataFrame]) -> str:
    rungs = _rungs()
    no_game_odds = [r for r in rungs if not r['name'].startswith("7.")]
    parts = ["# What each part of the props model adds", "",
             "Every model below is fitted (metrics.calibrate's form) on the earlier lines of a source and scored on "
             "its later lines; all of them on exactly the same lines. See backtest/ablation.py for the rungs.", ""]
    if '2022' in sources:
        parts += section("Unibet 2022/23", sources['2022'], no_game_odds,
                         "No lineup knowledge, so rung 6 equals rung 5; no game odds, so there's no rung 7.")
    if '2022 oracle' in sources:
        oracle = [r for r in rungs if r['name'][0] in '156' or r['name'].startswith("8.")]
        parts += section("Unibet 2022/23 with every absence known (oracle, an upper bound)", sources['2022 oracle'],
                         oracle, "Absences come from who actually didn't play: not available before a game.")
    if 'superbet' in sources and len(sources['superbet']):
        parts += section("Superbet 2026/27", sources['superbet'], rungs,
                         "Each line at its last fetch before tip-off, priced again with the current model.")
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--lines', default=COMPONENTS_2022)
    parser.add_argument('--refresh', action='store_true', help="price the Superbet lines again")
    parser.add_argument('--out', default=REPORT)
    args = parser.parse_args()
    sources = {}
    if os.path.exists(args.lines):
        variants = lines_2022(args.lines)
        sources['2022'] = variants['none']
        if 'absences' in variants:
            sources['2022 oracle'] = variants['absences']
    else:
        log.warning("%s not found: run python -m backtest.run --out %s first", args.lines, args.lines)
    superbet = superbet_components(args.refresh)
    sources['superbet'] = eligible(superbet[superbet['status'] == 'settled']).assign(source='superbet')
    text = report(sources)
    with open(args.out, 'w', encoding='utf-8') as f:
        f.write(text)
    sys.stdout.reconfigure(errors='replace')
    print(text)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    main()
