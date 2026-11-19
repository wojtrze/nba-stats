"""A regular ruled Out and his teammates' lines (H10 in docs/hipotezy_wyceny.md): one code for the Overview's "Big
chances vs Superbet" window and the backtest (backtest/absence_shift.py).

The rule, as the user's betting expert put it and fixed before any evaluation night (D in backtest/absence_shift):

  1. Out: a regular (news.MIN_MINUTES+ over his last 10 games) with play_pct 0 in RotoWire's latest version of the
     night is taken as not playing, hours before tip-off too. When an earlier version had him Out and the latest
     says 'Ques', he stays on the list, marked (RotoWire flipped Embiid to "Ques, 100%" on 15.11 and he sat).
     since: our first RotoWire read that night with him Out; game without him no.: 1 + the team's games he missed
     right before tonight (1 = the first game without him, when the expert expects Superbet to be off). Only a
     fresh absence counts: game no. up to MAX_GAME_NO (a longer one Superbet has priced for weeks; on 2022/23 such
     lines were few).
  2. Teammates: their Superbet lines in STATS; per out teammate metrics.absence_breakdown gives the shrunk
     with/without change, n without and n with (summed over the team's fresh absences). A line is listed when the summed change is at least MIN_SHARE of
     the player's usual average and at least one out teammate has MIN_WITHOUT games without him.
  3. Side: the change's direction (Over when it grows, Under when it shrinks).

Nothing here is a bet: no threshold of profitability, the stars and decisions don't read it. The window shows,
per line, Superbet's line the last time the out player played, when the line was first offered tonight (after we
saw the news: the line was born knowing it), our chance of the side against the margin-free price and the
after-tax break-even, so the reader can judge.
"""
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from metrics import ACTIVE_PROFILE, POSITION_GROUPS, absence_breakdown, absence_terms, break_even, team_rotation
from mispricing import ROLE_GAMES
from news import _night, _status, over_chance

STATS = ('PTS', 'REB', 'AST', 'ARP', '3PM')
MIN_SHARE = 0.10          # |summed change| / usual average
MIN_WITHOUT = 3           # games without the out teammate behind at least one change
MAX_GAME_NO = 3           # a fresh absence: the first, second or third game without him
SHRINK = 5                # metrics.absence_breakdown's shrink, as price_props uses it
QUES = 'Ques'
TOP_REPLACEMENTS = 2       # who_gains: teammates at his position
TOP_AFFECTED = 3           # who_gains: the biggest with/without changes besides them
GAIN_STATS = ('PTS', 'REB', 'AST')
AFFECTED_MPG = 15          # who_gains: 'affected' are players with a real role
OUT_COLUMNS = ['night', 'team', 'player_id_ESPN', 'name', 'since', 'game_no', 'now_ques']


# --- 1. who is out ---

def missed_in_a_row(logs: pd.DataFrame, pid, team: str, night) -> int:
    """The team's games right before `night` the player didn't play (stops at the last one he played)."""
    team_logs = logs[(logs['team'] == team) & (logs['Date'] < night)]
    played = set(team_logs.loc[(team_logs['player_id_ESPN'] == pid) & (pd.to_numeric(team_logs['MIN'],
                                                                                   errors='coerce') > 0), 'Date'])
    n = 0
    for day in sorted(team_logs['Date'].unique(), reverse=True):
        if day in played:
            break
        n += 1
    return n


def out_tonight(saved: List, logs: pd.DataFrame, night, regulars: set) -> pd.DataFrame:
    """The regulars ruled out tonight. saved: the night's RotoWire versions (news.lineup_versions' list of (saved
    at, rows)), oldest first; regulars: news.regulars_by_night's set for the night. Columns OUT_COLUMNS: since (our
    first read with him Out), game_no (1 = first game without him), now_ques (Out earlier, 'Ques' in the latest)."""
    if not saved:
        return pd.DataFrame(columns=OUT_COLUMNS)
    latest = _status(saved[-1][1])
    rows = []
    seen_out: Dict = {}
    for at, version in saved:
        s = _status(version)
        for pid in s.index[s['play_pct'] == 0]:
            seen_out.setdefault(int(pid), (at, s.at[pid, 'team'], s.at[pid, 'name']))
    for pid, (since, team, name) in seen_out.items():
        if pid not in regulars:
            continue
        if pid in latest.index and latest.at[pid, 'play_pct'] == 0:
            now_ques = False
        elif pid in latest.index and str(latest.at[pid, 'injury']).startswith(QUES):
            now_ques = True
        else:
            continue
        rows.append({'night': night, 'team': team, 'player_id_ESPN': pid, 'name': name, 'since': since,
                     'game_no': 1 + missed_in_a_row(logs, pid, team, night), 'now_ques': now_ques})
    return pd.DataFrame(rows, columns=OUT_COLUMNS)


