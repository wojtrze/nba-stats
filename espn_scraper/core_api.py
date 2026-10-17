"""Fallback for games whose site-API summary returns 404: rebuild the same summary shape
from ESPN's core API (sports.core.api.espn.com), so boxscore.parse_summary can parse it.
It takes about 70 requests per game instead of 1, so it's only used when the summary is missing."""
import logging
import re
from typing import Dict

from . import client

CORE_URL = "https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba"

log = logging.getLogger(__name__)

# made-attempted pairs as the site API names them -> core API stat names
MADE_ATTEMPTED = {'fieldGoalsMade-fieldGoalsAttempted': ('fieldGoalsMade', 'fieldGoalsAttempted'),
                  'threePointFieldGoalsMade-threePointFieldGoalsAttempted': ('threePointFieldGoalsMade',
                                                                             'threePointFieldGoalsAttempted'),
                  'freeThrowsMade-freeThrowsAttempted': ('freeThrowsMade', 'freeThrowsAttempted')}
PLAYER_KEYS = ['minutes', 'points', 'rebounds', 'offensiveRebounds', 'defensiveRebounds', 'assists', 'steals',
               'blocks', 'turnovers', 'fouls', 'plusMinus'] + list(MADE_ATTEMPTED)
TEAM_KEYS = ['offensiveRebounds', 'defensiveRebounds', 'totalRebounds', 'assists', 'steals', 'blocks',
             'totalTurnovers', 'fouls']


def _get(ref: str) -> dict:
    return client.get_url(ref.replace("http://", "https://"))


def _stats(ref: str) -> Dict[str, str]:
    """Flatten a core-API statistics response into {name: whole-number string}."""
    stats = {}
    for category in _get(ref)["splits"]["categories"]:
        for s in category["stats"]:
            stats.setdefault(s["name"], str(int(s.get("value") or 0)))
    for site_name, (made, attempted) in MADE_ATTEMPTED.items():
        stats[site_name] = f"{stats.get(made, '0')}-{stats.get(attempted, '0')}"
    return stats


def _season(ref: str) -> int:
    return int(re.search(r"/seasons/(\d+)", ref).group(1))


def _season_type(ref: str) -> int:
    return int(re.search(r"/types/(\d+)", ref).group(1))


def summary(game_id: str) -> dict:
    event = _get(f"{CORE_URL}/events/{game_id}")
    competition = event["competitions"][0]
    status = _get(competition["status"]["$ref"]) if "$ref" in competition.get("status", {}) else \
        _get(f"{CORE_URL}/events/{game_id}/competitions/{game_id}/status")

    competitors, teams, players = [], [], []
    for c in competition["competitors"]:
        team = _get(c["team"]["$ref"])
        score = _get(c["score"]["$ref"])["displayValue"]
        competitors.append({"homeAway": c["homeAway"], "team": team, "score": score})

        team_stats = _stats(c["statistics"]["$ref"])
        teams.append({"homeAway": c["homeAway"], "team": team,
                      "statistics": [{"name": k, "displayValue": team_stats.get(k, "0")}
                                     for k in list(MADE_ATTEMPTED) + TEAM_KEYS]})

        athletes = []
        for entry in _get(c["roster"]["$ref"])["entries"]:
            info = _get(entry["athlete"]["$ref"])
            athlete = {"athlete": {"id": info["id"], "displayName": info["displayName"],
                                   "position": {"abbreviation": info.get("position", {}).get("abbreviation", "")}},
                       "starter": entry.get("starter", False), "reason": entry.get("reason", "")}
            s = _stats(entry["statistics"]["$ref"]) if "statistics" in entry else {}
            # the roster's didNotPlay/active flags are unreliable here; gamesPlayed/minutes aren't
            if s.get("gamesPlayed", "0") == "0" and s.get("minutes", "0") == "0":
                athlete.update(didNotPlay=True, stats=[])
            else:
                athlete.update(didNotPlay=False, stats=[s.get(k, "0") for k in PLAYER_KEYS])
            athletes.append(athlete)
        players.append({"team": team, "statistics": [{"keys": PLAYER_KEYS, "athletes": athletes}]})

    log.info("Rebuilt game %s from the core API", game_id)
    return {
        "header": {
            "id": str(game_id),
            "season": {"year": _season(event["season"]["$ref"]), "type": _season_type(event["seasonType"]["$ref"])},
            "competitions": [{"date": event["date"], "status": {"type": status["type"]},
                              "competitors": competitors}],
        },
        "boxscore": {"teams": teams, "players": players},
    }
