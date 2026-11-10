import numpy as np
import pandas as pd

import whatif
from models import price_line

VALUES = pd.Series([10, 14, 18, 12, 16, 20, 11, 15, 13, 17, 19, 9.0])
COEF = {'a': 1.139, 'b': 0.17, 'c': 0.0, 'd': 0.0}


def test_evaluate_prices_the_side_as_the_table_does():
    row = price_line(VALUES, 14.5, 15.8, 1.85, 1.95, COEF)
    side = row['side']
    side_odds, other = (1.85, 1.95) if side == 'Over' else (1.95, 1.85)
    e = whatif.evaluate(VALUES, 14.5, 15.8, side, side_odds, other, COEF)
    assert np.isclose(e['p win %'], row['p win %']) and np.isclose(e['break-even %'], row['break-even net %'])
    assert np.isclose(e['ev net 100'], row['ev net 100']) and np.isclose(e['distance pp'], row['edge net pp'])


def test_whole_number_lines_keep_the_push_chance():
    row = price_line(VALUES, 14.0, 15.8, 1.85, 1.95, COEF)
    e = whatif.evaluate(VALUES, 14.0, 15.8, 'Over', 1.85, 1.95, COEF)
    assert row['p push %'] > 0
    if row['side'] == 'Over':
        assert np.isclose(e['ev net 100'], row['ev net 100'])


def test_needed_odds_is_the_first_price_above_break_even():
    found = whatif.needed_odds(VALUES, 14.5, 15.8, 'Over', 1.85, 1.95, COEF)
    ev = lambda o: whatif.evaluate(VALUES, 14.5, 15.8, 'Over', o, 1.95, COEF)['ev net 100']
    assert found is not None and ev(found) > 0 and not ev(round(found - 0.01, 2)) > 0
    # holding our chance fixed would ask for less: the calibration follows the price down
    assert found > 100 / (0.88 * whatif.evaluate(VALUES, 14.5, 15.8, 'Over', 1.85, 1.95, COEF)['p win %'])
    assert whatif.needed_odds(VALUES, 14.5, 15.8, 'Over', found, 1.95, COEF) == found


def test_needed_line_moves_in_the_sides_favour_or_gives_up():
    raw = {'a': 1.0, 'b': 1.0, 'c': 0.0, 'd': 0.0}                    # the model's own chance: lines matter
    over = whatif.needed_line(VALUES, 14.5, 15.8, 'Over', 1.85, 1.95, raw, VALUES.std())
    under = whatif.needed_line(VALUES, 14.5, 12.0, 'Under', 1.85, 1.95, raw, VALUES.std())
    assert over is not None and over < 14.5 and over % 1 == 0.5
    assert under is not None and under > 14.5
    assert whatif.needed_line(VALUES, 14.5, 15.8, 'Over', 1.20, 4.5, COEF, 0.1) is None    # nothing within reach


def test_gap_in_spreads():
    assert np.isclose(whatif.gap_in_spreads(16, 14, 4, 10), 0.5)
    assert np.isnan(whatif.gap_in_spreads(16, 14, 0, 10)) and np.isnan(whatif.gap_in_spreads(16, 14, 4, 3))
    assert np.isnan(whatif.gap_in_spreads(np.nan, 14, 4))


def test_odds_paths_and_move_share():
    snaps = pd.DataFrame({
        'fetched_at': ['2026-11-09T12:00:00Z', '2026-11-09T20:00:00Z', '2026-11-09T12:00:00Z',
                       '2026-11-10T02:00:00Z'],
        'event_id': [1, 1, 1, 1], 'name_ESPN': ['A', 'A', 'B', 'B'], 'bet_type': ['PTS'] * 4,
        'line': [14.5, 14.5, 9.5, 9.5], 'over_odds': [1.80, 2.10, 1.90, 2.50], 'under_odds': [2.0, 1.7, 1.9, 1.5],
        'start_time': ['2026-11-10T00:00:00Z'] * 4})
    quotes = pd.DataFrame({'fetched_at': ['2026-11-09T22:00:00Z'], 'event_id': [1], 'name_ESPN': ['B'],
                           'bet_type': ['PTS'], 'line': [10.5], 'over_odds': [3.0], 'under_odds': [1.3]})
    paths = whatif.odds_paths(snaps, quotes)
    a, b = (paths[paths['name_ESPN'] == n].iloc[0] for n in 'AB')
    assert a['max over'] == 2.10                       # rose at the same line
    assert b['max over'] == 1.90                       # 3.0 was another line; 2.5 came after tip-off
    share = whatif.move_share(paths, 'PTS', 'Over', 1.15)
    assert share == {'share': 50.0, 'lines': 2, 'nights': 1}
    assert np.isnan(whatif.move_share(paths, 'REB', 'Over', 1.1)['share'])


def _night():
    rows = []
    for name, line, proj, sd, games, over, under in (('A', 14.5, 15.8, 4.0, 12, 1.85, 1.95),
                                                     ('B', 9.5, 8.0, 0.0, 12, 1.90, 1.90),
                                                     ('C', 20.5, 22.0, 5.0, 3, 1.70, 2.10)):
        priced = price_line(VALUES, line, proj, over, under, COEF)
        rows.append({'name': name, 'line': line, 'proj avg': proj, 'sd': sd, 'games': games, 'over_odds': over,
                     'under_odds': under} | priced)
    return pd.DataFrame(rows)


def test_night_gaps_needs_a_usable_spread():
    g = whatif.night_gaps(_night())
    assert np.isclose(g.loc[0, 'gap sd'], (15.8 - 14.5) / 4)
    assert np.isnan(g.loc[1, 'gap sd']) and np.isnan(g.loc[2, 'gap sd'])     # sd 0; fewer than 5 games
    assert np.allclose(g['distance pp'], g['edge net pp'])


def test_nearest_orders_by_distance_and_finds_the_odds():
    g = whatif.night_gaps(_night())
    top = whatif.nearest(g, lambda r: VALUES, COEF, n=2)
    assert len(top) == 2 and top['distance pp'].is_monotonic_decreasing
    r = top.iloc[0]
    side_odds, other = (r['over_odds'], r['under_odds']) if r['side'] == 'Over' else (r['under_odds'], r['over_odds'])
    assert top.loc[0, 'needed odds'] == whatif.needed_odds(VALUES, r['line'], r['proj avg'], r['side'], side_odds,
                                                           other, COEF)