# --- 2. and 3. the teammates' lines ---

def fresh(out: pd.DataFrame) -> pd.DataFrame:
    """The out players of rule 1 that count: game no. up to MAX_GAME_NO."""
    return out[out['game_no'] <= MAX_GAME_NO]


def changes(logs: pd.DataFrame, pid, out_ids, stat: str) -> Dict:
    """The summed with/without change of `stat` over out_ids and its parts: {'change', 'usual', 'parts': [{'id',
    'n_without', 'n_with', 'change'}]}; usual = his average in logs."""
    part = logs[logs['player_id_ESPN'].isin(set(out_ids) | {pid})]
    parts = absence_breakdown(part, pid, list(out_ids), stat, SHRINK) if stat in part else []
    estimated = [p for p in parts if p['estimated']]
    own = part.loc[part['player_id_ESPN'] == pid, stat] if stat in part else pd.Series(dtype=float)
    return {'change': float(sum(p['change'] for p in estimated)) if estimated else np.nan,
            'usual': float(own.mean()) if len(own) else np.nan, 'parts': parts}


def listed(c: Dict) -> bool:
    """The rule's step 2: a big enough change behind enough games without."""
    if pd.isna(c['change']) or pd.isna(c['usual']) or c['usual'] <= 0:
        return False
    return abs(c['change']) >= MIN_SHARE * c['usual'] and \
        any(p['estimated'] and p['n_without'] >= MIN_WITHOUT for p in c['parts'])


def side_of(change: float) -> str:
    return 'Over' if change > 0 else 'Under'


def price_of(row, side: str) -> float:
    """The side's margin-free chance, %."""
    over = over_chance(row)
    return over if side == 'Over' else 100 - over


def previous_line(history: pd.DataFrame, logs: pd.DataFrame, pid, stat: str, out_ids, night) -> Optional[float]:
    """Superbet's line of the player and stat on the latest earlier night every out teammate played (the last
    saved fetch before that tip-off); None when there's no such night. history: saved superbet_props snapshots."""
    if history is None or history.empty:
        return None
    h = history[(pd.to_numeric(history['player_id_ESPN'], errors='coerce') == pid) & (history['bet_type'] == stat)]
    if h.empty:
        return None
    tip = pd.to_datetime(h['start_time'], utc=True)
    h = h.assign(at=pd.to_datetime(h['fetched_at'], utc=True), night=_night(tip))
    h = h[(h['at'] < tip) & (h['night'] < night)].dropna(subset=['line'])
    played = logs[logs['player_id_ESPN'].isin(out_ids) & (pd.to_numeric(logs['MIN'], errors='coerce') > 0)]
    with_all = [n for n, g in played.groupby('Date') if set(g['player_id_ESPN']) >= set(out_ids)]
    h = h[h['night'].isin(with_all)]
    return float(h.sort_values('at')['line'].iloc[-1]) if len(h) else None


