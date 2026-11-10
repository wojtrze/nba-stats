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
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

import backtest  # noqa: F401  (puts dashboard/ on the path)
from backtest.mispricing_eval import lineup_versions, offers, player_ids
from backtest.run import OUT_DIR, markdown
from safe_io import atomic_write_text

log = logging.getLogger(__name__)

REPORT_FILE = os.path.join(OUT_DIR, 'news_lag_cases.md')
MIN_MINUTES = 20
MAX_VERSION_GAP = pd.Timedelta(hours=2)
STATS = ('PTS', 'REB', 'AST', 'PRA')
NEEDED_PP = 11            # the registry's after-tax gap (docs/hipotezy_wyceny.md)
SAME = 0.5                # pp: a smaller change of the margin-free chance at the same line isn't a move


def _status(version: pd.DataFrame) -> pd.DataFrame:
    """One row per player of a version: team, play_pct (numeric)."""
    v = version.dropna(subset=['player_id_ESPN']).drop_duplicates('player_id_ESPN', keep='last')
    return v.assign(play_pct=pd.to_numeric(v['play_pct'], errors='coerce')).set_index('player_id_ESPN')


def find_events(versions: Dict, regulars: Dict) -> pd.DataFrame:
    """Out news between consecutive RotoWire versions: night, seen_at (the version's save time), prev_at, team,
    player_id_ESPN, name. regulars: {night: set of player ids averaging MIN_MINUTES before that night}."""
    rows = []
    for night, saved in versions.items():
        for (prev_at, prev), (seen_at, cur) in zip(saved, saved[1:]):
            if seen_at - prev_at > MAX_VERSION_GAP:
                continue
            p, c = _status(prev), _status(cur)
            out = c[c['play_pct'] == 0]
            for pid, row in out.iterrows():
                if pid not in regulars.get(night, set()):
                    continue
                was_playing = (pid in p.index and p.at[pid, 'play_pct'] > 0) or \
                              (pid not in p.index and row['team'] in set(p['team']))
                if was_playing:
                    rows.append({'night': night, 'seen_at': seen_at, 'prev_at': prev_at, 'team': row['team'],
                                 'player_id_ESPN': int(pid), 'name': row['name']})
    return pd.DataFrame(rows, columns=['night', 'seen_at', 'prev_at', 'team', 'player_id_ESPN', 'name'])


def regulars_by_night(logs: pd.DataFrame, nights) -> Dict:
    """{night: player ids whose last 10 games before that night average at least MIN_MINUTES}."""
    logs = logs.assign(MIN=pd.to_numeric(logs['MIN'], errors='coerce')).sort_values('Date')
    out = {}
    for night in nights:
        before = logs[logs['Date'] < night]
        avg = before.groupby('player_id_ESPN')['MIN'].apply(lambda m: m.tail(10).mean())
        out[night] = set(avg[avg >= MIN_MINUTES].index.astype(int))
    return out


def _over(row) -> float:
    if row is None or pd.isna(row['over_odds']) or pd.isna(row['under_odds']):
        return np.nan
    o, u = 1 / row['over_odds'], 1 / row['under_odds']
    return 100 * o / (o + u)


def _at(lines: pd.DataFrame, at) -> Dict:
    """{(name_ESPN, bet_type): row} of the lines offered at one read."""
    return {(r['name_ESPN'], r['bet_type']): r for _, r in lines[lines['at'] == at].iterrows()}


def _move(a, b) -> Optional[str]:
    """'line' when the line changed, 'price' when the chance at the same line moved ≥ SAME pp, None otherwise."""
    if a is None or b is None:
        return None
    if a['line'] != b['line']:
        return 'line'
    return 'price' if abs(_over(a) - _over(b)) >= SAME else None


