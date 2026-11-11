"""Sensitivity of real offers (harness output) to perturbations whose size comes from the data (read-only).

    python audit/reasons/sensitivity.py <harness pickle> [--json out.json]

Per priced line, with the player's games as of the night (same scope as the harness):
  minutes_se   projected mean × (1 ± SE of his mean minutes over the last 10 games / that mean)   [estimation noise]
  minutes_10   projected mean × (1 ± 10 %)                                                         [scenario]
  shooting_se  shot stats: projected mean × (1 ± SE of his make rate / rate, binomial on his attempts) [noise]
  odds_tick    the evaluated side's odds ± 0.05 (the no-vig price recomputed)                       [scenario]
  no_tax       the superbet_no_tax profile                                                         [scenario]
H1: the combo's chance with the pooled correlation prior, no correlation, and the player's own correlation only.
H6: the shrunk spread, the player's own spread and the league's.
H2: the player's rate ± 1.96 SE (binomial on attempts + the 200-attempt prior).
Reports how often the EV sign, the evaluated side, a mispricing signal's side or its 'clears' flips. The decision
can't flip: no threshold is admitted (decisions.ADMITTED_THRESHOLD is None), every game is NIE_OBSTAWIAJ.
"""
import json
import math
import os
import pickle
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path[:0] = [os.path.join(ROOT, 'dashboard'), ROOT, os.path.dirname(os.path.abspath(__file__))]
os.chdir(ROOT)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from metrics import break_even, calibrate, expected_return_100, no_vig, prop_probability  # noqa: E402
import mispricing as mp  # noqa: E402

SHOTS = {'PTS': ('FGM', 'FGA'), 'PA': ('FGM', 'FGA'), 'PR': ('FGM', 'FGA'), 'ARP': ('FGM', 'FGA'),
         '3PM': ('3PM', '3PA'), 'FGM': ('FGM', 'FGA'), 'FTM': ('FTM', 'FTA')}


def evaluate(values, line, over_odds, under_odds, mean, coef, profile='superbet_standard'):
    """Both sides' calibrated chance and EV; the evaluated side = higher EV (as price_props)."""
    m_over, m_under = no_vig(over_odds, under_odds)
    out = {}
    for side, m, odds in (('Over', m_over, over_odds), ('Under', m_under, under_odds)):
        p = calibrate(prop_probability(values, line, side, m, mean=mean)['p'], m, side, coef)
        out[side] = float(expected_return_100(p, odds, profile))
    side = max(out, key=out.get)
    return side, out[side]