def situations(priced: pd.DataFrame, logs: pd.DataFrame, out: pd.DataFrame, history: pd.DataFrame = None,
               first_seen: Optional[Dict] = None, profile: str = ACTIVE_PROFILE) -> pd.DataFrame:
    """The listed teammate lines of tonight's out players (rules 2 and 3), most promising first: first game without
    someone, then |change| / usual. priced: models.price_props' table (player_id, team, event_id, name_ESPN,
    bet_type, line, odds, side, p win %, p push %); logs: games before tonight with the stats (prepare_logs);
    first_seen: {(event_id, name_ESPN, bet_type): first time offered tonight}.

    Columns: team, event_id, name, name_ESPN, player_id, bet_type, line, side, odds, usual, change, without
    (usual + change), share % (change / usual), n without (per out teammate, as text), out (their names), game_no
    (the lowest of theirs), since (the earliest), previous line, shift (tonight's line − previous), new line (first
    offered after since), p side % (ours, absence included), price % (margin-free), gap pp, break-even net %."""
    out = fresh(out)
    if out.empty or priced.empty:
        return pd.DataFrame()
    rows = []
    names = dict(zip(out['player_id_ESPN'], out['name']))
    for team, outs in out.groupby('team'):
        out_ids = [int(p) for p in outs['player_id_ESPN']]
        since = outs['since'].min()
        lines = priced[(priced['team'] == team) & priced['bet_type'].isin(STATS) & priced['player_id'].notna()
                       & ~priced['player_id'].isin(out_ids)]
        for _, r in lines.iterrows():
            c = changes(logs, r['player_id'], out_ids, r['bet_type'])
            if not listed(c):
                continue
            side = side_of(c['change'])
            odds = r['over_odds'] if side == 'Over' else r['under_odds']
            p_win = r['p win %'] if r.get('side') == side else 100 - r['p win %'] - r.get('p push %', 0)
            prev = previous_line(history, logs, r['player_id'], r['bet_type'], out_ids, outs['night'].iloc[0])
            seen = (first_seen or {}).get((r['event_id'], r['name_ESPN'], r['bet_type']))
            rows.append({'team': team, 'event_id': r['event_id'], 'name': r['name'], 'name_ESPN': r['name_ESPN'],
                         'player_id': r['player_id'], 'bet_type': r['bet_type'], 'line': r['line'], 'side': side,
                         'odds': odds, 'usual': c['usual'], 'change': c['change'],
                         'without': c['usual'] + c['change'], 'share %': 100 * c['change'] / c['usual'],
                         'n without': ', '.join(f"{names.get(p['id'], p['id'])}: {p['n_without']}"
                                                for p in c['parts']),
                         'out': ', '.join(names[o] for o in out_ids), 'game_no': int(outs['game_no'].min()),
                         'since': since, 'previous line': prev,
                         'shift': r['line'] - prev if prev is not None else np.nan,
                         'new line': bool(seen is not None and seen > since),
                         'p side %': p_win, 'price %': price_of(r, side),
                         'gap pp': p_win - price_of(r, side),
                         'break-even net %': 100 * float(break_even(odds, profile))})
    if not rows:
        return pd.DataFrame()
    table = pd.DataFrame(rows)
    order = table.assign(_first=table['game_no'] > 1, _size=-table['share %'].abs())
    return table.loc[order.sort_values(['_first', '_size'], kind='stable').index].reset_index(drop=True)


# --- who gains: the names in the window's sentence about each absence (a description, not the rule) ---

def _group(position) -> Optional[str]:
    return POSITION_GROUPS.get(str(position)) if pd.notna(position) else None


