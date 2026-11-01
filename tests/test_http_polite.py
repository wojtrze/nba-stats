"""Run with: python -m pytest tests"""
from datetime import datetime, timedelta, timezone

import pytest
import requests

import http_polite
from http_polite import Blocked, PoliteClient, RunDeadline

NOW = datetime(2026, 11, 2, 18, 0, tzinfo=timezone.utc)


class FakeResponse:
    def __init__(self, status=200, headers=None, body=None):
        self.status_code, self.headers, self.body = status, headers or {}, body or {}

    def json(self):
        return self.body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


class FakeSession:
    """Answers in order; an Exception in the list is raised."""
    def __init__(self, *answers):
        self.answers, self.calls = list(answers), []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append(headers or {})
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


class Clock:
    def __init__(self):
        self.t, self.slept = 0.0, []

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.slept.append(round(s, 2))
        self.t += s


def make(session, tmp_path, deadline=None, clock=None):
    clock = clock or Clock()
    return PoliteClient('host', session, deadline=deadline, state_path=str(tmp_path / 'state.json'),
                        sleep=clock.sleep, clock=clock, uniform=lambda a, b: a, now=lambda: NOW), clock


def test_pause_between_requests(tmp_path):
    http, clock = make(FakeSession(FakeResponse(), FakeResponse()), tmp_path)
    http.get('https://x/1')
    http.get('https://x/2')
    assert clock.slept == [3.0]                                     # REQUEST_DELAY's lower end, nothing before the first
    assert http_polite.requests_today('host', NOW, str(tmp_path / 'state.json')) == 2


def test_5xx_and_dropped_connection_are_retried_with_backoff(tmp_path):
    session = FakeSession(FakeResponse(503), requests.ConnectionError("reset"), FakeResponse(body={'ok': 1}))
    http, clock = make(session, tmp_path)
    assert http.get('https://x/u').json() == {'ok': 1}
    assert clock.slept == [10, 30]                                  # the backoff covers the pause
    assert http.stats['retries'] == 2 and http.stats['statuses'] == {'503': 1, '200': 1}


def test_retry_after_is_honoured(tmp_path):
    http, clock = make(FakeSession(FakeResponse(429, {'Retry-After': '45'}), FakeResponse()), tmp_path)
    http.get('https://x/u')
    assert 45 in clock.slept


def test_403_blocks_the_host_for_two_hours(tmp_path):
    http, _ = make(FakeSession(FakeResponse(403)), tmp_path)
    with pytest.raises(Blocked):
        http.get('https://x/u')
    until = http_polite.blocked_until('host', NOW, str(tmp_path / 'state.json'))
    assert until == NOW + timedelta(hours=2)
    again, _ = make(FakeSession(), tmp_path)
    with pytest.raises(Blocked):                                    # no request is made while blocked
        again.get('https://x/u')
    assert http_polite.blocked_until('host', NOW + timedelta(hours=2, seconds=1), str(tmp_path / 'state.json')) is None


def test_two_429_in_a_row_block(tmp_path):
    http, _ = make(FakeSession(FakeResponse(429), FakeResponse(429)), tmp_path)
    with pytest.raises(Blocked):
        http.get('https://x/u')


def test_deadline_ends_the_run_instead_of_waiting(tmp_path):
    http, clock = make(FakeSession(FakeResponse(503)), tmp_path, deadline=5)
    with pytest.raises(RunDeadline):
        http.get('https://x/u')
    assert clock.slept == []


def test_etag_turns_304_into_the_cached_body(tmp_path):
    session = FakeSession(FakeResponse(headers={'ETag': '"a"'}, body={'n': 1}), FakeResponse(304))
    http, _ = make(session, tmp_path)
    http.get('https://x/u')
    assert http.get('https://x/u').json() == {'n': 1}
    assert session.calls[1] == {'If-None-Match': '"a"'} and http.stats['not_modified'] == 1


def test_budget_counts_per_day(tmp_path):
    path = str(tmp_path / 'state.json')
    http_polite._count_request('host', NOW, path)
    http_polite._count_request('host', NOW + timedelta(days=1), path)
    assert http_polite.requests_today('host', NOW + timedelta(days=1), path) == 1
