"""On-demand ESPN NBA scraper: game results and player game logs via ESPN's JSON API."""

SEASON_ID = 2026            # season start year, as used in season_id of the player-logs CSVs
ESPN_SEASON_YEAR = 2027     # ESPN labels the 2026/27 season by its end year
SEASON_START = "2026-09-30"
SEASON_END = "2027-06-26"
DATA_DIR = f"data/{SEASON_ID}"
