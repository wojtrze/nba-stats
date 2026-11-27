"""Run with: python -m pytest backtest/test_calibration_terms.py"""
import numpy as np
import pandas as pd

import backtest  # noqa: F401  (puts dashboard/ on the path)
from backtest.calibration_terms import BASE, VARIANTS, evaluate, features, line_sides, report, verdicts


def lines(nights=20, per_night=200, over_bias=-0.6, seed=1):
    """Superbet-like lines whose Overs win less than the margin-free price says (an Under bias to find)."""
    rng = np.random.default_rng(seed)
    n = nights * per_night
    market = rng.uniform(0.35, 0.65, n)
    truth = 1 / (1 + np.exp(-(np.log(market / (1 - market)) + over_bias)))
    over_won = rng.random(n) < truth
    line = rng.choice([0.5, 1.5, 4.5, 20.5], n)
    return pd.DataFrame({
        'source': 'superbet', 'game_date': pd.Timestamp('2026-10-20') + pd.to_timedelta(np.arange(n) // per_night, 'D'),
        'event_id': np.arange(n) // 20, 'name_ESPN': [f'P{i}' for i in range(n)],
        'bet_type': rng.choice(['PTS', 'BLK', 'REB'], n), 'line': line,
        'actual': np.where(over_won, line + 0.5, line - 0.5),
        'market over %': 100 * market, 'raw over %': 100 * market, 'raw under %': 100 * (1 - market),
        'over_odds': 0.95 / market, 'under_odds': 0.95 / (1 - market)})


def test_features_sign_the_over_and_small_terms():
    s = line_sides(lines(nights=2, per_night=10))
    x = features(s, ['over', 'small', 'b_main'])
    assert set(x[s['over'].values, 0]) == {1.0} and set(x[~s['over'].values, 0]) == {-1.0}
    assert (x[s['line'].values > 1.5, 1] == 0).all()
    assert (x[:, 2] == 0).all()                   # model = market: no opinion to weigh


def test_2022_lines_without_event_id_get_one():
    t = lines(nights=2, per_night=10).drop(columns='event_id').assign(home='bos')
    assert line_sides(t)['event_id'].str.endswith('bos').all()


def test_evaluate_finds_a_planted_under_bias():
    r = evaluate(lines(), 'superbet').set_index('variant')
    assert list(r.index) == list(VARIANTS)
    assert r.loc[BASE, 'Δ vs base'] == 0
    assert '+over' in r.index and 'over=-' in r.loc['+over', 'coefficients']
    assert r.loc['+over', 'Δ high'] < 0           # held-out log loss clearly better
    v = verdicts(r.reset_index()).set_index('variant')
    assert v.loc['+over', '(a) log loss'] == 'pass'


def test_report_skips_empty_sources():
    text = report({'superbet': lines(nights=10, per_night=100), '2022': pd.DataFrame()})
    assert 'Superbet' in text and 'Unibet' not in text and 'Verdict' in text
