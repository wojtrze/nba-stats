"""Rebuild a player's box-score line from a game's play-by-play.

ESPN sometimes lists a player in the box score without id, name or stats (seen for two-way contracts, e.g.
Lachlan Olbrich in 2025/26), while the play-by-play still names them and tags their plays with their id.
"""
import re
from collections import Counter
from typing import Dict, List, Optional


def _seconds(clock: str) -> float:
    """'7:41' -> 461; under a minute ESPN shows tenths without minutes ('50.0' -> 50)."""
    if ':' not in clock:
        return float(clock or 0)
    minutes, _, seconds = clock.partition(':')
    return float(minutes or 0) * 60 + float(seconds or 0)


def _elapsed(play: dict) -> int:
    """Seconds since tip-off at this play (12-minute quarters, 5-minute overtimes)."""
    period = play['period']['number']
    length = 720 if period <= 4 else 300
    start = 720 * min(period - 1, 4) + 300 * max(period - 5, 0)
    return start + length - _seconds(play['clock']['displayValue'])


def _period_end(period: int) -> int:
    return 720 * min(period, 4) + 300 * max(period - 4, 0)


def _actor(play: dict) -> Optional[str]:
    participants = play.get('participants') or []
    return participants[0].get('athlete', {}).get('id') if participants else None


def missing_player(plays: List[dict], team_id: str, short_name: str, known_ids) -> Optional[Dict[str, str]]:
    """The id and full name of the team's player whose box-score entry only has `short_name` (e.g. 'Olbrich'):
    a play participant of that team who isn't in the box score and whose name in the play texts ends with it."""
    pattern = re.compile(r"((?:[A-Z][\w'.-]* )+" + re.escape(short_name) + r")\b")
    ids, names = Counter(), Counter()
    for play in plays:
        if play.get('team', {}).get('id') != team_id or short_name not in play.get('text', ''):
            continue
        actor = _actor(play)
        match = pattern.match(play['text'])
        if actor and actor not in known_ids and match:
            ids[actor] += 1
            names[match.group(1)] += 1
    if not ids:
        return None
    return {'id': ids.most_common(1)[0][0], 'displayName': names.most_common(1)[0][0]}


def player_stats(plays: List[dict], player_id: str, name: str, side: str) -> Dict[str, str]:
    """The player's line in ESPN's box-score format (same keys as the summary's player statistics).
    side: 'home' or 'away', for the plus-minus."""
    s = Counter()
    for play in plays:
        text, kind = play.get('text', ''), play.get('type', {}).get('text', '').lower()
        if f"({name} assists)" in text:
            s['assists'] += 1
        if f"({name} steals)" in text:
            s['steals'] += 1
        if text.startswith(f"{name} blocks"):   # "X blocks Y's layup": the play's participant is the shooter
            s['blocks'] += 1
            continue
        if _actor(play) != player_id:
            continue
        if play.get('shootingPlay'):
            made = bool(play.get('scoringPlay'))
            if 'free throw' in kind or 'free throw' in text:
                s['ftm'] += made
                s['fta'] += 1
            else:
                three = play.get('pointsAttempted') == 3 or 'three point' in text
                s['fgm'] += made
                s['fga'] += 1
                s['tpm'] += made and three
                s['tpa'] += three
            s['points'] += play.get('scoreValue', 0) if made else 0
        elif not text.startswith(name):
            continue
        elif text.startswith(f"{name} offensive rebound"):
            s['offensiveRebounds'] += 1
        elif text.startswith(f"{name} defensive rebound"):
            s['defensiveRebounds'] += 1
        elif 'turnover' in kind or kind in ('traveling', 'double dribble', 'discontinued dribble'):
            s['turnovers'] += 1
        elif 'foul' in kind and 'technical' not in kind:
            s['fouls'] += 1

    # time on court: substitutions, and being on court at a period's start if the first thing in that
    # period isn't the player checking in
    on_since, seconds, plus_minus, last_diff = None, 0, 0, 0
    period = 0
    for play in plays:
        p = play['period']['number']
        diff = (play['homeScore'] - play['awayScore']) * (1 if side == 'home' else -1)
        if p != period:
            if on_since is not None:
                seconds += _period_end(period) - on_since
                on_since = None
            period = p
            first = next((q for q in plays if q['period']['number'] == p and name in q.get('text', '')), None)
            if first is not None and not first['text'].startswith(f"{name} enters the game"):
                on_since = _period_end(p - 1)
        if on_since is not None:
            plus_minus += diff - last_diff
        last_diff = diff
        text = play.get('text', '')
        if play.get('type', {}).get('text') == 'Substitution':
            if text.startswith(f"{name} enters the game") and on_since is None:
                on_since = _elapsed(play)
            elif text.endswith(f"for {name}") and on_since is not None:
                seconds += _elapsed(play) - on_since
                on_since = None
    if on_since is not None:
        seconds += _period_end(period) - on_since

    return {'minutes': str(round(seconds / 60)), 'points': str(s['points']),
            'fieldGoalsMade-fieldGoalsAttempted': f"{s['fgm']}-{s['fga']}",
            'threePointFieldGoalsMade-threePointFieldGoalsAttempted': f"{s['tpm']}-{s['tpa']}",
            'freeThrowsMade-freeThrowsAttempted': f"{s['ftm']}-{s['fta']}",
            'rebounds': str(s['offensiveRebounds'] + s['defensiveRebounds']), 'assists': str(s['assists']),
            'turnovers': str(s['turnovers']), 'steals': str(s['steals']), 'blocks': str(s['blocks']),
            'offensiveRebounds': str(s['offensiveRebounds']), 'defensiveRebounds': str(s['defensiveRebounds']),
            'fouls': str(s['fouls']), 'plusMinus': str(plus_minus)}
