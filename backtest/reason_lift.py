"""Do the context reasons know anything the props model doesn't? A fixed list, tested on unseen lines.

    python -m backtest.reason_lift                 # after python -m backtest.run
    python -m backtest.reason_lift --no-superbet   # the 2022/23 lines only

The panel's context reasons (reasons.prop_reasons) describe the player's games without being part of the model, so
they're shown without a direction. This tests whether each would have helped: for every line side,

    logit(p1) = logit(p0) + β·f

where p0 is the current model's chance calibrated the way the dashboards are (a, b fitted on the earlier lines),
f the feature as reasons.feature_* computes it from the player's games before the line (signed for Over, so −f for
Under), and β fitted on the earlier lines too. The score is p1's log loss minus p0's on the later lines, per line
side, with a 95% range from resampling whole nights; lines where the feature can't be computed are left out of
both. The split is backtest/calibrate.py's (2022/23: Nov–Jan / Feb–May; Superbet: all but the latest 30% of
nights).

The list is fixed before looking (no search for a feature that works): the last-10 hit rate, the minutes trend
in the current team stint, the home/away split, the rest difference, the history against the opponent, and the
change in shot attempts (PTS, its combos and 3PM). Not testable yet, so 'untested': tonight's role against the
player's recent starts (needs RotoWire's role as of each line) and the blowout minutes (needs the spread as of
each line; 2022/23 has no game odds).

A feature gets 'lift' only when its range is below 0 on the 2022/23 lines and the Superbet range doesn't lie
above 0; otherwise 'no_lift'. Only then does the panel give it a direction (β's sign: over_sign). Writes
data/backtest/reason_lift.json (read by reasons.lift_status) and data/backtest/reason_lift.md.
"""
import argparse
import bisect
import json
import logging
import os
import sys
from typing import Callable, Dict

import numpy as np
import pandas as pd

import backtest  # noqa: F401  (puts dashboard/ on the path)
from backtest.ablation import _loss, night_bootstrap
from backtest.calibrate import _logit, _sigmoid, fit, fit_coefficients, lines_2022, sides, split, features
from backtest.run import MIN_GAMES, OUT_DIR, markdown
from reasons import (LIFT, LIFT_FILE, NO_LIFT, UNTESTED, current_stint, feature_hits, feature_minutes, feature_rest,
                     feature_venue, feature_volume, feature_vs_opp)
from safe_io import atomic_write_text

log = logging.getLogger(__name__)

REPORT = os.path.join(OUT_DIR, 'reason_lift.md')
FEATURES = ['hits_l10', 'minutes', 'venue', 'rest', 'vs_opp', 'volume']
NOT_TESTABLE = {'role': "needs RotoWire's role as of each line",
                'blowout': "needs the spread as of each line (2022/23 has no game odds)"}


def _rest(dates_by_team: Dict[str, list], team: str, day: pd.Timestamp) -> float:
    dates = dates_by_team.get(team, [])
    i = bisect.bisect_left(dates, day)
    return (day - dates[i - 1]).days if i else np.nan


def line_features(lines: pd.DataFrame, logs: pd.DataFrame) -> pd.DataFrame:
    """Per line, every feature from the player's games before its date. lines: game_date, player_id_ESPN, team,
    home, away, bet_type, line, market over %; logs: models.prepare_logs output."""
    logs = logs.sort_values(['Date', 'game_id'])
    by_player = {pid: g for pid, g in logs.groupby('player_id_ESPN')}
    dates_by_team = {team: sorted(g['Date'].unique()) for team, g in logs.groupby('team')}
    out = {f: np.full(len(lines), np.nan) for f in FEATURES}
    for i, row in enumerate(lines.itertuples(index=False)):
        games = by_player.get(row.player_id_ESPN)
        if games is None:
            continue
        games = games[games['Date'] < row.game_date]
        if len(games) < MIN_GAMES:
            continue
        stat, line, day = row.bet_type, row.line, pd.Timestamp(row.game_date)
        values = games[stat]
        team = row.team
        opp = row.away if team == row.home else row.home
        stint = current_stint(games)
        out['hits_l10'][i] = feature_hits(values, line, getattr(row, 'market_over') / 100)
        out['minutes'][i] = feature_minutes(stint)
        out['venue'][i] = feature_venue(games, stat, team == row.home)
        out['rest'][i] = feature_rest(_rest(dates_by_team, team, day), _rest(dates_by_team, opp, day))
        out['vs_opp'][i] = feature_vs_opp(games[games['OPP'].str.lower() == opp], stat, line, values.std())
        out['volume'][i] = feature_volume(stint, stat)
    return lines.assign(**out)


def _fit_offset(offset: np.ndarray, f: np.ndarray, y: np.ndarray, iterations: int = 50) -> float:
    """β of logit(p) = offset + β·f by Newton's method."""
    beta = 0.0
    for _ in range(iterations):
        p = _sigmoid(offset + beta * f)
        hessian = np.sum(f * f * p * (1 - p))
        if hessian <= 0:
            break
        step = np.sum(f * (y - p)) / hessian
        beta += step
        if abs(step) < 1e-10:
            break
    return float(beta)


def _baseline(fit_sides: pd.DataFrame, test_sides: pd.DataFrame):
    """The current model calibrated in the dashboards' form (a, b) on the fit part: p0 on both parts."""
    coef = fit_coefficients(fit_sides)
    p0 = lambda s: _sigmoid(features(s['market'].values, s['model'].values, s['over'].values)
                            @ np.array([coef[k] for k in ('a', 'b', 'c', 'd')]))
    return p0(fit_sides), p0(test_sides)


