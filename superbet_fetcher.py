# Superbet offers for NBA games (player over/under props and game markets), via Superbet's public offer API.
import logging
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import requests

from bet_fetcher import NORMALIZED_TEAM_NAME

log = logging.getLogger(__name__)

OFFER_API = "https://production-superbet-offer-pl.freetls.fastly.net/v2/pl-PL"
NBA_SPORT_ID = 4
NBA_TOURNAMENT_ID = 164   # 2176 was used before the 2026/27 season

# over/under player markets ("Zawodnik - liczba ...") -> stat names used in the gamelogs
PLAYER_MARKETS = {
    233565: 'PTS',
    233566: 'AST',
    233567: 'REB',
    233568: '3PM',
    233569: 'ARP',  # points + rebounds + assists
    233570: 'RA',   # rebounds + assists
    233571: 'PA',   # points + assists
    233572: 'PR',   # points + rebounds
    235217: 'BLK',
    235218: 'STL',
    200985: 'TO',
    231806: 'FGM',
    231807: 'FGA',
    231804: 'FTM',
    231805: 'FTA',
    231810: '3PA',
    231811: 'PF',
}

# game markets, all including overtime. Moneyline outcomes are '1' (home) / '2' (away); the handicap's
# 'hcp' specifier is the home team's handicap.
GAME_MARKETS = {
    759: 'ML',
    768: 'SPREAD',
    753: 'TOTAL',
    758: 'HOME_TOTAL',
    776: 'AWAY_TOTAL',
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
    # "Jackson Jr., Jaren" -> "JarenJacksonJr.", accents removed ("Jokić" -> "Jokic"); "Ausar Thompson" -> "AusarThompson"
    ascii_name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    return ''.join(part.replace(' ', '') for part in reversed(ascii_name.split(',')))


def team_abbr(full_name: str) -> Optional[str]:
    full_name = full_name.strip()
    return NORMALIZED_TEAM_NAME.get(TEAM_NAME_ALIASES.get(full_name, full_name))


def nba_events(hours_ahead: int = 36) -> List[Dict]:
    now = datetime.now(timezone.utc)
    data = _get("events/by-date", currentStatus="active", offerState="prematch",
                startDate=now.strftime("%Y-%m-%d %H:%M:%S"),
                endDate=(now + timedelta(hours=hours_ahead)).strftime("%Y-%m-%d %H:%M:%S"))
    return [e for e in data['data'] if e['tournamentId'] == NBA_TOURNAMENT_ID and e.get('sportId') == NBA_SPORT_ID]


def fetch_event(event_id: int) -> Dict:
    return _get(f"events/{event_id}")['data'][0]


def _teams(event: Dict):
    home_name, away_name = event['matchName'].split('·')
    return team_abbr(home_name), team_abbr(away_name)


def _over_under(outcome_name: str) -> Optional[str]:
    return 'Over' if 'powyżej' in outcome_name else 'Under' if 'poniżej' in outcome_name else None


def event_props(event: Dict) -> List[Dict]:
    """Over/under player props of one event, one dict per outcome (over and under are separate)."""
    home, away = _teams(event)
    props = []
    for odd in event.get('odds') or []:
        bet_type = PLAYER_MARKETS.get(odd['marketId'])
        if bet_type is None or odd.get('status') != 'active':
            continue
        name = odd['specifiers']['player'].strip()
        over_under = _over_under(odd['name'])
        if over_under is None:
            log.warning("Unknown outcome %r in event %s", odd['name'], event['eventId'])
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
                      "event_id": event['eventId'],
                      "start_time": event['utcDate']})
    return props


def event_game_odds(event: Dict) -> List[Dict]:
    """Moneyline, handicap, total and team totals of one event, every line offered, one dict per outcome.
    side is home/away for ML and SPREAD (line = that side's handicap), over/under for the totals."""
    home, away = _teams(event)
    rows = []
    for odd in event.get('odds') or []:
        market = GAME_MARKETS.get(odd['marketId'])
        if market is None or odd.get('status') != 'active':
            continue
        specifiers = odd.get('specifiers') or {}
        if market == 'ML':
            side, line = {'1': 'home', '2': 'away'}.get(odd['name']), None
        elif market == 'SPREAD':
            # both outcomes carry the home handicap; the first outcome name is the home team
            home_hcp = float(specifiers['hcp'])
            side = 'home' if odd['name'].startswith(event['matchName'].split('·')[0].strip()) else 'away'
            line = home_hcp if side == 'home' else -home_hcp
        else:
            side, line = {'Over': 'over', 'Under': 'under'}.get(_over_under(odd['name'])), float(specifiers['total'])
        if side is None:
            log.warning("Unknown outcome %r in event %s", odd['name'], event['eventId'])
            continue
        team = {'home': home, 'away': away}.get(side) or {'HOME_TOTAL': home, 'AWAY_TOTAL': away}.get(market)
        rows.append({"market": market, "side": side, "line": line, "odds": odd['price'], "team": team,
                     "home": home, "away": away, "event_id": event['eventId'], "start_time": event['utcDate']})
    return rows


def main_lines(game_odds: List[Dict]) -> List[Dict]:
    """For each event and market, the line whose two prices are closest to each other (the book's main line)."""
    pairs: Dict[tuple, Dict[str, Dict]] = {}
    for row in game_odds:
        # a spread line is identified by the home handicap, so both sides of one line share a key; the
        # moneyline has no line (None, or NaN after a round trip through pandas, which never equals itself)
        line = None if row['line'] is None or row['line'] != row['line'] else row['line']
        key_line = line if row['market'] != 'SPREAD' or row['side'] == 'home' else -line
        pairs.setdefault((row['event_id'], row['market'], key_line), {})[row['side']] = row
    best: Dict[tuple, tuple] = {}
    for (event_id, market, _), sides in pairs.items():
        if len(sides) != 2:
            continue
        a, b = sides.values()
        gap = abs(a['odds'] - b['odds'])
        if (event_id, market) not in best or gap < best[(event_id, market)][0]:
            best[(event_id, market)] = (gap, [a, b])
    return [row for _, rows in best.values() for row in rows]


def todays_offers(hours_ahead: int = 36) -> Dict[str, List[Dict]]:
    """Player props and game odds of every NBA game starting in the next `hours_ahead` hours."""
    props, game_odds = [], []
    for summary in nba_events(hours_ahead):
        event = fetch_event(summary['eventId'])
        home, away = _teams(event)
        if home is None or away is None:
            log.warning("Unmapped team name in %r, skipping", event['matchName'])
            continue
        event_rows = event_props(event)
        print(f"{away.upper()} @ {home.upper()}: {len(event_rows)} player props")
        props.extend(event_rows)
        game_odds.extend(event_game_odds(event))
    return {'props': props, 'game_odds': game_odds}


def all_today_props(hours_ahead: int = 36) -> List[Dict]:
    return todays_offers(hours_ahead)['props']


if __name__ == '__main__':
    offers = todays_offers()
    for row in main_lines(offers['game_odds']):
        print(row)
    for prop in offers['props']:
        print(prop)
