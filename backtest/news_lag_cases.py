"""H4 case look (docs/hipotezy_wyceny.md): when RotoWire ruled a regular out, how Superbet's lines reacted.

    python -m backtest.news_lag_cases

Descriptive only: no detector, nothing in the app, no verdict. It lists real cases so the user can see whether a lag
exists at all before stage 1 proper (which waits for about 10 fully covered nights).

An event: between two consecutive RotoWire versions of a night (saved at most MAX_VERSION_GAP apart, so an outage
doesn't look like news) a player averaging at least MIN_MINUTES over his last 10 games went from playing (listed with
play_pct > 0, or not listed while his team was) to Out (play_pct 0). A scheduled slot reads RotoWire and then
Superbet under one time stamp, so the version's slot is also our first Superbet read after the news. Only games the
schedule read both before and at that slot count.

For each event:
  - his own lines: still offered at our first read after the news, or already withdrawn (Superbet knew by then; when
    they were gone at the read before, Superbet knew before our RotoWire read);
  - each teammate's PTS / REB / AST / PRA: line and margin-free Over chance at the read before the news, at our first
    read after it and at the close (the last read before tip-off). 'moved by our read' = Superbet was at least as
    fast as our hourly RotoWire check; 'moved later' = the line stood still at our read (the window H4 is about);
    'never' = it didn't move before tip-off.

Our RotoWire read is hourly (more often in the last hour), so the time we saw the news isn't the time it was posted.
Writes data/backtest/news_lag_cases.md.
"""
import logging
import os
from typing import List

import numpy as np
import pandas as pd

import backtest  # noqa: F401  (puts dashboard/ on the path)
from backtest.run import OUT_DIR, markdown
from news import (NEEDED_PP, cases, find_events, lineup_versions, offers, player_ids,  # noqa: F401
                  regulars_by_night)
from safe_io import atomic_write_text

log = logging.getLogger(__name__)

REPORT_FILE = os.path.join(OUT_DIR, 'news_lag_cases.md')
CASE_COLUMNS = ['player', 'stat', 'before', 'first read', 'close', 'kind', 'late move pp']


def _pl(ts) -> str:
    return f"{pd.Timestamp(ts).tz_convert('Europe/Warsaw'):%d.%m %H:%M}"


def report(cases: List) -> str:
    out = ["# H4 case look: RotoWire 'out' news and Superbet's lines", "",
           "Descriptive only (docs/hipotezy_wyceny.md, H4). Times are Polish. A line's value is 'line · margin-free "
           "Over chance'. *Moved by our read*: Superbet had moved it by the Superbet read of the slot that saw the "
           "news (at least as fast as our RotoWire check, which is hourly until the last hour). *Moved later*: it "
           "still stood at that read (the window H4 is about). *Withdrawn by our read*: gone at that read. "
           "*Never*: unchanged until tip-off.", ""]
    if not cases:
        return '\n'.join(out + ["No event yet: no regular ruled out between two RotoWire versions of a game the "
                                "schedule read before and after the news."]) + '\n'
    kinds, own, late, base = {}, {}, [], [0, 0]
    for event, c in cases:
        own[c['own']] = own.get(c['own'], 0) + 1
        base[0] += c['others'][0]
        base[1] += c['others'][1]
        if len(c['lines']):
            c['mates'] = (int((c['lines']['kind'] == 'moved by our read').sum()),
                          int(c['lines']['first read'].ne('gone').sum()))
        if len(c['lines']):
            for k, n in c['lines']['kind'].value_counts().items():
                kinds[k] = kinds.get(k, 0) + n
            late += c['lines'].loc[c['lines']['kind'] == 'moved later', 'late move pp'].dropna().tolist()
    n_lines = sum(kinds.values())
    out += ["## Summary", "",
            f"- **{len(cases)} events** on {len({e.night for e, _ in cases})} nights.",
            "- His own lines: " + '; '.join(f"{k}: {v}" for k, v in sorted(own.items())) + ".",
            f"- Teammates' lines ({n_lines}): " + '; '.join(f"{k}: {v}" for k, v in sorted(kinds.items())) + "."]
    mates = [sum(c['mates'][i] for _, c in cases if 'mates' in c) for i in (0, 1)]
    if mates[1] and base[1]:
        out.append(f"- **Baseline:** between the same two reads, {100 * mates[0] / mates[1]:.0f}% of the teammates' "
                   f"lines still offered moved ({mates[0]} of {mates[1]}), against {100 * base[0] / base[1]:.0f}% of "
                   f"the other team's lines in the same games ({base[0]} of {base[1]}): that much moves without "
                   f"news.")
    if late:
        out.append(f"- Lines that moved only later and kept their line: {len(late)}, median move "
                   f"{np.median(late):.1f} pp (max {max(late):.1f}); after tax a side needs about {NEEDED_PP} pp.")
    out += ["", "Few events and an hourly RotoWire read: this shows whether a lag exists at all, not its size. "
            "Stage 1 proper waits for about 10 fully covered nights.", ""]
    for event, c in cases:
        out += [f"## {event.name} ({event.team.upper()}) out, seen {_pl(event.seen_at)}, tip-off {_pl(c['tip'])}",
                "", f"Previous RotoWire version {_pl(event.prev_at)}. Reads: before {_pl(c['before'])}, first after "
                f"{_pl(c['after'])}, close {_pl(c['close'])}. His own lines: **{c['own']}**. The other team's lines "
                f"that moved between the same reads: {c['others'][0]} of {c['others'][1]}.", ""]
        if len(c['lines']):
            t = c['lines'][CASE_COLUMNS].assign(**{'late move pp': c['lines']['late move pp'].map(
                lambda v: '' if pd.isna(v) else f"{v:.1f}")})
            out += [markdown(t), ""]
        else:
            out += ["No teammate PTS / REB / AST / PRA lines at the read before.", ""]
    return '\n'.join(out) + '\n'


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    from espn_scraper import SEASONS
    from espn_scraper.storage import load_player_gamelogs, load_snapshot
    from name_resolver import NameResolver
    read = load_snapshot
    logs = load_player_gamelogs(sorted(SEASONS))
    logs = logs[logs['season_type'] != 'pre'].assign(Date=lambda x: pd.to_datetime(x['Date']))
    logs['player_id_ESPN'] = logs['player_id_ESPN'].astype('Int64')
    props, quotes, fetches = read('superbet_props'), read('superbet_prop_quotes'), read('superbet_event_fetches')
    offered = offers(props, quotes, fetches)
    offered = offered[offered['source'] == 'schedule'].copy()
    offered['player_id_ESPN'] = player_ids(offered, props, logs)
    lineups = NameResolver(logs).add_ids(read('rotowire_lineups'))
    versions = lineup_versions(lineups)
    events = find_events(versions, regulars_by_night(logs, list(versions)))
    events = events[events['kind'] == 'out']
    team_of = logs.sort_values('Date').drop_duplicates('player_id_ESPN', keep='last')         .set_index('player_id_ESPN')['team'].to_dict()
    teams = props.drop_duplicates('event_id').set_index('event_id')[['home', 'away']]
    found = cases(events, offered, teams, team_of)
    log.info("%d out events, %d with a game read before and after", len(events), len(found))
    text = report(found)
    atomic_write_text(REPORT_FILE, text)
    print(text)


if __name__ == '__main__':
    main()
