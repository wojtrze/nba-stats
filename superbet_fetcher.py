# Superbet player-prop offers (over/under lines) for NBA games, via Superbet's public offer API.
import logging
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import requests

from bet_fetcher import NORMALIZED_TEAM_NAME

log = logging.getLogger(__name__)

OFFER_API = "https://production-superbet-offer-pl.freetls.fastly.net/v2/pl-PL"
NBA_TOURNAMENT_ID = 2176

# over/under player markets ("Zawodnik - liczba ...") -> stat names used in the gamelogs
PLAYER_MARKETS = {
    233565: 'PTS',
    233566: 'AST',
    233567: 'REB',
    233568: '3PM',
    233571: 'PA',   # points + assists
    233572: 'PR',   # points + rebounds
}

TEAM_NAME_ALIASES = {"LA Clippers": "Los Angeles Clippers"}

_session = requests.Session()
_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/126.0 Safari/537.36",
    "Accept": "application/json",
    "Origin": "https://superbet.pl",
    "Referer": "https://superbet.pl/",
})


def _get(path: str, **params) -> dict:
    response = _session.get(f"{OFFER_API}/{path}", params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def superbet_name_to_ESPN(name: str) -> str:
    # "Jackson Jr., Jaren" -> "JarenJacksonJr.", accents removed ("Jokić" -> "Jokic")
    ascii_name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    return ''.join(part.replace(' ', '') for part in reversed(ascii_name.split(',')))


def team_abbr(full_name: str) -> Optional[str]:
    full_name = full_name.strip()
    return NORMALIZED_TEAM_NAME.get(TEAM_NAME_ALIASES.get(full_name, full_name))


def nba_events(hours_ahead: int = 36, tournament_id: int = NBA_TOURNAMENT_ID) -> List[Dict]:
    now = datetime.now(timezone.utc)
    data = _get("events/by-date", currentStatus="active", offerState="prematch",
                startDate=now.strftime("%Y-%m-%d %H:%M:%S"),
                endDate=(now + timedelta(hours=hours_ahead)).strftime("%Y-%m-%d %H:%M:%S"))
    return [e for e in data['data'] if e['tournamentId'] == tournament_id]


def event_props(event_id: int) -> List[Dict]:
    """Over/under player props of one event, one dict per outcome (over and under are separate)."""
    event = _get(f"events/{event_id}")['data'][0]
    home_name, away_name = event['matchName'].split('·')
    home, away = team_abbr(home_name), team_abbr(away_name)
    props = []
    for odd in event.get('odds') or []:
        bet_type = PLAYER_MARKETS.get(odd['marketId'])
        if bet_type is None or odd.get('status') != 'active':
            continue
        name = odd['specifiers']['player'].strip()
        over_under = 'Over' if 'powyżej' in odd['name'] else 'Under' if 'poniżej' in odd['name'] else None
        if over_under is None:
            log.warning("Unknown outcome %r in event %s", odd['name'], event_id)
            continue
        props.append({"name": name,
                      "name_ESPN": superbet_name_to_ESPN(name),
                      "odds": odd['price'],
                      "line": float(odd['specifiers']['total']),
                      "over_under": over_under,
                      "home": home,
                      "away": away,
                      "bet_type": bet_type,
                      "id": odd['uuid'],
                      "event_id": event_id,
                      "start_time": event['utcDate']})
    return props


def all_today_props(hours_ahead: int = 36) -> List[Dict]:
    result = []
    for event in nba_events(hours_ahead):
        props = event_props(event['eventId'])
        if props and (props[0]['home'] is None or props[0]['away'] is None):
            log.warning("Unmapped team name in %r, skipping", event['matchName'])
            continue
        print(f"{' @ '.join(reversed(event['matchName'].split(chr(0xb7))))}: {len(props)} player props")
        result.extend(props)
    return result


if __name__ == '__main__':
    for prop in all_today_props():
        print(prop)
