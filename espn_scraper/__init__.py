"""On-demand ESPN NBA scraper: game results and player game logs via ESPN's JSON API."""
import json
import os

# season start year (season_id in the player-logs CSVs) -> (first day, last day) of ESPN's season calendar
SEASONS = {
    2024: ("2024-09-24", "2025-06-27"),
    2025: ("2025-10-01", "2026-06-27"),
    2026: ("2026-09-30", "2027-06-26"),
}
CURRENT_SEASON = 2026

# lowercase ESPN abbreviations of the 30 NBA teams
with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "team_abbr.json")) as _f:
    NBA_TEAM_ABBRS = frozenset(json.load(_f).values())


def team_code(team: dict) -> str:
    """Lowercase ESPN team abbreviation. Some foreign exhibition clubs have none; use their name instead."""
    return (team.get("abbreviation") or team.get("displayName") or team["id"]).replace(" ", "").lower()


def espn_year(season: int) -> int:
    # ESPN labels a season by the year it ends in (2026/27 -> 2027)
    return season + 1


def data_dir(season: int) -> str:
    return f"data/{season}"