def case(event, game: pd.DataFrame, team_of: Dict) -> Optional[Dict]:
    """One event's lines: game holds every offered line of its game (offers() with player_id_ESPN)."""
    reads = sorted(game['at'].unique())
    first = [a for a in reads if a >= event.seen_at]
    earlier = [a for a in reads if a < event.seen_at]
    if not first or not earlier or first[0] - event.seen_at > pd.Timedelta(minutes=10):
        return None                                       # the game wasn't read by that slot, or not before it
    before, after, close = earlier[-1], first[0], reads[-1]
    own = game[game['player_id_ESPN'] == event.player_id_ESPN]
    own_reads = set(own['at'])
    own_state = ('withdrawn before our RotoWire read' if before not in own_reads
                 else 'withdrawn by our first read' if after not in own_reads
                 else 'still offered at our first read')
    mates = game[(game['player_id_ESPN'] != event.player_id_ESPN) & game['bet_type'].isin(STATS)
                 & (game['player_id_ESPN'].map(team_of) == event.team)]
    b, f, c = _at(mates, before), _at(mates, after), _at(mates, close)
    lines = []
    for key, rb in b.items():
        rf, rc = f.get(key), c.get(key)
        early, late = _move(rb, rf), _move(rf, rc) if rf is not None else None
        kind = 'moved by our read' if early else 'moved later' if late else 'never'
        late_pp = abs(_over(rc) - _over(rf)) if rf is not None and rc is not None and \
            rf['line'] == rc['line'] else np.nan
        lines.append({'player': key[0], 'stat': key[1],
                      'before': f"{rb['line']:g} · {_over(rb):.0f}%",
                      'first read': f"{rf['line']:g} · {_over(rf):.0f}%" if rf is not None else 'gone',
                      'close': f"{rc['line']:g} · {_over(rc):.0f}%" if rc is not None else 'gone',
                      'kind': kind, 'late move pp': late_pp})
    # the baseline: the other team's lines of the same game between the same two reads (no news for them)
    others = game[game['bet_type'].isin(STATS) & game['player_id_ESPN'].map(team_of).notna()
                  & (game['player_id_ESPN'].map(team_of) != event.team)]
    ob, of = _at(others, before), _at(others, after)
    pairs = [(r, of.get(k)) for k, r in ob.items() if of.get(k) is not None]
    return {'before': before, 'after': after, 'close': close, 'tip': game['tip'].iloc[0], 'own': own_state,
            'lines': pd.DataFrame(lines),
            'others': (sum(1 for a, b in pairs if _move(a, b)), len(pairs))}


def _pl(ts) -> str:
    return f"{pd.Timestamp(ts).tz_convert('Europe/Warsaw'):%d.%m %H:%M}"


def report(cases: List) -> str:
    out = ["# H4 case look: RotoWire 'out' news and Superbet's lines", "",
           "Descriptive only (docs/hipotezy_wyceny.md, H4). Times are Polish. A line's value is 'line · margin-free "
           "Over chance'. *Moved by our read*: Superbet had moved it by the Superbet read of the slot that saw the "
           "news (at least as fast as our RotoWire check, which is hourly until the last hour). *Moved later*: it "
           "still stood at that read (the window H4 is about). *Never*: unchanged until tip-off.", ""]
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
            t = c['lines'].assign(**{'late move pp': c['lines']['late move pp'].map(
                lambda v: '' if pd.isna(v) else f"{v:.1f}")})
            out += [markdown(t), ""]
        else:
            out += ["No teammate PTS / REB / AST / PRA lines at the read before.", ""]
    return '\n'.join(out) + '\n'


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    from espn_scraper import CURRENT_SEASON, SEASONS
    from espn_scraper.storage import load_player_gamelogs, read_snapshot, snapshot_file
    from name_resolver import NameResolver
    read = lambda name: read_snapshot(snapshot_file(CURRENT_SEASON, name)) \
        if os.path.exists(snapshot_file(CURRENT_SEASON, name)) else pd.DataFrame()
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
    team_of = logs.sort_values('Date').drop_duplicates('player_id_ESPN', keep='last') \
        .set_index('player_id_ESPN')['team'].to_dict()
    teams = props.drop_duplicates('event_id').set_index('event_id')[['home', 'away']]
    offered['night'] = offered['tip'].dt.tz_convert('US/Eastern').dt.tz_localize(None).dt.normalize()
    cases = []
    for event in events.itertuples():
        ids = [e for e in offered.loc[offered['night'] == event.night, 'event_id'].unique()
               if e in teams.index and event.team in (teams.at[e, 'home'], teams.at[e, 'away'])]
        if not ids:
            continue
        c = case(event, offered[offered['event_id'] == ids[0]], team_of)
        if c:
            cases.append((event, c))
    log.info("%d out events, %d with a game read before and after", len(events), len(cases))
    text = report(cases)
    atomic_write_text(REPORT_FILE, text)
    print(text)


if __name__ == '__main__':
    main()
