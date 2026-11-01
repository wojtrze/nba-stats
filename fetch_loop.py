"""The scheduled fetches: Superbet's quotes and RotoWire's lineups on fetch_schedule's slots, only while a program
runs them (the v2 dashboard's background worker, or this module in a terminal). Nothing is registered with the
system: closing the program stops the fetching.

    python -m fetch_loop                                   # run until Ctrl+C
    python -m fetch_loop --dry-run                         # print tonight's slots, contact nothing
    python -m fetch_loop --dry-run --now "2026-11-02 18:00"

Each slot records the quotes of the games it read (save_quotes: only what changed since the game's last quote,
plus one superbet_event_fetches row per game read, so "unchanged" is told apart from "not read"). Priced slots
also save a full snapshot with the model (daily_snapshot.save_superbet), which the dashboards read. Every run
is logged to data/run_log.csv.
"""
import argparse
import json
import logging
import os
import socket
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, List, Optional

import pandas as pd

import fetch_schedule
from espn_scraper import CURRENT_SEASON
from espn_scraper.storage import snapshot_file
from safe_io import append_csv, atomic_write_text, locked

log = logging.getLogger(__name__)

SCHEDULED_GAP = timedelta(minutes=3)       # the scheduled fetches' own cooldown (T-10 and T-5 are 5 min apart)
WORKER_FILE = os.path.join('data', 'fetch_worker.json')
SETTINGS_FILE = os.path.join('data', 'fetch_worker_settings.json')
HEARTBEAT_STALE = timedelta(minutes=3)
IDLE_RELIST = timedelta(hours=1)           # with no slot ahead, list the games again this often

PROP_QUOTE_KEY = ['event_id', 'name_ESPN', 'bet_type']
PROP_QUOTE_COLUMNS = ['fetched_at', *PROP_QUOTE_KEY, 'line', 'over_odds', 'under_odds']
GAME_QUOTE_KEY = ['event_id', 'market', 'side', 'line']
GAME_QUOTE_COLUMNS = ['fetched_at', *GAME_QUOTE_KEY, 'odds']
EVENT_FETCH_COLUMNS = ['fetched_at', 'event_id', 'start_time', 'n_props', 'n_game_odds', 'run_kind']


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _stamp(at: datetime) -> str:
    return at.strftime('%Y-%m-%dT%H:%M:%SZ')


# --- quotes: only what changed ---

def _last_quotes(path: str, key: List[str], events) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()
    saved = pd.read_csv(path)
    saved = saved[saved['event_id'].isin(events)]
    return saved.sort_values('fetched_at', kind='stable').drop_duplicates(key, keep='last')


def _changes(new: pd.DataFrame, last: pd.DataFrame, key: List[str], values: List[str]) -> pd.DataFrame:
    """Rows of `new` that differ from the last saved quote of their key, plus a withdrawal (empty values) for each
    key last seen with a price that is no longer offered."""
    if last.empty:
        return new
    # one dtype per key on both sides (a moneyline's line is None when fetched, NaN when read back)
    numeric = [k for k in key if k in ('event_id', 'line')]
    new = new.assign(**{k: pd.to_numeric(new[k], errors='coerce') for k in numeric})
    last = last.assign(**{k: pd.to_numeric(last[k], errors='coerce') for k in numeric})
    merged = new.merge(last[key + values], on=key, how='left', suffixes=('', '_last'), indicator=True)
    differs = merged['_merge'] == 'left_only'
    for v in values:
        a, b = pd.to_numeric(merged[v], errors='coerce'), pd.to_numeric(merged[f'{v}_last'], errors='coerce')
        differs |= ~((a == b) | (a.isna() & b.isna()))
    changed = new[differs.values]
    priced = last[last[values].notna().any(axis=1)]
    gone = priced.merge(new[key], on=key, how='left', indicator=True)
    gone = gone[gone['_merge'] == 'left_only'][key].assign(**{v: None for v in values})
    return pd.concat([changed, gone], ignore_index=True)


