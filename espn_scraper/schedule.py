from datetime import date
from typing import Dict, List

from . import client

SEASON_TYPES = {1: "pre", 2: "regular", 3: "post", 5: "playin"}


def list_games(day: date) -> List[Dict]:
    """Games ESPN lists for a given (US Eastern) calendar day."""
    data = client.scoreboard(day.strftime("%Y%m%d"))
    games = []
    for event in data.get("events", []):
        competitors = event["competitions"][0]["competitors"]
        teams = {c["homeAway"]: c["team"]["abbreviation"].lower() for c in competitors}
        status = event["status"]["type"]
        games.append({
            "game_id": event["id"],
            "date": day.isoformat(),
            "season_year": event["season"]["year"],
            "season_type": SEASON_TYPES.get(event["season"]["type"], str(event["season"]["type"])),
            "home": teams.get("home"),
            "away": teams.get("away"),
            "status": status["name"],
            "completed": status.get("completed", False),
        })
    return games
