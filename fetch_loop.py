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

A watchdog gives each slot its time limit (run_guarded): a run still going after it is logged as stuck, with the last
step it reached and every thread's stack in data/fetch_hangs.log, and the schedule goes on. On 1.11 one run hung for
4.4 h and every slot of the night waited behind it. Slots nobody ran (the dashboard was off, or started late) are
logged when a worker starts. The loop beats in `status['beat']` at least every BEAT_EVERY, so the dashboard's
supervisor (dashboard_v2/core/fetch_worker.py) can replace a loop that stopped beating.

The schedule's settings (fetch_schedule.Config) are saved with the worker's switches (worker_settings) and read again
at every turn of the loop, so a change in the Data center applies from the next slot.

On 5.11 the whole process froze for 47 h: Windows' console QuickEdit mode (a click in the console window starts a
selection) blocks every write to the console until a key is pressed, and a run wrote a line after every game it
read. disable_quick_edit() switches that mode off for the program's console.
"""
import argparse
import json
import logging
import os
import socket
import sys
import threading
import time
import traceback
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
SLOT_LIMIT = timedelta(minutes=fetch_schedule.SLOT_LIMIT_MIN)   # default for a slot's run (RUN_DEADLINE 4 min)
BEAT_EVERY = timedelta(seconds=30)         # the loop's heartbeat (status['beat']) while waiting
HANG_LOG = os.path.join('data', 'fetch_hangs.log')
MISSED_LOOKBACK = timedelta(hours=12)      # how far back a starting worker looks for slots nobody ran

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


def run_slot(slot: fetch_schedule.Slot, now: Callable[[], datetime] = _utc_now, progress: Optional[Dict] = None,
             cancelled: Optional[threading.Event] = None) -> Dict:
    """Fetch and save one slot. Returns a status dict (ok, summary, events: the listed games). progress gets the
    step it's at (stage, since); once `cancelled` is set (the watchdog gave up on it) it saves nothing."""
    import superbet_fetcher
    from daily_snapshot import claim_superbet, log_run, save_lineups_if_changed, save_superbet
    from http_polite import DAILY_REQUEST_BUDGET, Blocked, requests_today

    progress = {} if progress is None else progress
    step = lambda stage: progress.update(stage=stage, since=now())
    abandoned = lambda: cancelled is not None and cancelled.is_set()
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
        step("RotoWire")
        try:
            from lineup_fetcher import fetch_lineups
            lineups = pd.DataFrame(fetch_lineups())
            saved = save_lineups_if_changed(lineups, fetched_at)
            parts.append(f"RotoWire: {saved or 'unchanged'}")
        except Exception as e:
            log.warning("RotoWire failed: %s", e)
            parts.append(f"RotoWire failed: {e}")
            lineups = _saved_lineups()
    http = superbet_fetcher.client(trace=lambda line: step(f"Superbet: {line}"))
    try:
        wanted = None if slot.all_events or slot.priced else slot.event_ids
        offers = superbet_fetcher.todays_offers(event_ids=wanted, http=http)
    except Blocked as e:
        return done(False, f"Superbet: {e}; " + '; '.join(parts))
    except Exception as e:
        return done(False, f"Superbet failed: {e} ({http.summary()}); " + '; '.join(parts))
    events = offers['events']
    if abandoned():
        return done(False, f"finished after the watchdog gave up on it: nothing saved ({offers['http']})")
    step("saving quotes")
    counts = save_quotes(offers, fetched_at, slot.kind)
    parts.insert(0, f"{len(offers['fetched'])} games read, {counts['prop_quotes']} prop and "
                    f"{counts['game_quotes']} game quotes changed; {offers['http']}")
    if offers['incomplete']:
        code = 1
        parts.append("incomplete: the run's deadline or an error cut it short")
    if slot.priced:
        if offers['incomplete']:
            parts.append("snapshot not saved (incomplete)")
        elif abandoned():
            parts.append("snapshot not saved (the watchdog gave up on the run)")
        else:
            step("saving the snapshot (pricing)")
            saved = save_superbet(offers, lineups, fetched_at)
            parts.append(f"snapshot: {saved['superbet_props']} lines, {saved['superbet_game_odds']} game odds")
    return done(code == 0, '; '.join(parts))


