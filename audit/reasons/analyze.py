"""Audit checks over the harness output (read-only). Prints counts and examples per check; writes a JSON summary.

    python audit/reasons/analyze.py <dir with fetch_*.pkl> [--json out.json]

Every number here is computed again from the saved rows and the player's games with code written for the audit
(scipy's distributions, own formulas), not by calling the production function that produced it, except where a
check is about what the production code emits (then the emitted text/fields are read).
"""
import glob
import json
import math
import os
import pickle
import re
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path[:0] = [os.path.join(ROOT, 'dashboard'), ROOT]

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats as ss  # noqa: E402

CAL = json.load(open(os.path.join(ROOT, 'data', 'backtest', 'calibration.json'), encoding='utf-8'))['coefficients']


# --- independent re-implementation of the props chance (from the documented method, scipy distributions) ---

def lg(p):
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


def p_over_count(mean, var, line):
    """P(X > line) for a count with this mean/var: scipy nbinom if overdispersed else poisson."""
    mean = max(mean, 1e-6)
    k = math.floor(line)
    if var > mean * 1.0001:
        n = mean ** 2 / (var - mean)
        p = mean / var
        return float(ss.nbinom.sf(k, n, p))
    return float(ss.poisson.sf(k, mean))


def indep_p_win(values, line, side, market, mean, coef=CAL, prior=10):
    values = np.asarray(values, dtype=float)
    n = len(values)
    hits = (values > line).sum() if side == 'Over' else (values < line).sum()
    hit = (hits + prior * market) / (n + prior)
    if n >= 3:
        avg = values.mean()
        var = values.var(ddof=1) * (mean / avg if avg > 0 else 1)
        whole = float(line).is_integer()
        cut = line + 0.5 if whole and side == 'Over' else line - 0.5 if whole else line
        over = p_over_count(mean, var, cut)
        w = n / (n + prior)
        dist = w * (over if side == 'Over' else 1 - over) + (1 - w) * market
        p = (hit + dist) / 2
    else:
        p = hit
    z = coef['a'] * lg(market) + coef['b'] * (lg(p) - lg(market)) + coef['c'] * (side == 'Over') + coef['d']
    return 1 / (1 + math.exp(-z)), p


def nv(o, u):
    return (1 / o) / (1 / o + 1 / u)


def load(paths):
    out = []
    for p in paths:
        r = pickle.load(open(p, 'rb'))
        for night, n in r['nights'].items():
            for l in n['lines']:
                l['_fetch'], l['_night'], l['_replay_only'] = r['fetched_at'], night, r['replay_only']
                out.append(l)
            n['_fetch'], n['_replay_only'] = r['fetched_at'], r['replay_only']
    return out, [pickle.load(open(p, 'rb')) for p in paths]


