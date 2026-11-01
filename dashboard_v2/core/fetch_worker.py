"""The scheduled fetches (fetch_loop.loop) as a background thread of this dashboard's process: it starts with the
dashboard (when switched on in the Data center) and stops when the dashboard is closed. One per process
(st.cache_resource); fetch_loop.claim_worker keeps it to one across processes too."""
import threading
from typing import Dict

import streamlit as st

import fetch_loop


@st.cache_resource(show_spinner=False)
def _worker() -> Dict:
    return {'thread': None, 'stop': None, 'status': {}}


def running() -> bool:
    w = _worker()
    return bool(w['thread'] and w['thread'].is_alive())


def start():
    w = _worker()
    if running():
        return
    w['stop'], w['status'] = threading.Event(), {}
    w['thread'] = threading.Thread(target=fetch_loop.loop, name='fetch-loop', daemon=True,
                                   args=(w['stop'], w['status'], fetch_loop.worker_settings()['keep_awake']))
    w['thread'].start()


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
    return dict(_worker()['status']) | {'running': running()}
