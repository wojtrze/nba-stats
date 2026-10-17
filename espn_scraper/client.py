import logging
import random
import time

import requests

BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
MIN_DELAY = 0.5
MAX_DELAY = 1.5
RETRIES = 4

log = logging.getLogger(__name__)

_session = requests.Session()
_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/126.0 Safari/537.36",
    "Accept": "application/json",
})


def get_json(endpoint: str, **params) -> dict:
    """GET {BASE_URL}/{endpoint} with a polite delay and exponential backoff on errors."""
    return get_url(f"{BASE_URL}/{endpoint}", **params)


def get_url(url: str, **params) -> dict:
    """GET an absolute ESPN API url (e.g. a core-API $ref) with delay and backoff."""
    for attempt in range(1, RETRIES + 1):
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
        try:
            response = _session.get(url, params=params, timeout=20)
            if response.status_code == 200:
                return response.json()
            log.warning("HTTP %s for %s %s (attempt %d)", response.status_code, url, params, attempt)
            if 400 <= response.status_code < 500 and response.status_code != 429:
                response.raise_for_status()
        except requests.RequestException as e:
            if attempt == RETRIES:
                raise
            log.warning("Request error for %s %s: %s (attempt %d)", url, params, e, attempt)
        time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed to fetch {url} {params} after {RETRIES} attempts")


def scoreboard(date_yyyymmdd: str) -> dict:
    return get_json("scoreboard", dates=date_yyyymmdd)


def summary(game_id: str) -> dict:
    return get_json("summary", event=game_id)
