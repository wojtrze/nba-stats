"""RotoWire news and Superbet's lines (H4 in docs/hipotezy_wyceny.md): one code for the Overview's news window and
the backtests (backtest/news_lag.py, backtest/news_lag_cases.py, backtest/mispricing_eval.py).

An event: between two consecutive RotoWire versions of a night (saved at most MAX_VERSION_GAP apart, so an outage
doesn't look like news) a regular (at least MIN_MINUTES over his last 10 games) changed status:

  - 'out': from playing (listed with play_pct > 0, or not listed while his team was) to Out (play_pct 0);
  - 'return': from Out to playing.

A scheduled slot reads RotoWire and then Superbet under one time stamp, so the version's slot is also our first
Superbet read after the news. Our RotoWire read is hourly (more often in the last hour): the time we saw the news is
the time of our read, not the time it was posted.

For each event, reactions() follows every teammate's PTS / REB / AST / PRA line from the read before the news, over
our first read after it, to the close (the last read before tip-off; the latest read so far for tonight):
'moved by our read' (Superbet was at least as fast as our RotoWire check), 'withdrawn by our read', 'moved later'
(it still stood at our read: the window H4 is about) or 'never'. A move is a new line, or the margin-free chance at the same line changing
by at least SAME pp.

H4's side is fixed in advance (2026-11-19, before any evaluation night): the news makes a teammate's Over more likely
when a regular is out and his Under when one returns. signal_rows() turns each teammate line that still stood at our
first read into that side at that read, in backtest/mispricing_eval's outputs format.
"""
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from tracking import PROP_KEY

MIN_MINUTES = 20
MAX_VERSION_GAP = pd.Timedelta(hours=2)
FIRST_READ_WITHIN = pd.Timedelta(minutes=10)
STATS = ('PTS', 'REB', 'AST', 'PRA')
NEEDED_PP = 11            # the registry's after-tax gap (docs/hipotezy_wyceny.md)
SAME = 0.5                # pp: a smaller change of the margin-free chance at the same line isn't a move
SIDE = {'out': 'Over', 'return': 'Under'}
MOVED_EARLY, MOVED_LATER, NEVER = 'moved by our read', 'moved later', 'never'
WITHDRAWN = 'withdrawn by our read'
LINE = ['bet_type', 'line', 'over_odds', 'under_odds']
EVENT_COLUMNS = ['night', 'seen_at', 'prev_at', 'team', 'player_id_ESPN', 'name', 'kind']


# --- the offers at every read and RotoWire's versions ---

def _utc(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, utc=True)


def _night(tip: pd.Series) -> pd.Series:
    return tip.dt.tz_convert('US/Eastern').dt.tz_localize(None).dt.normalize()


def offers(props: pd.DataFrame, quotes: pd.DataFrame, fetches: pd.DataFrame) -> pd.DataFrame:
    """Every line as offered at every read before tip-off: at (the read), event_id, tip, name_ESPN, bet_type,
    line, over_odds, under_odds, source ('schedule' or 'snapshot'). A game read by the schedule
    (superbet_event_fetches) is rebuilt from superbet_prop_quotes, which hold only changes: at every read, each line
    is its last quote so far. Older games come from the dashboard's superbet_props snapshots. A line withdrawn
    (empty odds) or not yet listed at a read isn't in it."""
    frames = []
    scheduled = set()
    if len(fetches) and len(quotes):
        reads = fetches.assign(at=_utc(fetches['fetched_at']), tip=_utc(fetches['start_time']))
        reads = reads[reads['at'] < reads['tip']].drop_duplicates(['event_id', 'at'])[['event_id', 'at', 'tip']]
        q = quotes.assign(at=_utc(quotes['fetched_at'])).drop(columns='fetched_at').sort_values('at')
        keys = q[PROP_KEY].drop_duplicates()
        grid = reads.merge(keys, on='event_id').sort_values('at')
        rebuilt = pd.merge_asof(grid, q, on='at', by=PROP_KEY, direction='backward')
        frames.append(rebuilt.assign(source='schedule'))
        scheduled = set(reads['event_id'])
    if len(props):
        s = props.assign(at=_utc(props['fetched_at']), tip=_utc(props['start_time']))
        s = s[(s['at'] < s['tip']) & ~s['event_id'].isin(scheduled)]
        frames.append(s[['at', 'event_id', 'tip'] + PROP_KEY[1:] + LINE[1:]].assign(source='snapshot'))
    if not frames:
        return pd.DataFrame(columns=['at', 'event_id', 'tip', *PROP_KEY[1:], *LINE[1:], 'source'])
    out = pd.concat(frames, ignore_index=True)
    out = out.dropna(subset=['line', 'over_odds', 'under_odds'])
    return out.drop_duplicates(['at'] + PROP_KEY, keep='last').sort_values(['at'] + PROP_KEY, ignore_index=True)


