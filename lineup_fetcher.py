# Expected/confirmed starting lineups and injury statuses from RotoWire's NBA lineups page.
import re
from datetime import datetime
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from http_polite import PoliteClient

URL = "https://www.rotowire.com/basketball/nba-lineups.php"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/126.0 Safari/537.36"}

# RotoWire team codes that differ from ESPN's (lowercased); the rest are the same
ROTOWIRE_TO_ESPN = {'GSW': 'gs', 'NOP': 'no', 'NYK': 'ny', 'SAS': 'sa', 'UTA': 'utah', 'WAS': 'wsh', 'PHO': 'phx'}


def espn_team(code: str) -> str:
    code = code.strip().upper()
    return ROTOWIRE_TO_ESPN.get(code, code.lower())


_session = requests.Session()
_session.headers.update(HEADERS)
_etags: dict = {}


def fetch_html(date: str = 'today') -> str:
    """The lineups page, fetched politely (http_polite: retries with backoff, RotoWire's block, ETag)."""
    http = PoliteClient('rotowire', _session, deadline=120, etags=_etags)
    return http.get(URL, params={'date': date} if date == 'tomorrow' else None).text


def _page_date(soup) -> Optional[str]:
    # "Starting lineups for October 20, 2026" -> "2026-10-20"
    title = soup.select_one('.page-title__secondary')
    match = re.search(r'([A-Z][a-z]+ \d{1,2}, \d{4})', title.get_text() if title else '')
    return datetime.strptime(match.group(1), '%B %d, %Y').strftime('%Y-%m-%d') if match else None


def _player(li, role: str) -> Dict:
    link = li.find('a')
    pct = re.search(r'is-pct-play-(\d+)', ' '.join(li.get('class', [])))
    rotowire_id = re.search(r'-(\d+)$', link.get('href', ''))
    injury = li.select_one('.lineup__inj')
    pos = li.select_one('.lineup__pos')
    return {'role': role,
            'pos': pos.get_text(strip=True) if pos else None,
            'name': link.get('title') or link.get_text(strip=True),
            'rotowire_id': int(rotowire_id.group(1)) if rotowire_id else None,
            'play_pct': int(pct.group(1)) if pct else None,
            'injury': injury.get_text(strip=True) if injury else None}


def parse_lineups(html: str) -> List[Dict]:
    """One row per listed player: the five starters of each side, then everyone under "MAY NOT PLAY"."""
    soup = BeautifulSoup(html, 'html.parser')
    game_date = _page_date(soup)
    rows = []
    for game in soup.select('div.lineup.is-nba'):
        if 'is-tools' in game.get('class', []):
            continue
        away = espn_team(game.select_one('.lineup__team.is-visit .lineup__abbr').get_text())
        home = espn_team(game.select_one('.lineup__team.is-home .lineup__abbr').get_text())
        tip = game.select_one('.lineup__time')
        for side, team in (('away', away), ('home', home)):
            ul = game.select_one(f"ul.lineup__list.is-{'visit' if side == 'away' else 'home'}")
            status = ul.select_one('li.lineup__status')
            status_classes = status.get('class', []) if status else []
            lineup_status = 'confirmed' if 'is-confirmed' in status_classes else \
                'expected' if 'is-expected' in status_classes else None
            role = 'starter'
            for li in ul.find_all('li', recursive=False):
                classes = li.get('class', [])
                if 'lineup__title' in classes:   # "MAY NOT PLAY"
                    role = 'may_not_play'
                elif 'lineup__player' in classes and li.find('a'):
                    rows.append({'game_date': game_date, 'tip_et': tip.get_text(strip=True) if tip else None,
                                 'away': away, 'home': home, 'team': team, 'side': side,
                                 'lineup_status': lineup_status, **_player(li, role)})
    return rows


def parse_game_lines(html: str) -> List[Dict]:
    """The moneyline, spread and total RotoWire shows for each game (FanDuel's by default)."""
    soup = BeautifulSoup(html, 'html.parser')
    rows = []
    for game in soup.select('div.lineup.is-nba'):
        if 'is-tools' in game.get('class', []):
            continue
        row = {'away': espn_team(game.select_one('.lineup__team.is-visit .lineup__abbr').get_text()),
               'home': espn_team(game.select_one('.lineup__team.is-home .lineup__abbr').get_text())}
        for item in game.select('.lineup__odds-item'):
            label = item.find('b').get_text(strip=True).lower().replace('o/u', 'total')
            shown = next((s for s in item.find_all('span') if 'hide' not in s.get('class', [])), None)
            row[label] = shown.get_text(strip=True) if shown else None
        rows.append(row)
    return rows


def fetch_lineups(date: str = 'today') -> List[Dict]:
    return parse_lineups(fetch_html(date))


def players_unlikely_to_play(lineups: Optional[List[Dict]] = None) -> List[Dict]:
    """Players listed under "MAY NOT PLAY" with less than a 100% chance to play. team is ESPN's abbreviation."""
    lineups = fetch_lineups() if lineups is None else lineups
    return [{'name': p['name'], 'team': p['team'], 'likelihood': p['play_pct']}
            for p in lineups if p['role'] == 'may_not_play' and p['play_pct'] is not None and p['play_pct'] < 100]


if __name__ == "__main__":
    html = fetch_html()
    for game in parse_game_lines(html):
        print(game)
    for player in parse_lineups(html):
        print(player)
