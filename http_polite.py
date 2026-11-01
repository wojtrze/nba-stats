"""Polite HTTP for the scrapers (Superbet's offer API, RotoWire's lineups page).

- A random pause of REQUEST_DELAY seconds between two requests of one client, so a run never fires back-to-back.
- Retries with exponential backoff and jitter on 429, 5xx, dropped connections and timeouts; Retry-After is
  honoured. A wait that would run past the run's deadline ends the run instead (RunDeadline).
- A circuit breaker: 403, or two 429 in a row, blocks the host for BACKOFF_ON_BLOCK, recorded in a state file
  shared by every process (Blocked); nothing contacts it again before then.
- A daily request budget per host in the same state file; the scheduled fetches stop when it's used up.
- Conditional requests: a response's ETag is sent back as If-None-Match, and a 304 returns the cached body.

The clock, sleep and random draw are injectable, so the tests run without waiting.
"""
import json
import os
import random
import time
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, Optional, Tuple

import requests

from safe_io import atomic_write_text, locked

REQUEST_DELAY = (3.0, 6.0)          # seconds between two requests of one client
BACKOFF = (10, 30, 90)              # seconds before retry 1, 2, 3 (plus up to 25% jitter)
TIMEOUT = (5, 20)                   # connect, read
BACKOFF_ON_BLOCK = timedelta(hours=2)
DAILY_REQUEST_BUDGET = 400
STATE_FILE = os.path.join('data', 'scrape_state.json')
RETRY_STATUSES = {429, 500, 502, 503, 504}


class Blocked(Exception):
    """The host refused us (403 or repeated 429), now or within BACKOFF_ON_BLOCK; `until` is when it's tried again."""
    def __init__(self, host: str, until: datetime, reason: str = ''):
        super().__init__(f"{host} blocked until {until:%Y-%m-%d %H:%M} UTC{f' ({reason})' if reason else ''}")
        self.host, self.until = host, until


class RunDeadline(Exception):
    """The run's time is up (a request or a backoff would end after its deadline)."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --- the state shared by every process: blocks and the daily budget, per host ---

def _read_state(path: str) -> Dict:
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {}


def blocked_until(host: str, now: Optional[datetime] = None, path: str = STATE_FILE) -> Optional[datetime]:
    """When the host may be contacted again after a block; None = not blocked."""
    until = _read_state(path).get(host, {}).get('blocked_until')
    until = datetime.fromisoformat(until) if until else None
    return until if until and until > (now or _now()) else None


def block(host: str, reason: str, now: Optional[datetime] = None, path: str = STATE_FILE) -> datetime:
    until = (now or _now()) + BACKOFF_ON_BLOCK
    with locked(path):
        state = _read_state(path)
        state.setdefault(host, {}).update(blocked_until=until.isoformat(), block_reason=reason)
        atomic_write_text(path, json.dumps(state, indent=1))
    return until


def requests_today(host: str, now: Optional[datetime] = None, path: str = STATE_FILE) -> int:
    entry = _read_state(path).get(host, {})
    return entry.get('count', 0) if entry.get('day') == f"{now or _now():%Y-%m-%d}" else 0


def _count_request(host: str, now: datetime, path: str):
    with locked(path):
        state = _read_state(path)
        entry = state.setdefault(host, {})
        day = f"{now:%Y-%m-%d}"
        entry['count'] = entry.get('count', 0) + 1 if entry.get('day') == day else 1
        entry['day'] = day
        atomic_write_text(path, json.dumps(state, indent=1))


def _retry_after(response: requests.Response) -> Optional[float]:
    value = response.headers.get('Retry-After')
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            from email.utils import parsedate_to_datetime
            return max(0.0, (parsedate_to_datetime(value) - _now()).total_seconds())
        except (TypeError, ValueError):
            return None


class PoliteClient:
    """GETs to one host with pauses, retries, the circuit breaker, the budget and ETags. `stats` counts what a run
    did (requests, retries, not_modified, statuses, http_seconds), for the run log."""

    def __init__(self, host: str, session: requests.Session, deadline: Optional[float] = None,
                 delay: Tuple[float, float] = REQUEST_DELAY, backoff: Tuple[float, ...] = BACKOFF,
                 state_path: str = STATE_FILE, sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic, uniform: Callable[[float, float], float] = random.uniform,
                 now: Callable[[], datetime] = _now, etags: Optional[Dict] = None):
        self.host, self.session, self.delay, self.backoff = host, session, delay, backoff
        self.state_path, self.sleep, self.clock, self.uniform, self.now = state_path, sleep, clock, uniform, now
        self.deadline = None if deadline is None else clock() + deadline
        self.etags = {} if etags is None else etags          # url -> (etag, response)
        self._last = None
        self.stats = {'requests': 0, 'retries': 0, 'not_modified': 0, 'statuses': {}, 'http_seconds': 0.0}

    def _wait(self, seconds: float):
        if self.deadline is not None and self.clock() + seconds > self.deadline:
            raise RunDeadline(f"{self.host}: the run's deadline would pass while waiting {seconds:.0f} s")
        if seconds > 0:
            self.sleep(seconds)

    def _pause(self):
        if self._last is not None:
            self._wait(self._last + self.uniform(*self.delay) - self.clock())

    def get(self, url: str, params: Optional[dict] = None, **kwargs) -> requests.Response:
        until = blocked_until(self.host, self.now(), self.state_path)
        if until:
            raise Blocked(self.host, until)
        key = requests.Request('GET', url, params=params).prepare().url
        cached = self.etags.get(key)
        headers = {'If-None-Match': cached[0]} if cached else {}
        too_many = 0
        for attempt in range(len(self.backoff) + 1):
            self._pause()
            t0 = self.clock()
            self._last = t0
            _count_request(self.host, self.now(), self.state_path)
            self.stats['requests'] += 1
            try:
                response = self.session.get(url, params=params, headers=headers, timeout=TIMEOUT, **kwargs)
            except (requests.ConnectionError, requests.Timeout) as e:
                self.stats['http_seconds'] += self.clock() - t0
                if attempt == len(self.backoff):
                    raise
                self._retry(attempt, None, str(e))
                continue
            self.stats['http_seconds'] += self.clock() - t0
            self._last = self.clock()
            status = response.status_code
            self.stats['statuses'][str(status)] = self.stats['statuses'].get(str(status), 0) + 1
            if status == 304 and cached:
                self.stats['not_modified'] += 1
                return cached[1]
            if status == 403:
                raise Blocked(self.host, block(self.host, '403', self.now(), self.state_path), '403')
            if status == 429:
                too_many += 1
                if too_many >= 2:
                    raise Blocked(self.host, block(self.host, '429 twice', self.now(), self.state_path), '429')
            if status in RETRY_STATUSES and attempt < len(self.backoff):
                self._retry(attempt, _retry_after(response), str(status))
                continue
            response.raise_for_status()
            if response.headers.get('ETag'):
                self.etags[key] = (response.headers['ETag'], response)
            return response
        raise RuntimeError("unreachable")

    def _retry(self, attempt: int, retry_after: Optional[float], why: str):
        self.stats['retries'] += 1
        base = self.backoff[attempt]
        self._wait(max(retry_after or 0, base + self.uniform(0, base * 0.25)))

    def summary(self) -> str:
        s = self.stats
        codes = ', '.join(f"{k}×{v}" for k, v in sorted(s['statuses'].items()))
        return (f"{s['requests']} requests ({codes or 'none answered'}), {s['retries']} retries, "
                f"{s['not_modified']} unchanged, {s['http_seconds']:.0f} s HTTP")