def player_ids(offered: pd.DataFrame, props: pd.DataFrame, logs: pd.DataFrame) -> pd.Series:
    """Each offered line's player_id_ESPN: the snapshot's for the same game and name, else the gamelogs' when the
    name belongs to one player only."""
    known = props.dropna(subset=['player_id_ESPN']).drop_duplicates(['event_id', 'name_ESPN'], keep='last')
    pid = offered[['event_id', 'name_ESPN']].merge(
        known[['event_id', 'name_ESPN', 'player_id_ESPN']], on=['event_id', 'name_ESPN'], how='left')['player_id_ESPN']
    named = logs.drop_duplicates(['player_name_ESPN', 'player_id_ESPN'])
    unique = named.groupby('player_name_ESPN')['player_id_ESPN'].transform('size') == 1
    by_name = named[unique].set_index('player_name_ESPN')['player_id_ESPN']
    pid.index = offered.index
    return pid.fillna(offered['name_ESPN'].map(by_name)).astype('Int64')


def lineup_versions(lineups: pd.DataFrame) -> Dict:
    """RotoWire's saved versions (rotowire_lineups with player_id_ESPN) per night (game_date): a list of (saved at,
    that version's rows), oldest first."""
    if lineups is None or lineups.empty:
        return {}
    rw = lineups.assign(at=_utc(lineups['fetched_at']), night=pd.to_datetime(lineups['game_date']),
                        player_id_ESPN=pd.to_numeric(lineups['player_id_ESPN'], errors='coerce'))
    return {night: [(at, v) for at, v in day.groupby('at')] for night, day in rw.groupby('night')}


# --- the events ---

def _status(version: pd.DataFrame) -> pd.DataFrame:
    """One row per player of a version: team, play_pct (numeric)."""
    v = version.dropna(subset=['player_id_ESPN']).drop_duplicates('player_id_ESPN', keep='last')
    return v.assign(play_pct=pd.to_numeric(v['play_pct'], errors='coerce')).set_index('player_id_ESPN')


def _playing(status: pd.DataFrame, pid, team) -> bool:
    """Listed with a chance to play, or not listed while his team is (RotoWire lists only the doubtful)."""
    if pid in status.index:
        return bool(status.at[pid, 'play_pct'] > 0)
    return team in set(status['team'])


