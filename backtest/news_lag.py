"""H4 stage 1 (docs/hipotezy_wyceny.md): after RotoWire news, how fast Superbet moves the teammates' lines, and
whether a line that still stood at our first read was worth taking.

    python -m backtest.news_lag [--d YYYY-MM-DD]

Events and reactions come from dashboard/news.py (the same code as the Overview's news window): a regular (20+
minutes over his last 10 games) ruled out, or back from Out, between two RotoWire versions at most 2 h apart, on a
game the schedule read before the news and at its slot. Only games read by the schedule count (the dashboard's
snapshots are too sparse to time a reaction).

  1. Speed (descriptive): how many teammate lines had moved or were withdrawn by our first read, how many moved
     only later and how many minutes after we saw the news, against the other team's lines between the same two
     reads (what moves without news), and how far the late moves went against the ~11 pp a side needs after tax.
  2. The signal (test a, decides): the side fixed in advance (2026-11-19) – a teammate's Over after an out, his
     Under after a return – on every teammate PTS / REB / AST / PRA line that still stood at our first read, taken
     at that read. Counted and judged exactly as backtest/mispricing_eval's signals: once per game, player, bet and
     side, only when the next read still had the same line and odds not worse, after-tax CLV and ROI with 99% ranges
     from resampling whole nights, the registry's verdict.

Nights up to D are the recognition nights (descriptive, they set nothing after the fact: the side and the signal
were fixed before looking at them); nights after D decide (at least 10). Writes data/backtest/news_lag.md and
news_lag.json (the summary the Overview's news window shows). The status in mispricing_status.json is set by hand.
"""
import argparse
import json
import logging
import os
from typing import Dict, List

import numpy as np
import pandas as pd

import backtest  # noqa: F401  (puts dashboard/ on the path)
from backtest.mispricing_eval import economic, signals
from backtest.run import OUT_DIR, markdown
from news import (MOVED_EARLY, MOVED_LATER, NEEDED_PP, NEVER, WITHDRAWN, _night, cases, find_events,
                  lineup_versions, offers, player_ids, regulars_by_night, signal_rows)
from safe_io import atomic_write_text

log = logging.getLogger(__name__)

REPORT_FILE = os.path.join(OUT_DIR, 'news_lag.md')
SUMMARY_FILE = os.path.join(OUT_DIR, 'news_lag.json')
D = '2026-11-19'
KINDS = (MOVED_EARLY, WITHDRAWN, MOVED_LATER, NEVER)


def speed(found: List) -> pd.DataFrame:
    """Per event kind (out / return, then all): events, nights, the teammate lines by kind, the share that reacted
    by our read, the other team's share moving between the same reads, the median minutes until a late move and
    the median late move in pp."""
    rows = []
    for kind in ('out', 'return', 'all'):
        part = [(e, c) for e, c in found if kind == 'all' or e.kind == kind]
        lines = pd.concat([c['lines'] for _, c in part if len(c['lines'])] or [pd.DataFrame(columns=['kind'])])
        counts = lines['kind'].value_counts()
        n = len(lines)
        base = np.sum([c['others'] for _, c in part], axis=0) if part else (0, 0)
        late = lines[lines['kind'] == MOVED_LATER] if n else lines
        rows.append({'news': kind, 'events': len(part), 'nights': len({e.night for e, _ in part}), 'lines': n,
                     **{k: int(counts.get(k, 0)) for k in KINDS},
                     'reacted by our read %': 100 * (counts.get(MOVED_EARLY, 0) + counts.get(WITHDRAWN, 0)) / n
                     if n else np.nan,
                     'other team moved %': 100 * base[0] / base[1] if base[1] else np.nan,
                     'late: median min': late['minutes to move'].median() if len(late) else np.nan,
                     'late: median pp': late['late move pp'].median() if len(late) else np.nan})
    return pd.DataFrame(rows)