def who_gains(o, latest: pd.DataFrame, logs: pd.DataFrame, lines: Optional[pd.DataFrame] = None,
              out_ids=()) -> Dict:
    """The teammates an absence matters most for, by his own with/without (not summed with other absences).
    o: an out_tonight row; latest: RotoWire's latest version that night; logs: games before the night; lines:
    tonight's priced lines (player_id, bet_type, line); out_ids: everyone out tonight (never named).

    Candidates: the team's rotation (metrics.team_rotation) with MIN_WITHOUT+ games without him
    (metrics.absence_terms over MIN and GAIN_STATS). Returns {'position': his G / F / C, 'replacements': up to
    TOP_REPLACEMENTS at his position, promoted to RotoWire's starting five first (a starter tonight with at most one
    start in his last ROLE_GAMES games, H5's promotion), then by minutes gained, only with a promotion or more
    minutes; 'affected': up to TOP_AFFECTED others playing AFFECTED_MPG+ minutes, by the biggest change among
    GAIN_STATS in his own spreads (|change| / sd), when that change is MIN_SHARE+ of his usual;
    'too_few': no teammate has MIN_WITHOUT games without him}. Each entry: name, player_id, promoted, min_change,
    stat, change, share %, n_without, line (Superbet's tonight in that stat, None without one), mpg, spreads."""
    pid, team = int(o['player_id_ESPN']), o['team']
    own = logs[logs['player_id_ESPN'] == pid]
    position = _group(own['position'].iloc[-1]) if len(own) and 'position' in own else None
    status = _status(latest) if latest is not None and len(latest) else pd.DataFrame()
    rotation = team_rotation(logs, team)
    skip = set(int(x) for x in out_ids) | {pid}
    rows = []
    for mate, r in rotation.iterrows():
        if int(mate) in skip:
            continue
        term = absence_terms(logs, mate, pid, ['MIN', *GAIN_STATS])
        if not term['estimated'] or term['n_without'] < MIN_WITHOUT:
            continue
        games = logs[logs['player_id_ESPN'] == mate]
        starts = int(games.sort_values('Date')['starter'].tail(ROLE_GAMES).astype(bool).sum())
        starter = mate in status.index and status.at[mate, 'role'] == 'starter' if len(status) else False
        group = _group(status.at[mate, 'pos']) if starter and 'pos' in status else _group(r['position'])
        usual = games[list(GAIN_STATS)].mean()
        # the stat that changes most in his own spreads (a bench player's +0.8 assists isn't +163% of anything real)
        spread = games[list(GAIN_STATS)].std()
        size = (term['change'][list(GAIN_STATS)] / spread.where(spread > 0)).abs()
        stat = size.idxmax() if size.notna().any() else None
        line = None
        if stat and lines is not None and len(lines):
            hit = lines[(lines['player_id'] == mate) & (lines['bet_type'] == stat)]
            line = float(hit['line'].iloc[0]) if len(hit) else None
        rows.append({'name': r['name'], 'player_id': int(mate), 'group': group,
                     'promoted': bool(starter and starts <= 1), 'min_change': float(term['change']['MIN']),
                     'stat': stat, 'change': float(term['change'][stat]) if stat else np.nan,
                     'share %': float(100 * term['change'][stat] / usual[stat]) if stat else np.nan,
                     'n_without': term['n_without'], 'line': line, 'mpg': float(r['mpg']),
                     'spreads': float(size[stat]) if stat else np.nan})
    places = [r for r in rows if position and r['group'] == position and (r['promoted'] or r['min_change'] > 0)]
    places = sorted(places, key=lambda r: (not r['promoted'], -r['min_change']))[:TOP_REPLACEMENTS]
    named = {r['player_id'] for r in places}
    others = [r for r in rows if r['player_id'] not in named and r['mpg'] >= AFFECTED_MPG
              and pd.notna(r['share %']) and abs(r['share %']) >= 100 * MIN_SHARE]
    others = sorted(others, key=lambda r: -r['spreads'])[:TOP_AFFECTED]
    return {'position': position, 'replacements': places, 'affected': others, 'too_few': not rows}


# --- the backtest's signals ---

def signal_rows(night, out: pd.DataFrame, offered: pd.DataFrame, logs: pd.DataFrame,
                team_of: Dict) -> pd.DataFrame:
    """H10's sides on one night in backtest/mispricing_eval's outputs format: for every team with out players, each
    teammate line in STATS at its first read at or after the team's earliest `since` (Out known), listed by
    the rule, on the side of its change (clears = True: the rule has no profitability threshold). offered:
    news.offers rows with player_id_ESPN; logs: games before the night."""
    frames = []
    for team, outs in fresh(out).groupby('team'):
        out_ids = [int(p) for p in outs['player_id_ESPN']]
        since = outs['since'].min()
        team_lines = offered[offered['player_id_ESPN'].map(team_of) == team]
        team_lines = team_lines[team_lines['bet_type'].isin(STATS) & ~team_lines['player_id_ESPN'].isin(out_ids)]
        if team_lines.empty:
            continue
        # each line at its first read once Out was known (a line first offered later, like Walker's on 15.11, too)
        at = team_lines[team_lines['at'] >= since].sort_values('at').drop_duplicates(['event_id', 'name_ESPN',
                                                                                     'bet_type'])
        rows = []
        for _, r in at.iterrows():
            c = changes(logs, int(r['player_id_ESPN']), out_ids, r['bet_type'])
            if not listed(c):
                continue
            side = side_of(c['change'])
            rows.append({'night': night, 'at': r['at'], 'event_id': r['event_id'], 'name_ESPN': r['name_ESPN'],
                         'player_id_ESPN': r['player_id_ESPN'], 'hypothesis': 'H10', 'bet_type': r['bet_type'],
                         'line': r['line'], 'side': side,
                         'odds': r['over_odds'] if side == 'Over' else r['under_odds'],
                         'over_odds': r['over_odds'], 'under_odds': r['under_odds'], 'clears': True,
                         'change': c['change'], 'share %': 100 * c['change'] / c['usual'],
                         'game_no': int(outs['game_no'].min()), 'price %': price_of(r, side)})
        if rows:
            frames.append(pd.DataFrame(rows))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