def save_quotes(offers: Dict, fetched_at: str, run_kind: str) -> Dict[str, int]:
    """Record one fetch's quotes (superbet_fetcher.todays_offers output) for the games it read: prop and game
    quotes that changed, and one row per game read. Returns the rows written per file."""
    from daily_snapshot import merge_over_under
    read = set(offers.get('fetched') or [])
    if not read:
        return {'prop_quotes': 0, 'game_quotes': 0, 'event_fetches': 0}
    props = merge_over_under(pd.DataFrame(offers['props']))
    props = props.reindex(columns=PROP_QUOTE_COLUMNS[1:]) if len(props) else pd.DataFrame(columns=PROP_QUOTE_COLUMNS[1:])
    games = pd.DataFrame(offers['game_odds']).reindex(columns=GAME_QUOTE_COLUMNS[1:])
    counts = {}
    for name, new, key, columns in (('superbet_prop_quotes', props, PROP_QUOTE_KEY, PROP_QUOTE_COLUMNS),
                                    ('superbet_game_quotes', games, GAME_QUOTE_KEY, GAME_QUOTE_COLUMNS)):
        path = snapshot_file(CURRENT_SEASON, name)
        values = [c for c in columns[1:] if c not in key]
        with locked(path):
            rows = _changes(new, _last_quotes(path, key, read), key, values)
            rows.insert(0, 'fetched_at', fetched_at)
            counts[name.replace('superbet_', '')] = append_csv(rows[columns], path, columns) if len(rows) else 0
    starts = {e['event_id']: e['start_time'] for e in offers.get('events') or []}
    per_event = pd.DataFrame([{'fetched_at': fetched_at, 'event_id': e, 'start_time': starts.get(e),
                               'n_props': int((props['event_id'] == e).sum()),
                               'n_game_odds': int((games['event_id'] == e).sum()), 'run_kind': run_kind}
                              for e in sorted(read)], columns=EVENT_FETCH_COLUMNS)
    counts['event_fetches'] = append_csv(per_event, snapshot_file(CURRENT_SEASON, 'superbet_event_fetches'),
                                         EVENT_FETCH_COLUMNS)
    return counts


# --- one slot ---

def _saved_lineups() -> pd.DataFrame:
    """The latest saved RotoWire version (when a live fetch failed), without fetched_at."""
    path = snapshot_file(CURRENT_SEASON, 'rotowire_lineups')
    if not os.path.exists(path):
        return pd.DataFrame()
    saved = pd.read_csv(path)
    return saved[saved['fetched_at'] == saved['fetched_at'].max()].drop(columns='fetched_at')


def run_slot(slot: fetch_schedule.Slot, now: Callable[[], datetime] = _utc_now) -> Dict:
    """Fetch and save one slot. Returns a status dict (ok, summary, events: the listed games)."""
    import superbet_fetcher
    from daily_snapshot import claim_superbet, log_run, save_lineups_if_changed, save_superbet
    from http_polite import DAILY_REQUEST_BUDGET, Blocked, requests_today

    started, t0 = now(), time.monotonic()
    fetched_at = _stamp(started)
    job = 'snapshot' if slot.priced else 'quotes'
    command = f"scheduled {slot.kind}"
    parts, code, events = [], 0, None

    def done(ok: bool, summary: str) -> Dict:
        log_run(started, job, command, 0 if ok else 1, time.monotonic() - t0, summary[:300])
        return {'ok': ok, 'summary': summary, 'events': events, 'at': started}

    if requests_today(superbet_fetcher.HOST, started) >= DAILY_REQUEST_BUDGET:
        return done(False, f"skipped: today's budget of {DAILY_REQUEST_BUDGET} Superbet requests is used up")
    wait = claim_superbet(SCHEDULED_GAP)
    if wait:
        return done(False, f"skipped: Superbet can't be contacted for {wait.total_seconds() / 60:.0f} more min")

    lineups = pd.DataFrame()
    if slot.rotowire:
        try:
            from lineup_fetcher import fetch_lineups
            lineups = pd.DataFrame(fetch_lineups())
            saved = save_lineups_if_changed(lineups, fetched_at)
            parts.append(f"RotoWire: {saved or 'unchanged'}")
        except Exception as e:
            log.warning("RotoWire failed: %s", e)
            parts.append(f"RotoWire failed: {e}")
            lineups = _saved_lineups()
    http = superbet_fetcher.client()
    try:
        wanted = None if slot.all_events or slot.priced else slot.event_ids
        offers = superbet_fetcher.todays_offers(event_ids=wanted, http=http)
    except Blocked as e:
        return done(False, f"Superbet: {e}; " + '; '.join(parts))
    except Exception as e:
        return done(False, f"Superbet failed: {e} ({http.summary()}); " + '; '.join(parts))
    events = offers['events']
    counts = save_quotes(offers, fetched_at, slot.kind)
    parts.insert(0, f"{len(offers['fetched'])} games read, {counts['prop_quotes']} prop and "
                    f"{counts['game_quotes']} game quotes changed; {offers['http']}")
    if offers['incomplete']:
        code = 1
        parts.append("incomplete: the run's deadline or an error cut it short")
    if slot.priced:
        if offers['incomplete']:
            parts.append("snapshot not saved (incomplete)")
        else:
            saved = save_superbet(offers, lineups, fetched_at)
            parts.append(f"snapshot: {saved['superbet_props']} lines, {saved['superbet_game_odds']} game odds")
    return done(code == 0, '; '.join(parts))