def evaluate(found: List, offered: pd.DataFrame, logs: pd.DataFrame, d, closing=None) -> Dict:
    """{'speed': {period: table}, 'a': {period: economic row}} for 'recognition' (nights ≤ d) and 'evaluation'."""
    d = pd.Timestamp(d)
    settled = set(logs['Date'].unique())
    outputs = pd.concat([signal_rows(e, c) for e, c in found] or [pd.DataFrame()], ignore_index=True)
    sig = signals(outputs[outputs['night'].isin(settled)], offered, logs, closing) if len(outputs) else outputs
    covered = pd.Series(_night(offered['tip']).unique())
    covered = covered[covered.isin(settled)]
    result = {'speed': {}, 'a': {}}
    for period, keep in (('recognition', lambda n: n <= d), ('evaluation', lambda n: n > d)):
        result['speed'][period] = speed([(e, c) for e, c in found if keep(e.night)])
        s = sig[keep(sig['night'])] if len(sig) else sig
        result['a'][period] = economic(s, int(keep(covered).sum()))
    return result


def report(result: Dict, d) -> str:
    text = ["# H4 stage 1: RotoWire news and the speed of Superbet's lines", "",
            __doc__.split("\n\n", 2)[2].strip(), ""]
    for period, title in (('evaluation', f"Evaluation (nights after {d}): decides"),
                          ('recognition', f"Recognition (nights up to {d}): descriptive")):
        a = result['a'][period]
        text += [f"## {title}", "", "### Speed", "", markdown(result['speed'][period]), "",
                 f"A side needs about {NEEDED_PP} pp after tax; *late: median pp* is how far the chance moved after "
                 f"our read on the lines that stood (same line).", "",
                 "### The signal (after tax)", "", markdown(pd.DataFrame([a])), ""]
    return "\n".join(text)


def summary(result: Dict, d) -> Dict:
    """What the Overview's news window says about the record so far (plain numbers, JSON-safe)."""
    clean = lambda v: None if v is None or (isinstance(v, float) and np.isnan(v)) else \
        (v.item() if isinstance(v, np.generic) else v)
    out = {'d': str(pd.Timestamp(d).date()), 'updated': pd.Timestamp.now(tz='UTC').isoformat(timespec='minutes')}
    for period in ('recognition', 'evaluation'):
        a = result['a'][period]
        sp = result['speed'][period]
        every = sp[sp['news'] == 'all'].iloc[0]
        out[period] = {k: clean(a.get(k)) for k in ('nights', 'signals', 'settled', 'won %', 'ROI after tax %',
                                                     'with a close', 'CLV after tax %', 'CLV low', 'CLV high',
                                                     'verdict', 'why')}
        out[period] |= {'events': clean(every['events']),
                        'reacted by our read %': clean(every['reacted by our read %']),
                        'other team moved %': clean(every['other team moved %'])}
    return out


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument('--d', default=D, help="D, the last recognition night (default %(default)s)")
    args = parser.parse_args()
    from espn_scraper import SEASONS
    from espn_scraper.storage import load_player_gamelogs, load_snapshot
    from name_resolver import NameResolver
    from tracking import closing_props
    read = load_snapshot
    logs = load_player_gamelogs(sorted(SEASONS))
    logs = logs[logs['season_type'] != 'pre'].assign(Date=lambda x: pd.to_datetime(x['Date']))
    logs['player_id_ESPN'] = logs['player_id_ESPN'].astype('Int64')
    props, quotes, fetches = read('superbet_props'), read('superbet_prop_quotes'), read('superbet_event_fetches')
    offered = offers(props, quotes, fetches)
    offered = offered[offered['source'] == 'schedule'].copy()
    offered['player_id_ESPN'] = player_ids(offered, props, logs)
    versions = lineup_versions(NameResolver(logs).add_ids(read('rotowire_lineups')))
    events = find_events(versions, regulars_by_night(logs, list(versions)))
    team_of = logs.sort_values('Date').drop_duplicates('player_id_ESPN', keep='last') \
        .set_index('player_id_ESPN')['team'].to_dict()
    teams = props.drop_duplicates('event_id').set_index('event_id')[['home', 'away']]
    found = cases(events, offered, teams, team_of)
    log.info("%d events (%s), %d with a game read before and at the news", len(events),
             events['kind'].value_counts().to_dict(), len(found))
    result = evaluate(found, offered, logs, args.d, closing_props(quotes, fetches))
    text = report(result, args.d)
    atomic_write_text(REPORT_FILE, text)
    atomic_write_text(SUMMARY_FILE, json.dumps(summary(result, args.d), indent=2, ensure_ascii=False))
    print(text)


if __name__ == '__main__':
    main()