def find_events(versions: Dict, regulars: Dict) -> pd.DataFrame:
    """Status news between consecutive RotoWire versions: night, seen_at (the version's save time), prev_at, team,
    player_id_ESPN, name, kind ('out' or 'return'). regulars: {night: set of player ids averaging MIN_MINUTES
    before that night}."""
    rows = []
    for night, saved in versions.items():
        for (prev_at, prev), (seen_at, cur) in zip(saved, saved[1:]):
            if seen_at - prev_at > MAX_VERSION_GAP:
                continue
            p, c = _status(prev), _status(cur)
            regular = regulars.get(night, set())
            for pid, row in c[c['play_pct'] == 0].iterrows():
                if pid in regular and _playing(p, pid, row['team']):
                    rows.append({'night': night, 'seen_at': seen_at, 'prev_at': prev_at, 'team': row['team'],
                                 'player_id_ESPN': int(pid), 'name': row['name'], 'kind': 'out'})
            # back: Out in the previous version, playing in this one (still listed > 0, or gone from the list)
            for pid, row in p[p['play_pct'] == 0].iterrows():
                if pid in regular and _playing(c, pid, row['team']):
                    rows.append({'night': night, 'seen_at': seen_at, 'prev_at': prev_at, 'team': row['team'],
                                 'player_id_ESPN': int(pid), 'name': row['name'], 'kind': 'return'})
    return pd.DataFrame(rows, columns=EVENT_COLUMNS)


def regulars_by_night(logs: pd.DataFrame, nights) -> Dict:
    """{night: player ids whose last 10 games before that night average at least MIN_MINUTES}."""
    logs = logs.assign(MIN=pd.to_numeric(logs['MIN'], errors='coerce')).sort_values('Date')
    out = {}
    for night in nights:
        before = logs[logs['Date'] < night]
        avg = before.groupby('player_id_ESPN')['MIN'].apply(lambda m: m.tail(10).mean())
        out[night] = set(avg[avg >= MIN_MINUTES].index.astype(int))
    return out


# --- the lines' reactions ---

def over_chance(row) -> float:
    """The margin-free Over chance of a quote, %."""
    if row is None or pd.isna(row['over_odds']) or pd.isna(row['under_odds']):
        return np.nan
    o, u = 1 / row['over_odds'], 1 / row['under_odds']
    return 100 * o / (o + u)


def _at(lines: pd.DataFrame, at) -> Dict:
    """{(name_ESPN, bet_type): row} of the lines offered at one read."""
    return {(r['name_ESPN'], r['bet_type']): r for _, r in lines[lines['at'] == at].iterrows()}


def moved(a, b) -> Optional[str]:
    """'line' when the line changed, 'price' when the chance at the same line moved ≥ SAME pp, None otherwise."""
    if a is None or b is None:
        return None
    if a['line'] != b['line']:
        return 'line'
    return 'price' if abs(over_chance(a) - over_chance(b)) >= SAME else None


def _quote(row) -> str:
    return f"{row['line']:g} · {over_chance(row):.0f}%" if row is not None else 'gone'