def run_guarded(slot: fetch_schedule.Slot, now: Callable[[], datetime] = _utc_now,
                limit: timedelta = SLOT_LIMIT, run: Callable = run_slot) -> Dict:
    """run_slot in its own thread, given at most `limit`. A run still going after it is abandoned: logged as stuck
    with the last step it reached, and told to save nothing if it ever goes on (its quotes would carry a time long
    past). An error in the run is logged as a failed run instead of stopping the loop."""
    from daily_snapshot import log_run
    progress, cancelled, box = {}, threading.Event(), {}
    started = now()

    def target():
        try:
            box['result'] = run(slot, now, progress, cancelled)
        except Exception as e:                 # noqa: BLE001  (one slot's failure mustn't end the schedule)
            log.exception("scheduled %s failed", slot.kind)
            box['error'] = e

    worker = threading.Thread(target=target, name=f"fetch-{slot.kind}", daemon=True)
    worker.start()
    worker.join(limit.total_seconds())
    command = f"scheduled {slot.kind}"
    if 'result' in box:
        return box['result']
    if 'error' in box:
        summary = f"failed: {type(box['error']).__name__}: {box['error']}"
        log_run(started, 'quotes', command, 1, (now() - started).total_seconds(), summary[:300])
        return {'ok': False, 'summary': summary, 'events': None, 'at': started}
    cancelled.set()
    since = progress.get('since')
    summary = (f"stuck: abandoned after {limit.total_seconds() / 60:.0f} min at: {progress.get('stage', 'starting')}"
               + (f" (since {since:%H:%M:%S} UTC)" if since else ""))
    dump_threads(f"scheduled {slot.kind} {summary}", now())
    log.warning("scheduled %s %s", slot.kind, summary)
    log_run(started, 'quotes', command, 1, limit.total_seconds(), summary[:300])
    return {'ok': False, 'summary': summary, 'events': None, 'at': started}


def dump_threads(why: str, at: datetime, path: str = HANG_LOG):
    """Append every thread's stack to data/fetch_hangs.log, so a hang shows where each thread waited."""
    names = {t.ident: t.name for t in threading.enumerate()}
    lines = [f"=== {at:%Y-%m-%d %H:%M:%S} UTC: {why}"]
    for ident, frame in sys._current_frames().items():
        lines.append(f"--- thread {names.get(ident, ident)}")
        lines.extend(line.rstrip('\n') for line in traceback.format_stack(frame))
    try:
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        with open(path, 'a', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
    except OSError as e:
        log.warning("couldn't write %s: %s", path, e)


def disable_quick_edit() -> bool:
    """Switch off QuickEdit for this program's Windows console (see the module's docstring); True when done. Does
    nothing elsewhere or without a console."""
    if sys.platform != 'win32':
        return False
    try:
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-10)          # STD_INPUT_HANDLE
        mode = wintypes.DWORD()
        if not handle or not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        quick_edit, extended_flags = 0x0040, 0x0080
        return bool(kernel32.SetConsoleMode(handle, (mode.value & ~quick_edit) | extended_flags))
    except Exception:                                # noqa: BLE001  (a convenience: never stop the program)
        return False


def _last_scheduled_run() -> Optional[datetime]:
    """When the run log last saw a scheduled fetch (run, skipped or stuck)."""
    from daily_snapshot import RUN_LOG
    if not os.path.exists(RUN_LOG):
        return None
    runs = pd.read_csv(RUN_LOG, usecols=['started_at', 'command'])
    runs = runs[runs['command'].astype(str).str.startswith('scheduled')]
    return pd.Timestamp(runs['started_at'].max()).to_pydatetime() if len(runs) else None


def _saved_tips() -> List:
    """(event_id, tip-off) of the games the scheduled fetches have read, for slots of games no longer listed."""
    path = snapshot_file(CURRENT_SEASON, 'superbet_event_fetches')
    if not os.path.exists(path):
        return []
    saved = pd.read_csv(path, usecols=['event_id', 'start_time']).dropna().drop_duplicates('event_id', keep='last')
    return [(e, pd.Timestamp(t).to_pydatetime()) for e, t in zip(saved['event_id'], saved['start_time'])]


