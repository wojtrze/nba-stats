"""The scheduled fetches (fetch_loop.loop) as a background thread of this dashboard's process: it starts with the
dashboard (when switched on in the Data center) and stops when the dashboard is closed. One per process
(st.cache_resource); fetch_loop.claim_worker keeps it to one across processes too.

A supervisor thread watches the loop's heartbeat (status['beat']): a loop alive but silent for longer than a slot's
time limit plus STALE_MARGIN is stuck (on 5.11 it waited 47 h on the console). It's told to stop and left behind, its
stack goes to data/fetch_hangs.log, the run log gets a 'scheduled restart' row, and a new loop takes over (the
stuck one's heartbeat in data/fetch_worker.json is stale by then, so claim_worker lets the new one in).
"""
import threading
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, Optional

import streamlit as st

import fetch_loop

STALE_MARGIN = timedelta(minutes=4)
CHECK_EVERY = 60                                   # seconds between the supervisor's checks


@st.cache_resource(show_spinner=False)
def _worker() -> Dict:
    return {'thread': None, 'stop': None, 'status': {}, 'supervisor': None, 'restarts': 0}


def running() -> bool:
    w = _worker()
    return bool(w['thread'] and w['thread'].is_alive())


def _launch(w: Dict):
    w['stop'], w['status'] = threading.Event(), {}
    w['thread'] = threading.Thread(target=fetch_loop.loop, name='fetch-loop', daemon=True,
                                   args=(w['stop'], w['status'], fetch_loop.worker_settings()['keep_awake']))
    w['thread'].start()


def stuck_since(status: Dict, now: datetime, slot_limit_min: int) -> Optional[datetime]:
    """The loop's last beat when it's older than a slot's limit plus STALE_MARGIN (the loop is stuck), else None."""
    beat = status.get('beat')
    if beat is None or now - beat <= timedelta(minutes=slot_limit_min) + STALE_MARGIN:
        return None
    return beat


def check(w: Dict, now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> bool:
    """One supervisor check: replace a stuck loop. True when it did."""
    if not (w['thread'] and w['thread'].is_alive()):
        return False
    t = now()
    beat = stuck_since(w['status'], t, fetch_loop.schedule_config().slot_limit)
    if beat is None:
        return False
    from daily_snapshot import log_run
    why = f"restart: the loop was stuck since {beat:%H:%M} UTC (state: {w['status'].get('state', '?')})"
    fetch_loop.dump_threads(f"scheduled {why}", t)
    log_run(t, 'quotes', 'scheduled restart', 1, (t - beat).total_seconds(), why)
    w['stop'].set()                                # it ends if it ever wakes; meanwhile it's left behind
    w['restarts'] += 1
    _launch(w)
    return True


def _supervise(w: Dict):
    while True:
        try:
            if fetch_loop.worker_settings()['enabled']:
                check(w)
        except Exception:                          # noqa: BLE001  (the supervisor must outlive any one check)
            pass
        threading.Event().wait(CHECK_EVERY)


def start():
    w = _worker()
    fetch_loop.disable_quick_edit()
    if not (w['supervisor'] and w['supervisor'].is_alive()):
        w['supervisor'] = threading.Thread(target=_supervise, args=(w,), name='fetch-supervisor', daemon=True)
        w['supervisor'].start()
    if running():
        return
    _launch(w)


def stop():
    w = _worker()
    if w['stop'] is not None:
        w['stop'].set()


def follow_settings():
    """Start or stop the worker to match the saved switch; called on every page run."""
    if fetch_loop.worker_settings()['enabled']:
        start()
    elif running():
        stop()


def status() -> Dict:
    w = _worker()
    return dict(w['status']) | {'running': running(), 'restarts': w['restarts']}