def reactions(event, game: pd.DataFrame, team_of: Dict) -> Optional[Dict]:
    """One event's lines. game: every offered line of its game (offers() with player_id_ESPN). None when the game
    wasn't read at the news's slot (within FIRST_READ_WITHIN of it) or not before it.

    Returns before / after / close (the reads), tip, own (his own lines: withdrawn before our RotoWire read,
    withdrawn by our first read, or still offered), others ((moved, compared): the other team's lines between the
    same two reads, the baseline without news) and lines: one row per teammate line offered at the read before,
    with player, stat, before / first read / close (as 'line · Over chance'), kind, late move pp (how far the chance
    moved after our read at the same line), and for the signal: event_id, name_ESPN, player_id_ESPN, bet_type,
    line, over_odds, under_odds (at our first read), minutes to move (from our read of the news to the first read
    where the line had moved, NaN if it never did)."""
    reads = sorted(game['at'].unique())
    first = [a for a in reads if a >= event.seen_at]
    earlier = [a for a in reads if a < event.seen_at]
    if not first or not earlier or first[0] - event.seen_at > FIRST_READ_WITHIN:
        return None
    before, after, close = earlier[-1], first[0], reads[-1]
    own_reads = set(game.loc[game['player_id_ESPN'] == event.player_id_ESPN, 'at'])
    own = ('withdrawn before our RotoWire read' if before not in own_reads
           else 'withdrawn by our first read' if after not in own_reads
           else 'still offered at our first read')
    team = game['player_id_ESPN'].map(team_of)
    mates = game[(game['player_id_ESPN'] != event.player_id_ESPN) & game['bet_type'].isin(STATS)
                 & (team == event.team)]
    later = [a for a in reads if a > after]
    by_read = {a: _at(mates, a) for a in [before, after] + later}
    rows = []
    for key, rb in by_read[before].items():
        rf, rc = by_read[after].get(key), by_read[close].get(key)
        early = rf is None or moved(rb, rf)
        when = after if early else next((a for a in later if moved(rf, by_read[a].get(key))
                                         or by_read[a].get(key) is None), None)
        kind = (WITHDRAWN if rf is None else MOVED_EARLY if early else MOVED_LATER if when is not None
                else NEVER)
        late_pp = abs(over_chance(rc) - over_chance(rf)) if rf is not None and rc is not None and \
            rf['line'] == rc['line'] else np.nan
        rows.append({'player': key[0], 'stat': key[1], 'before': _quote(rb), 'first read': _quote(rf),
                     'close': _quote(rc), 'kind': kind, 'late move pp': late_pp,
                     'event_id': rb['event_id'], 'name_ESPN': key[0], 'player_id_ESPN': rb['player_id_ESPN'],
                     'bet_type': key[1], 'line': rf['line'] if rf is not None else np.nan,
                     'over_odds': rf['over_odds'] if rf is not None else np.nan,
                     'under_odds': rf['under_odds'] if rf is not None else np.nan,
                     'minutes to move': (when - event.seen_at).total_seconds() / 60 if when is not None else np.nan})
    others = game[game['bet_type'].isin(STATS) & team.notna() & (team != event.team)]
    ob, of = _at(others, before), _at(others, after)
    pairs = [(r, of.get(k)) for k, r in ob.items() if of.get(k) is not None]
    return {'before': before, 'after': after, 'close': close, 'tip': game['tip'].iloc[0], 'own': own,
            'lines': pd.DataFrame(rows), 'others': (sum(1 for a, b in pairs if moved(a, b)), len(pairs))}


def game_of(event, offered: pd.DataFrame, teams: pd.DataFrame) -> Optional[str]:
    """The event_id of the event's team that night among the offered games (teams: home / away by event_id)."""
    tonight = offered.loc[_night(offered['tip']) == event.night, 'event_id'].unique()
    ids = [e for e in tonight if e in teams.index and event.team in (teams.at[e, 'home'], teams.at[e, 'away'])]
    return ids[0] if ids else None


def cases(events: pd.DataFrame, offered: pd.DataFrame, teams: pd.DataFrame,
          team_of: Dict) -> List[Tuple[object, Dict]]:
    """(event, reactions) of every event whose game was read before and at the news's slot."""
    out = []
    for event in events.itertuples():
        event_id = game_of(event, offered, teams)
        if event_id is None:
            continue
        c = reactions(event, offered[offered['event_id'] == event_id], team_of)
        if c:
            out.append((event, c))
    return out


def signal_rows(event, case: Dict) -> pd.DataFrame:
    """H4's sides (SIDE of the event's kind) on the teammate lines that still stood at our first read, at that
    read, in backtest/mispricing_eval's outputs format (clears = True: stage 1 takes every such line)."""
    lines = case['lines']
    if lines.empty:
        return pd.DataFrame()
    still = lines[lines['kind'].isin([MOVED_LATER, NEVER])]
    side = SIDE[event.kind]
    odds = still['over_odds'] if side == 'Over' else still['under_odds']
    return pd.DataFrame({'night': event.night, 'at': case['after'], 'event_id': still['event_id'],
                         'name_ESPN': still['name_ESPN'], 'player_id_ESPN': still['player_id_ESPN'],
                         'hypothesis': 'H4', 'bet_type': still['bet_type'], 'line': still['line'], 'side': side,
                         'odds': odds, 'over_odds': still['over_odds'], 'under_odds': still['under_odds'],
                         'clears': True, 'kind': event.kind, 'news': event.name}).reset_index(drop=True)