def missed_slots(tips, last_run: Optional[datetime], started: datetime,
                 cfg: fetch_schedule.Config = fetch_schedule.DEFAULT) -> List[fetch_schedule.Slot]:
    """The slots after the last scheduled run (at most MISSED_LOOKBACK back) that were due more than the late
    tolerance before this worker started: nobody ran them."""
    since = max(last_run or started, started - MISSED_LOOKBACK)
    tips = list({e: t for e, t in tips}.items())
    return [s for s in fetch_schedule.night_slots(tips, since, cfg) if s.at < started - cfg.late_by]


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


def _saved_settings() -> Dict:
    try:
        with open(SETTINGS_FILE, encoding='utf-8') as f:
            saved = json.load(f)
        return saved if isinstance(saved, dict) else {}
    except (FileNotFoundError, ValueError):
        return {}


def worker_settings() -> Dict:
    """The worker's switches (enabled, keep_awake) and the schedule's settings ('schedule': fetch_schedule.Config
    as a dict; missing or invalid = the defaults)."""
    saved = _saved_settings()
    out = {'enabled': True, 'keep_awake': True} | saved
    out['schedule'] = schedule_config(saved).to_dict()
    return out


def schedule_config(settings: Optional[Dict] = None) -> fetch_schedule.Config:
    """The saved schedule settings (fetch_schedule.Config.from_dict: invalid ones fall back to the defaults)."""
    settings = _saved_settings() if settings is None else settings
    return fetch_schedule.Config.from_dict(settings.get('schedule'))


def save_worker_settings(**changes):
    """Save the switches and/or the schedule (changes['schedule']: a fetch_schedule.Config or its dict)."""
    if isinstance(changes.get('schedule'), fetch_schedule.Config):
        changes['schedule'] = changes['schedule'].to_dict()
    atomic_write_text(SETTINGS_FILE, json.dumps(worker_settings() | changes, indent=1))


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


def _pause(stop: threading.Event, seconds: float, status: Dict, now: Callable[[], datetime]):
    """stop.wait(seconds), beating in status every BEAT_EVERY meanwhile."""
    end = time.monotonic() + seconds
    while not stop.is_set():
        status['beat'] = now()
        left = end - time.monotonic()
        if left <= 0:
            return
        stop.wait(min(left, BEAT_EVERY.total_seconds()))


