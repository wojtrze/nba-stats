from datetime import date
from typing import Dict, List

from . import NBA_TEAM_ABBRS, client, team_code

SEASON_TYPES = {1: "pre", 2: "regular", 3: "post", 5: "playin"}


def season_type_name(espn_type: int, home: str, away: str) -> str:
    """ESPN season type as a name. All-Star games (non-NBA teams outside preseason) get 'allstar'."""
    name = SEASON_TYPES.get(espn_type, str(espn_type))
    if name != "pre" and (home not in NBA_TEAM_ABBRS or away not in NBA_TEAM_ABBRS):
        return "allstar"
    return name


def list_games(day: date) -> List[Dict]:
    """Games ESPN lists for a given (US Eastern) calendar day."""
    data = client.scoreboard(day.strftime("%Y%m%d"))
    games = []
    for event in data.get("events", []):
        competitors = event["competitions"][0]["competitors"]
        teams = {c["homeAway"]: team_code(c["team"]) for c in competitors}
        status = event["status"]["type"]
        games.append({
            "game_id": event["id"],
            "date": day.isoformat(),
            "season_year": event["season"]["year"],
            "season_type": season_type_name(event["season"]["type"], teams.get("home"), teams.get("away")),
            "home": teams.get("home"),
            "away": teams.get("away"),
            "status": status["name"],
            "completed": status.get("completed", False),
        })
    return games