def main():
    from harness import load
    from models import DEFAULT_SEASON_TYPES, load_calibration, top_up_logs
    path = sys.argv[1]
    r = pickle.load(open(path, 'rb'))
    props, odds, rotowire, logs, games, _ = load()
    coef = load_calibration()
    c, examples = Counter(), {}
    for night, n in r['nights'].items():
        night = pd.Timestamp(night)
        before = logs[logs['Date'] < night]
        season = before['season_id'].max()
        table = n['table']
        scope = top_up_logs(before[(before['season_id'] == season) & before['season_type'].isin(DEFAULT_SEASON_TYPES)],
                            before, season, table['player_id'].dropna().unique())
        prior = mp.pooled_correlations(scope)
        spreads = mp.league_spreads(scope)
        rates = mp.league_rates(scope)
        for l in n['lines']:
            row = l['row']
            g = scope[scope['player_id_ESPN'] == row['player_id']].sort_values('Date')
            if len(g) < 3:
                continue
            values = g[row['bet_type']].astype(float)
            base_side, base_ev = row['side'], row['ev net 100']
            mean = row['proj avg']
            c['lines'] += 1

            def record(name, side, ev, scenario):
                c[f'{name}:n'] += 1
                if side != base_side:
                    c[f'{name}:side_flip'] += 1
                if np.sign(ev) != np.sign(base_ev):
                    c[f'{name}:ev_sign_flip'] += 1
                    examples.setdefault(name, (row['name'], row['bet_type'], row['line'], base_side,
                                               round(base_ev, 1), side, round(ev, 1), scenario))

            mins = g['MIN'].tail(10).astype(float)
            if len(mins) >= 3 and mins.mean() > 0:
                rel = mins.std() / math.sqrt(len(mins)) / mins.mean()
                c['minutes_se_rel_sum'] += rel
                for sgn in (-1, 1):
                    record('minutes_se', *evaluate(values, row['line'], row['over_odds'], row['under_odds'],
                                                   mean * (1 + sgn * rel), coef), 'noise')
                    record('minutes_10', *evaluate(values, row['line'], row['over_odds'], row['under_odds'],
                                                   mean * (1 + sgn * 0.10), coef), 'scenario')
            if row['bet_type'] in SHOTS:
                made, att = SHOTS[row['bet_type']]
                tm, ta = g[made].sum(), g[att].sum()
                if ta > 0 and 0 < tm < ta:
                    rate = tm / ta
                    rel = math.sqrt(rate * (1 - rate) / ta) / rate
                    share = 1.0 if row['bet_type'] in ('3PM', 'FGM', 'FTM') else 0.8   # PTS mostly from field goals
                    for sgn in (-1, 1):
                        record('shooting_se', *evaluate(values, row['line'], row['over_odds'], row['under_odds'],
                                                        mean * (1 + sgn * share * rel), coef), 'noise')
            for d in (-0.05, 0.05):
                o, u = row['over_odds'], row['under_odds']
                o, u = (o + d, u) if base_side == 'Over' else (o, u + d)
                if min(o, u) > 1.01:
                    record('odds_tick', *evaluate(values, row['line'], o, u, mean, coef), 'scenario')
            record('no_tax', *evaluate(values, row['line'], row['over_odds'], row['under_odds'], mean, coef,
                                       'superbet_no_tax'), 'scenario')

            # mispricing variants on this player's lines (once per player/event: take the line's own stat)
            lines = table[(table['player_id'] == row['player_id']) & (table['event_id'] == row['event_id'])]
            quoted = mp._quoted(lines)
            stat = row['bet_type']
            recent = g.tail(mp.RECENT)
            if stat in mp.COMBOS and len(recent) >= mp.MIN_GAMES and all(s in quoted.index for s in mp.COMBOS[stat]) \
                    and stat in quoted.index:
                parts = {s: {'line': float(quoted.loc[s, 'line']),
                             'p_over': no_vig(quoted.loc[s, 'over_odds'], quoted.loc[s, 'under_odds'])[0]}
                         for s in mp.COMBOS[stat]}
                pb = no_vig(quoted.loc[stat, 'over_odds'], quoted.loc[stat, 'under_odds'])[0]
                eye = pd.DataFrame(np.eye(3), ['PTS', 'REB', 'AST'], ['PTS', 'REB', 'AST'])
                res = {}
                for name, pr, rr in (('pooled', prior, recent), ('zero', eye, recent)):
                    res[name] = mp.combo_over_from_parts(parts, float(quoted.loc[stat, 'line']), rr, pr)
                if None not in res.values():
                    c['H1:n'] += 1
                    sides = {k: v >= pb for k, v in res.items()}
                    c['H1:side_flip_zero_corr'] += sides['pooled'] != sides['zero']
                    c['H1:abs_diff_pp_sum'] += 100 * abs(res['pooled'] - res['zero'])
            if stat in mp.SMALL_STATS and stat in quoted.index and quoted.loc[stat, 'line'] <= mp.SMALL_LINE \
                    and len(recent) >= mp.MIN_GAMES and stat in spreads:
                v = recent[stat].astype(float)
                if v.mean() > 0:
                    own = v.var() / v.mean()
                    k = len(v)
                    shr = (k * own + mp.PRIOR_SPREAD_GAMES * spreads[stat]) / (k + mp.PRIOR_SPREAD_GAMES)
                    line = float(quoted.loc[stat, 'line'])
                    oo, uu = quoted.loc[stat, 'over_odds'], quoted.loc[stat, 'under_odds']
                    pb = no_vig(oo, uu)[0]
                    mean0 = mp.market_mean(line, pb, 1.0, 1.0)
                    from metrics import count_over
                    res = {name: count_over(mean0, max(s, 1.0) * mean0, line)
                           for name, s in (('shrunk', shr), ('own', own), ('league', spreads[stat]))}
                    c['H6:n'] += 1
                    c['H6:own_vs_shrunk_side_flip'] += (res['own'] >= pb) != (res['shrunk'] >= pb)
                    for name in ('shrunk', 'own', 'league'):
                        p_side = res[name] if res[name] >= pb else 1 - res[name]
                        odds_side = oo if res[name] >= pb else uu
                        c[f'H6:clears_{name}'] += p_side >= float(break_even(odds_side))
            if stat in mp.SHOTS and stat in quoted.index and mp.SHOTS[stat] in quoted.index and stat in rates:
                sig = [s for s in l['signals_ui'] if s['hypothesis'] == 'H2' and s['bet_type'] == stat]
                if sig:
                    s = sig[0]
                    se = math.sqrt(s['player_rate'] * (1 - s['player_rate']) / (s['attempted'] + mp.PRIOR_ATTEMPTS))
                    att = mp.SHOTS[stat]
                    a_avg, a_var = recent[att].astype(float).mean(), recent[att].astype(float).var()
                    m_avg, m_var = recent[stat].astype(float).mean(), recent[stat].astype(float).var()
                    attempts = mp.market_mean(float(quoted.loc[att, 'line']),
                                              no_vig(quoted.loc[att, 'over_odds'], quoted.loc[att, 'under_odds'])[0],
                                              a_avg, a_var)
                    from metrics import count_over
                    flips = 0
                    for sgn in (-1, 1):
                        mean2 = attempts * (s['player_rate'] + sgn * 1.96 * se)
                        p_over = count_over(mean2, m_var / m_avg * mean2, s['line'])
                        side2 = 'Over' if p_over >= no_vig(quoted.loc[stat, 'over_odds'],
                                                           quoted.loc[stat, 'under_odds'])[0] else 'Under'
                        flips += side2 != s['side']
                    c['H2:n'] += 1
                    c['H2:side_flip_within_rate_ci'] += flips > 0
    out = {'counts': dict(sorted(c.items())), 'examples': examples}
    print(json.dumps(out, indent=1, default=str))
    if '--json' in sys.argv:
        json.dump(out, open(sys.argv[sys.argv.index('--json') + 1], 'w'), indent=1, default=str)


if __name__ == '__main__':
    main()