def main():
    d = sys.argv[1]
    paths = sorted(glob.glob(os.path.join(d, 'fetch_*.pkl')))
    lines, fetches = load(paths)
    summary = {'fetches': [{'fetched_at': f['fetched_at'], 'replay_only': f['replay_only'],
                            'saved_calibration': f['saved_calibration'],
                            'lines': sum(len(n['lines']) for n in f['nights'].values())} for f in fetches]}
    ex = defaultdict(list)
    c = Counter()

    from metrics import ACTIVE_PROFILE  # noqa: F401  (only for the label)
    for l in lines:
        row, bet, R = l['row'], l['bet'], l['reasons_en']
        stat, side, line = row['bet_type'], row['side'], row['line']
        c['lines'] += 1
        # --- A1 economics, recomputed independently ---
        o, u = row['over_odds'], row['under_odds']
        m_over = nv(o, u)
        m_side = m_over if side == 'Over' else 1 - m_over
        odds = o if side == 'Over' else u
        p_win = row['p win %'] / 100
        be = 1 / (0.88 * odds)
        ev = 100 * (p_win * 0.88 * odds - 1)
        if abs(100 * be - row['break-even net %']) > 1e-6 or abs(ev - row['ev net 100']) > 1e-6:
            c['A1_econ_mismatch'] += 1
        # independent chance from the player's games (needs the same games the harness used)
        # (stored on the bet dict? no: recompute from 'avg'/'proj avg' is impossible without values; done in tests)
        econ = [x for x in R if x['kind'] == 'economics']
        if econ and abs(econ[0]['value'] - row['p win %']) > 1e-9:
            c['A1_text_value_mismatch'] += 1
        # beyond_price consistency: final in impacts equals p win %
        imp = bet.get('impacts') or {}
        if imp and abs(imp['final'] - row['p win %']) > 1e-6:
            c['A1_final_vs_pwin_mismatch'] += 1
            if len(ex['A1_final_vs_pwin_mismatch']) < 3:
                ex['A1_final_vs_pwin_mismatch'].append((row['name'], stat, line, side, imp['final'], row['p win %']))
        if imp:
            calib_price = 100 / (1 + math.exp(-(CAL['a'] * lg(m_side))))
            c['A2_calib_price_gt_market'] += calib_price > 100 * m_side
            # share of the final chance's distance from the margin-free price that is the calibration's a, not the player
            total = row['p win %'] - 100 * m_side
            c['A2_lines_with_imp'] += 1
            if abs(total) > 0.5:
                c['A2_total_gt_0.5'] += 1
                if abs(calib_price - 100 * m_side) > abs(imp['beyond_price']):
                    c['A2_calibration_a_dominates'] += 1
            # non-additivity of drivers
            s = sum(imp[k] for k in ('availability', 'environment', 'opponent'))
            proj_part = None
            c['A2_driver_sum_abs_gt_beyond'] += abs(s) > abs(imp['beyond_price']) + 0.05
        # --- A3 hit-rate note: model uses all games' rate, text shows last 10 ---
        hist = [x for x in R if x.get('group') == 'history']
        if hist:
            m = re.search(r'in (\d+) of the last (\d+) games', hist[0]['text'])
            m_all = re.search(r', (\d+) of all (\d+)', hist[0]['text'])
            if m and m_all:
                r10 = int(m.group(1)) / int(m.group(2))
                rall = int(m_all.group(1)) / int(m_all.group(2))
                c['A3_hist_with_all'] += 1
                if abs(r10 - rall) >= 0.15:
                    c['A3_hist_l10_vs_all_15pp'] += 1
                    if len(ex['A3']) < 3:
                        ex['A3'].append(hist[0]['text'])
            elif m:
                c['A3_hist_only_l10_n_le_10'] += 1
            if 'from last season' in hist[0]['text'] or 'preseason' in hist[0]['text']:
                c['B_hist_mixed_sample'] += 1
        # --- teammates reason ---
        tm = [x for x in R if x.get('group') == 'availability' and x['kind'] == 'driver']
        if tm:
            c['C_teammates'] += 1
            if not bet.get('out_n'):
                c['C_teammates_n0'] += 1
        if bet.get('lineup adj') and bet.get('out_names') and not tm:
            c['C_teammates_dropped_incomplete'] += 1
        # --- mispricing shown ---
        for x in R:
            if x['kind'] != 'mispricing':
                continue
            c['M_shown'] += 1
            h = x['group']
            c[f'M_shown_{h}'] += 1
            text = x['text']
            clears = 'covers it' in text
            c[f'M_shown_{h}_clears'] += clears
            sig_line = re.search(r'“(Over|Under) (\S+) ([\d.]+)”', text)
            if sig_line:
                s_side, s_stat, s_line = sig_line.group(1), sig_line.group(2), float(sig_line.group(3))
                if s_stat != stat:
                    c['M_on_other_line'] += 1
                    if len(ex['M_on_other_line']) < 2:
                        ex['M_on_other_line'].append((row['name'], stat, line, side, text.split('  \n')[0]))
                elif s_side != side:
                    c['M_opposite_side_same_line'] += 1
                elif clears and row['ev net 100'] < 0:
                    c['M_clears_same_side_but_model_ev_neg'] += 1
                    if len(ex['M_clears_vs_model']) < 2:
                        ex['M_clears_vs_model'].append((row['name'], stat, line, side, round(row['ev net 100'], 1),
                                                        text.split('  \n')[0]))
            if 'On the exploration nights' in text:
                roi = float(re.search(r'([-+]?[\d.]+) per 100 staked after the tax\.$', text).group(1))
                c['M_exploration_shown'] += 1
                c['M_exploration_negative_roi'] += roi < 0
            if h == 'H6':
                m = re.search(r'spread ([\d.]+)× .*league\'s typical ([\d.]+)×', text)
                if m and float(m.group(1)) < float(m.group(2)):
                    c['M_H6_more_than_usual_false'] += 1
                if 'Over ' in (sig_line.group(1) + ' ' if sig_line else ''):
                    c['M_H6_over_side_with_below_why'] += 1
                    if len(ex['M_H6_over']) < 2:
                        ex['M_H6_over'].append(text.split('  \n')[:2])
        # every signal (shown or not), H6 direction and spread vs league
        for s in l['signals_ui']:
            if s['bet_type'] != stat:
                continue
            c[f'S_{s["hypothesis"]}'] += 1
            if s['hypothesis'] == 'H6':
                c['S_H6_over'] += s['side'] == 'Over'
                c['S_H6_spread_below_league'] += s['spread'] < s['league_spread']
            if s['hypothesis'] == 'H2':
                c['S_H2_prior_weight_gt_half'] += s['attempted'] < 200
        for s in l['signals_role']:
            if s['hypothesis'] == 'H5' and s['bet_type'] == stat:
                c['S_H5_role_only'] += 1
        # --- C: several mispricing reasons backing the same side of THIS line (same quote, same player's games)
        same = Counter()
        for x in R:
            if x['kind'] == 'mispricing':
                m = re.search(r'“(Over|Under) (\S+) ([\d.]+)”', x['text'])
                if m and m.group(2) == stat:
                    same[m.group(1)] += 1
        if any(v >= 2 for v in same.values()):
            c['C_two_signals_same_side_same_line'] += 1
            if len(ex['C_two_signals']) < 2:
                ex['C_two_signals'].append((row['name'], stat, line,
                                            [x['text'].split('  \n')[0] for x in R if x['kind'] == 'mispricing']))
        # drivers for/against counted as separate arguments although they all move one projected mean
        dirs = Counter(x['direction'] for x in R if x['kind'] == 'driver' and x['direction'])
        if sum(dirs.values()) >= 2 and len(dirs) == 1:
            c['C_drivers_all_same_direction_2plus'] += 1
        # --- warnings vs blockers both present
        kinds = Counter(x['kind'] for x in R)
        if kinds['blocker'] and kinds['mispricing']:
            c['B_blocker_and_mispricing_same_panel'] += 1
        if any(x['kind'] == 'mispricing' and 'covers it' in x['text'] for x in R) and kinds['blocker']:
            c['B_blocker_with_clearing_signal'] += 1
        # --- decision consistency
        dec = l['decision']
        c[f'D_{dec["status"]}_{dec["reason"]}'] += 1
        # --- uncertainty: is model range shown anywhere? (edge low exists in row)
        if not any('range' in x['text'] and x['kind'] == 'economics' for x in R):
            c['B_econ_without_model_range'] += 1

    # decisions per game
    for f in fetches:
        for night, n in f['nights'].items():
            t = n['table']
            for e, dcs in n['decisions'].items():
                c[f'G_{dcs["status"]}_{dcs["reason"]}'] += 1
                if dcs['reason'] == 'decision.reason.questionable':
                    rows = t[(t['event_id'] == e) & t['side'].fillna('').ne('')]
                    top = rows.sort_values('ev net 100', ascending=False).iloc[0]
                    c['G_questionable_top_is_red_flagged'] += bool(top['red flag'])
                    c['G_questionable_clean_lines_in_game'] += int((rows['red flag'].fillna('') == '').sum())
                    if len(ex['G_questionable']) < 3:
                        ex['G_questionable'].append((f['fetched_at'], top['game'], top['name'], top['RotoWire'],
                                                     round(top['ev net 100'], 1), top['red flag']))
                saved = t.loc[t['event_id'] == e, 'saved_decision'].dropna().unique().tolist()
                if saved and saved != [dcs['status']]:
                    c['G_replayed_decision_differs_from_saved'] += 1
    summary['counts'] = dict(sorted(c.items()))
    summary['examples'] = {k: v for k, v in ex.items()}
    print(json.dumps(summary, indent=1, ensure_ascii=False, default=str))
    if '--json' in sys.argv:
        with open(sys.argv[sys.argv.index('--json') + 1], 'w', encoding='utf-8') as fh:
            json.dump(summary, fh, indent=1, ensure_ascii=False, default=str)


if __name__ == '__main__':
    main()