def test_feature(lines: pd.DataFrame, feature: str) -> Dict:
    """β fitted on the earlier lines, log loss difference (p1 − p0) on the later ones with its night range."""
    fit_part, test_part = split(lines)
    fit_sides, test_sides = sides(fit_part), sides(test_part)
    signed = lambda s, part: part.loc[s['line_id'], feature].values * np.where(s['over'], 1.0, -1.0)
    f_fit, f_test = signed(fit_sides, fit_part), signed(test_sides, test_part)
    keep_fit, keep_test = ~np.isnan(f_fit), ~np.isnan(f_test)
    if keep_fit.sum() < 100 or keep_test.sum() < 100:
        return {'feature': feature, 'lines': int(keep_test.sum() // 2), 'nights': 0}
    p0_fit, p0_test = _baseline(fit_sides, test_sides)
    beta = _fit_offset(_logit(p0_fit[keep_fit]), f_fit[keep_fit], fit_sides['won'].values[keep_fit])
    p1 = _sigmoid(_logit(p0_test[keep_test]) + beta * f_test[keep_test])
    won = test_sides['won'].values[keep_test]
    diff = _loss(won, p1) - _loss(won, p0_test[keep_test])
    nights = test_sides['game_date'].values[keep_test]
    low, high = night_bootstrap(nights, diff)
    return {'feature': feature, 'lines': int(keep_test.sum() // 2), 'nights': int(pd.Series(nights).nunique()),
            'beta': beta, 'vs model': float(diff.mean()), 'range low': low, 'range high': high}


def verdicts(results: Dict[str, pd.DataFrame]) -> Dict[str, Dict]:
    """Each feature's status (LIFT / NO_LIFT, UNTESTED for NOT_TESTABLE) and over_sign (β's sign on 2022/23)."""
    old = results['2022'].set_index('feature')
    new = results['superbet'].set_index('feature') if 'superbet' in results else None
    out = {}
    for feature in FEATURES:
        r = old.loc[feature]
        helped = pd.notna(r.get('range high')) and r['range high'] < 0
        contradicted = new is not None and feature in new.index and pd.notna(new.loc[feature].get('range low')) \
            and new.loc[feature, 'range low'] > 0
        out[feature] = {'status': LIFT if helped and not contradicted else NO_LIFT,
                        'over_sign': 1 if pd.notna(r.get('beta')) and r['beta'] >= 0 else -1,
                        'beta_2022': None if pd.isna(r.get('beta')) else float(r['beta']),
                        'vs_model_2022': None if pd.isna(r.get('vs model')) else float(r['vs model'])}
    for feature, why in NOT_TESTABLE.items():
        out[feature] = {'status': UNTESTED, 'why': why}
    return out


def superbet_lines() -> pd.DataFrame:
    """Settled Superbet lines priced by the current model (backtest/calibrate.py's), with the player's id and team
    from the stored games, and the logs of the current season they're compared with."""
    from espn_scraper import CURRENT_SEASON, SEASONS
    from espn_scraper.storage import load_games, load_player_gamelogs
    from backtest.calibrate import _superbet_sources
    from models import prepare_logs
    logs = prepare_logs(load_player_gamelogs(sorted(SEASONS)))
    t = _superbet_sources(logs, load_games(sorted(SEASONS)))
    if t.empty:
        return t, logs
    ids = logs.groupby('player_name_ESPN')['player_id_ESPN'].last()
    t = t.assign(player_id_ESPN=t['name_ESPN'].map(ids), game_date=pd.to_datetime(t['game_date']))
    teams = logs.sort_values('Date').groupby('player_id_ESPN')['team'].last()
    t = t.assign(team=t['player_id_ESPN'].map(teams)).dropna(subset=['player_id_ESPN', 'team'])
    return t.reset_index(drop=True), logs[logs['season_id'] == CURRENT_SEASON]


def run(sources: Dict[str, tuple]) -> Dict[str, pd.DataFrame]:
    results = {}
    for name, (lines, logs) in sources.items():
        if lines.empty:
            continue
        lines = line_features(lines.rename(columns={'market over %': 'market_over'}), logs) \
            .rename(columns={'market_over': 'market over %'})
        results[name] = pd.DataFrame([test_feature(lines, f) for f in FEATURES])
        log.info("%s: %d lines", name, len(lines))
    return results


def report(results: Dict[str, pd.DataFrame], verdict: Dict[str, Dict]) -> str:
    parts = ["# Context reasons against the props model on unseen lines", "",
             "*vs model* = the log loss with the feature minus without it, per line side (below 0 = the feature "
             "helped), with the 95% range from resampling whole nights; *beta* = its weight fitted on the earlier "
             "lines (positive = more of it, more Over). See backtest/reason_lift.py.", ""]
    for name, table in results.items():
        parts += [f"## {'Unibet 2022/23' if name == '2022' else 'Superbet 2026/27'}", "", markdown(table, '{:.4f}'), ""]
    parts += ["## Verdicts (what the panel shows)", "",
              markdown(pd.DataFrame([{'feature': f, 'status': v['status'], 'why': v.get('why', '')}
                                     for f, v in verdict.items()])), ""]
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--no-superbet', action='store_true', help="the 2022/23 lines only")
    args = parser.parse_args()
    from backtest.data_2022 import load_logs_2022
    from models import prepare_logs

    logs_2022, _ = load_logs_2022()
    sources = {'2022': (lines_2022(), prepare_logs(logs_2022))}
    if not args.no_superbet:
        sources['superbet'] = superbet_lines()
    results = run(sources)
    verdict = verdicts(results)
    atomic_write_text(LIFT_FILE, json.dumps({'features': verdict}, indent=2))
    text = report(results, verdict)
    atomic_write_text(REPORT, text)
    sys.stdout.reconfigure(errors='replace')
    print(text)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    main()