# --- the loop, and one worker at a time across processes ---

def claim_worker(owner: str, now: datetime) -> bool:
    """Become (or stay) the one running worker: the worker file is ours or its heartbeat is stale."""
    with locked(WORKER_FILE):
        try:
            with open(WORKER_FILE, encoding='utf-8') as f:
                current = json.load(f)
        except (FileNotFoundError, ValueError):
            current = {}
        beat = current.get('heartbeat')
        if current.get('owner') not in (None, owner) and beat and \
                now - datetime.fromisoformat(beat) < HEARTBEAT_STALE:
            return False
        atomic_write_text(WORKER_FILE, json.dumps({'owner': owner, 'heartbeat': now.isoformat()}))
        return True


def release_worker(owner: str):
    with locked(WORKER_FILE):
        try:
            with open(WORKER_FILE, encoding='utf-8') as f:
                if json.load(f).get('owner') != owner:
                    return
        except (FileNotFoundError, ValueError):
            return
        os.remove(WORKER_FILE)


def worker_settings() -> Dict:
    try:
        with open(SETTINGS_FILE, encoding='utf-8') as f:
            return {'enabled': True, 'keep_awake': True} | json.load(f)
    except (FileNotFoundError, ValueError):
        return {'enabled': True, 'keep_awake': True}


def save_worker_settings(**changes):
    atomic_write_text(SETTINGS_FILE, json.dumps(worker_settings() | changes))


def _keep_awake(on: bool):
    """Ask Windows not to sleep while this thread runs (released when it stops or the process ends)."""
    if sys.platform != 'win32':
        return
    import ctypes
    ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if on else 0))


def _snapshot_age(now: datetime) -> timedelta:
    path = snapshot_file(CURRENT_SEASON, 'superbet_props')
    if not os.path.exists(path):
        return timedelta.max
    last = pd.read_csv(path, usecols=['fetched_at'])['fetched_at'].max()
    return now - pd.Timestamp(last).to_pydatetime() if isinstance(last, str) else timedelta.max


def _list_events() -> List[Dict]:
    import superbet_fetcher
    http = superbet_fetcher.client()
    return [{'event_id': e['eventId'], 'start_time': e.get('utcDate')} for e in superbet_fetcher.nba_events(36, http)]


def _tips(events: List[Dict]):
    return [(e['event_id'], pd.Timestamp(e['start_time']).to_pydatetime()) for e in events or [] if e.get('start_time')]


