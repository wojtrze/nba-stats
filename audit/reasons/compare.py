"""Before/after comparison of two harness runs of the same fetch (read-only).

    python audit/reasons/compare.py <before.pkl> <after.pkl> [--show "Ace Bailey|FGA" ...]

Numbers that a reasons-only change must not move are compared exactly (prices, projections, adjustments, EV,
profile, evaluated side, game decisions, mispricing signals' numbers). Reasons are compared per line by
(kind, group) and by text; the summary counts what changed by group, with examples.
"""
import os
import pickle
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path[:0] = [os.path.join(ROOT, 'dashboard'), ROOT]

import numpy as np  # noqa: E402

FIXED = ['p win %', 'raw over %', 'raw under %', 'market over %', 'proj avg', 'adj avg', 'lineup adj', 'avg',
         'break-even net %', 'edge net pp', 'ev net 100', 'p push %', 'cost profile', 'side', 'side odds',
         'red flag', 'signal', 'bet']
SIGNAL = ['hypothesis', 'bet_type', 'line', 'side', 'p_ours', 'p_book', 'gap_pp', 'needed_pp', 'clears', 'odds']


def same(a, b):
    if isinstance(a, float) and isinstance(b, float) and np.isnan(a) and np.isnan(b):
        return True
    return a == b


def key(l):
    r = l['row']
    return (r['event_id'], r['name_ESPN'], r['bet_type'])


def main():
    before, after = (pickle.load(open(p, 'rb')) for p in sys.argv[1:3])
    shows = [a for i, a in enumerate(sys.argv) if i > 3 and sys.argv[i - 1] == '--show']
    c, numeric = Counter(), Counter()
    examples = {}
    for night, nb in before['nights'].items():
        na = after['nights'][night]
        for e, d in nb['decisions'].items():
            c['games'] += 1
            da = na['decisions'][e]
            if (d['status'], d['reason'], d['values']) != (da['status'], da['reason'], da['values']):
                numeric['decision'] += 1
        la = {key(l): l for l in na['lines']}
        for lb in nb['lines']:
            k = key(lb)
            l2 = la.get(k)
            c['lines'] += 1
            if l2 is None:
                numeric['line missing after'] += 1
                continue
            for col in FIXED:
                if not same(lb['row'].get(col), l2['row'].get(col)):
                    numeric[col] += 1
            if (lb['decision']['status'], lb['decision']['reason']) != (l2['decision']['status'],
                                                                       l2['decision']['reason']):
                numeric['line decision'] += 1
            for which in ('signals_ui', 'signals_role'):
                sb = [tuple(s[f] for f in SIGNAL) for s in lb[which]]
                sa = [tuple(s[f] for f in SIGNAL) for s in l2[which]]
                if sb != sa:
                    numeric[which] += 1
            ib, ia = lb['bet'].get('impacts') or {}, l2['bet'].get('impacts') or {}
            if any(not same(ib.get(x), ia.get(x)) for x in set(ib) | set(ia)):
                numeric['impacts'] += 1
            def keyed(reasons):
                seen = Counter()
                out = {}
                for r in reasons:          # several reasons can share a group (venue, rest, blowout; H1 × 2)
                    seen[(r['kind'], r['group'])] += 1
                    out[(r['kind'], r['group'], seen[(r['kind'], r['group'])])] = r
                return out

            for lang in ('en', 'pl'):
                rb, ra = keyed(lb[f'reasons_{lang}']), keyed(l2[f'reasons_{lang}'])
                for g in set(rb) | set(ra):
                    tag = f"{lang} {g[0]}/{g[1]}" + (f" #{g[2]}" if g[2] > 1 else '')
                    if g not in rb:
                        c[f'added   {tag}'] += 1
                    elif g not in ra:
                        c[f'removed {tag}'] += 1
                    elif rb[g]['text'] != ra[g]['text']:
                        c[f'text    {tag}'] += 1
                        if rb[g]['supports'] != ra[g]['supports']:
                            numeric[f'direction {tag}'] += 1
                    else:
                        continue
                    examples.setdefault(tag, (lb['row']['name'], k[2], rb.get(g, {}).get('text'),
                                              ra.get(g, {}).get('text')))
            name = f"{lb['row']['name']}|{k[2]}"
            if any(name.startswith(s.split('|')[0]) and name.endswith('|' + s.split('|')[1]) for s in shows):
                print(f"\n===== {name} {lb['row']['side']} {lb['row']['line']}")
                for lang in ('en', 'pl'):
                    print(f"--- before ({lang})")
                    for r in lb[f'reasons_{lang}']:
                        print(f"  [{r['kind']}/{r['group']}/{r['direction']}] {r['text']}")
                    print(f"--- after ({lang})")
                    for r in l2[f'reasons_{lang}']:
                        print(f"  [{r['kind']}/{r['group']}/{r['direction']}] {r['text']}")
    print(f"\nprofile before/after: {before.get('profile')} / {after.get('profile')}; "
          f"{c['games']} games, {c['lines']} lines")
    print("NUMBERS THAT MUST NOT MOVE:", dict(numeric) if numeric else "none changed")
    print("REASONS:")
    for k_, v in sorted((k_, v) for k_, v in c.items() if k_ not in ('games', 'lines')):
        print(f"  {k_}: {v}")
    print("FIRST EXAMPLE PER CHANGE:")
    for tag, (name, stat, b, a) in sorted(examples.items()):
        print(f"  [{tag}] {name} {stat}\n    before: {b}\n    after:  {a}")


if __name__ == '__main__':
    main()