def loop(stop: threading.Event, status: Optional[Dict] = None, keep_awake: bool = False,
         now: Callable[[], datetime] = _utc_now):
    """Run slots until `stop` is set. `status` (shared with the dashboard) gets state, next, last, skipped and beat
    (the loop's last sign of life). The schedule's settings are read again at every turn."""
    from daily_snapshot import claim_superbet, log_run
    status = {} if status is None else status
    owner = f"{socket.gethostname()}:{os.getpid()}:{threading.get_ident()}"
    started = now()
    last_run = _last_scheduled_run()
    events, listed_at, done_through = None, None, None
    status.update(state='starting', started=started, last=None, skipped=0, beat=started)
    if keep_awake:
        _keep_awake(True)
    try:
        while not stop.is_set():
            current = now()
            status['beat'] = current
            cfg = schedule_config()
            limit = timedelta(minutes=cfg.slot_limit)
            if not claim_worker(owner, current):
                status.update(state='another worker is running')
                _pause(stop, 60, status, now)
                continue
            if events is None:
                # on start: one run over every game, priced when the dashboards' snapshot is over an hour old
                start = fetch_schedule.Slot(current, ('start',), all_events=True,
                                            priced=_snapshot_age(current) > timedelta(hours=1))
                status.update(state='fetching (start)')
                result = run_guarded(start, now, limit)
                status.update(last=result)
                if result['events'] is None:
                    _pause(stop, 300, status, now)  # couldn't list the games (blocked, offline): try again later
                    continue
                events, listed_at, done_through = result['events'], current, current
                missed = missed_slots(_tips(events) + _saved_tips(), last_run, started, cfg)
                if missed:
                    log_run(current, 'quotes', 'scheduled missed', 1, 0,
                            f"skipped: {len(missed)} slots nobody ran ({missed[0].at:%H:%M} {missed[0].kind} to "
                            f"{missed[-1].at:%H:%M} {missed[-1].kind} UTC): the dashboard was off or busy"[:300])
                    status['skipped'] = status.get('skipped', 0) + len(missed)
            elif current - listed_at > IDLE_RELIST and                     fetch_schedule.next_at(fetch_schedule.night_slots(_tips(events), current), current) is None:
                # no game ahead: list them again now and then (one request), to see the next night's
                if claim_superbet(SCHEDULED_GAP) is None:
                    try:
                        events = _list_events()
                    except Exception as e:
                        log_run(current, 'quotes', 'scheduled listing', 1, 0, f"listing failed: {e}"[:300])
                listed_at = current
            slots = fetch_schedule.night_slots(_tips(events), started - cfg.late_by, cfg)
            slot, skipped = fetch_schedule.due(slots, current, done_through, cfg.late_by)
            for s in skipped:
                log_run(current, 'quotes', f"scheduled {s.kind}", 1, 0, f"skipped: {s.at:%H:%M} UTC was missed")
                status['skipped'] = status.get('skipped', 0) + 1
                done_through = max(done_through or s.at, s.at)
            if slot:
                status.update(state=f"fetching ({slot.kind})")
                result = run_guarded(slot, now, limit)
                done_through = slot.at
                if result['events'] is not None:
                    events, listed_at = result['events'], current
                status.update(last=result)
            upcoming = fetch_schedule.next_at(slots, now())
            status.update(state='waiting', next=upcoming, games=len(_tips(events)))
            pause = 60 if upcoming is None else max(1.0, min(60.0, (upcoming - now()).total_seconds()))
            _pause(stop, pause, status, now)
    finally:
        if keep_awake:
            _keep_awake(False)
        release_worker(owner)
        status.update(state='stopped')


def known_tips() -> List:
    """(event_id, tip-off) of the games in the latest saved snapshot and the scheduled reads, without contacting
    anything."""
    tips = []
    path = snapshot_file(CURRENT_SEASON, 'superbet_props')
    if os.path.exists(path):
        saved = pd.read_csv(path, usecols=['fetched_at', 'event_id', 'start_time'])
        latest = saved[saved['fetched_at'] == saved['fetched_at'].max()].drop_duplicates('event_id')
        tips = _tips([{'event_id': e, 'start_time': s} for e, s in zip(latest['event_id'], latest['start_time'])])
    return list({e: t for e, t in tips + _saved_tips()}.items())


def plan(tips, at: datetime, cfg: fetch_schedule.Config = fetch_schedule.DEFAULT) -> pd.DataFrame:
    """The slots after `at` under `cfg`: at (UTC), kind, requests (Superbet: the listing plus one per game read),
    priced, rotowire."""
    slots = fetch_schedule.night_slots(tips, at, cfg)
    all_upcoming = lambda s: sum(1 for _, t in tips if s.at < t <= s.at + cfg.horizon)
    rows = [{'at': s.at, 'kind': s.kind,
             'requests': 1 + (all_upcoming(s) if s.all_events or s.priced else len(s.event_ids)),
             'priced': s.priced, 'rotowire': s.rotowire} for s in slots]
    return pd.DataFrame(rows, columns=['at', 'kind', 'requests', 'priced', 'rotowire'])


def dry_run(at: datetime, cfg: Optional[fetch_schedule.Config] = None) -> str:
    """Tonight's slots from the saved games (no contact) under the saved settings, and the requests they'd make."""
    p = plan(known_tips(), at, cfg or schedule_config())
    lines = [f"{pd.Timestamp(r.at).tz_convert('Europe/Warsaw'):%a %H:%M}  {r.kind:<22} {r.requests:>3} requests"
             f"{'  priced' if r.priced else ''}{'  +RotoWire' if r.rotowire else ''}" for r in p.itertuples()]
    return '\n'.join(lines + [f"{len(p)} runs, about {int(p['requests'].sum())} Superbet requests"])


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
    disable_quick_edit()
    stop_event = threading.Event()
    try:
        loop(stop_event, keep_awake=args.keep_awake)
    except KeyboardInterrupt:
        stop_event.set()