def loop(stop: threading.Event, status: Optional[Dict] = None, keep_awake: bool = False,
         now: Callable[[], datetime] = _utc_now):
    """Run slots until `stop` is set. `status` (shared with the dashboard) gets state, next, last, skipped."""
    from daily_snapshot import claim_superbet, log_run
    status = {} if status is None else status
    owner = f"{socket.gethostname()}:{os.getpid()}:{threading.get_ident()}"
    started = now()
    events, listed_at, done_through = None, None, None
    status.update(state='starting', started=started, last=None, skipped=0)
    if keep_awake:
        _keep_awake(True)
    try:
        while not stop.is_set():
            current = now()
            if not claim_worker(owner, current):
                status.update(state='another worker is running')
                stop.wait(60)
                continue
            if events is None:
                # on start: one run over every game, priced when the dashboards' snapshot is over an hour old
                start = fetch_schedule.Slot(current, ('start',), all_events=True,
                                            priced=_snapshot_age(current) > timedelta(hours=1))
                status.update(state='fetching (start)')
                result = run_slot(start, now)
                status.update(last=result)
                if result['events'] is None:
                    stop.wait(300)                 # couldn't list the games (blocked, offline): try again later
                    continue
                events, listed_at, done_through = result['events'], current, current
            elif current - listed_at > IDLE_RELIST and                     fetch_schedule.next_at(fetch_schedule.night_slots(_tips(events), current), current) is None:
                # no game ahead: list them again now and then (one request), to see the next night's
                if claim_superbet(SCHEDULED_GAP) is None:
                    try:
                        events = _list_events()
                    except Exception as e:
                        log_run(current, 'quotes', 'scheduled listing', 1, 0, f"listing failed: {e}"[:300])
                listed_at = current
            slots = fetch_schedule.night_slots(_tips(events), started - fetch_schedule.LATE)
            slot, skipped = fetch_schedule.due(slots, current, done_through)
            for s in skipped:
                log_run(current, 'quotes', f"scheduled {s.kind}", 1, 0, f"skipped: {s.at:%H:%M} UTC was missed")
                status['skipped'] = status.get('skipped', 0) + 1
                done_through = max(done_through or s.at, s.at)
            if slot:
                status.update(state=f"fetching ({slot.kind})")
                result = run_slot(slot, now)
                done_through = slot.at
                if result['events'] is not None:
                    events, listed_at = result['events'], current
                status.update(last=result)
            upcoming = fetch_schedule.next_at(slots, now())
            status.update(state='waiting', next=upcoming, games=len(_tips(events)))
            pause = 60 if upcoming is None else max(1.0, min(60.0, (upcoming - now()).total_seconds()))
            stop.wait(pause)
    finally:
        if keep_awake:
            _keep_awake(False)
        release_worker(owner)
        status.update(state='stopped')


def dry_run(at: datetime) -> str:
    """Tonight's slots from the latest saved snapshot's games (no contact), and the requests they'd make."""
    path = snapshot_file(CURRENT_SEASON, 'superbet_props')
    saved = pd.read_csv(path, usecols=['fetched_at', 'event_id', 'start_time'])
    latest = saved[saved['fetched_at'] == saved['fetched_at'].max()].drop_duplicates('event_id')
    events = [{'event_id': e, 'start_time': s} for e, s in zip(latest['event_id'], latest['start_time'])]
    tips = _tips(events)
    slots = fetch_schedule.night_slots(tips, at)
    all_upcoming = lambda s: sum(1 for _, t in tips if s.at < t <= s.at + fetch_schedule.HOURLY_HORIZON)
    lines, total = [], 0
    for s in slots:
        n = 1 + (all_upcoming(s) if s.all_events or s.priced else len(s.event_ids))
        total += n
        lines.append(f"{pd.Timestamp(s.at).tz_convert('Europe/Warsaw'):%a %H:%M}  {s.kind:<22} "
                     f"{n:>3} requests{'  priced' if s.priced else ''}{'  +RotoWire' if s.rotowire else ''}")
    return '\n'.join(lines + [f"{len(slots)} runs, about {total} Superbet requests"])


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--dry-run', action='store_true', help="print the slots, contact nothing")
    parser.add_argument('--now', help="the time to plan from (local time, Europe/Warsaw), with --dry-run")
    parser.add_argument('--keep-awake', action='store_true', help="keep Windows awake while running")
    args = parser.parse_args()
    if args.dry_run:
        at = pd.Timestamp(args.now, tz='Europe/Warsaw').tz_convert('UTC').to_pydatetime() if args.now else _utc_now()
        print(dry_run(at))
        sys.exit()
    stop_event = threading.Event()
    try:
        loop(stop_event, keep_awake=args.keep_awake)
    except KeyboardInterrupt:
        stop_event.set()
