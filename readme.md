# nba-stats

Tools for NBA player-prop betting analysis. The project:

1. **Scrapes player statistics** from ESPN: every game of the 2026/27 season and each player's box-score line.
2. **Fetches bookmaker offers**: over/under player lines from Superbet.
3. **Compares the two**: checks where a bookmaker's line sits within a player's recent results, and scores bets with a set of statistical rules.

## Contents

| Path | What it does |
|---|---|
| `espn_scraper/` | Scrapes games and player game logs from ESPN's JSON API into `data/<season>/` (2024/25, 2025/26 and the current 2026/27). Run on demand; only new games are added. |
| `superbet_fetcher.py` | Fetches today's NBA over/under player props from Superbet (PTS, AST, REB, 3PM, PTS+AST, PTS+REB). |
| `betfinder.py` | Takes today's Superbet props and checks whether each line falls between the player's 30th and 70th percentile. |
| `bet_analyst.py` | Rule engine (`BetAssessment`): each rule votes Over or Under for a bet. Also resolves past offers against actual results. |
| `bet_analizator.py` | Helpers for loading game logs (`game_players`, `all_nba_players`, `NBA_TEAMS`) and older percentile analysis. |
| `bet_fetcher.py`, `bet_scrapper.py` | Unibet/Kambi offer fetchers. Unibet's feed currently doesn't respond (see [Known limitations](#known-limitations)). |
| `lineup_fetcher.py` | Players unlikely to play, scraped from RotoWire's lineups page. |
| `mappings.py`, `team_abbr.json` | Team and player name mappings between data sources. |
| `nba2024/` | Older Selenium-based Superbet crawler. Superseded by `superbet_fetcher.py`. |
| `Untitled6.ipynb` | Old analysis notebook. It imports modules that no longer exist, so it no longer runs. |

### Data files

| File | Content |
|---|---|
| `data/<season>/games.csv` | One row per game: date, season type, teams, score, team totals. Seasons are named by their start year: `data/2024` = 2024/25, `data/2025` = 2025/26, `data/2026` = 2026/27. |
| `data/<season>/player_gamelogs.csv` | One row per player per game (players who didn't play are skipped). |
| `2022-players-logs.csv` | Player game logs from earlier seasons, same columns. |
| `offers.csv`, `offers_resolved.csv`, `assessed_bets.csv`, `bets.csv` | Historical bookmaker offers, their results and rule assessments. |
| `season_ratings/` | Team ratings for seasons 2018–2022. |

`player_gamelogs.csv` uses the same columns, in the same order, as `2022-players-logs.csv`:

```
OPP, Result, MIN, FG%, 3P%, FT%, REB, AST, BLK, STL, PF, TO, PTS, FGM, FGA, 3PM, 3PA, FTM, FTA,
type, Date, season_id, player_id_ESPN, player_name_ESPN, team,
game_id, season_type, starter, position, OREB, DREB, PLUS_MINUS, player_display_name
```

- `player_name_ESPN` has no spaces (`RJBarrett`, `JarenJacksonJr.`). This is the key used to match bookmaker names to game logs.
- `team` is a lowercase ESPN abbreviation (`bos`, `gs`, `utah`); `OPP` is the opponent in uppercase.
- `Result` is from the player's team's point of view, e.g. `L106-144`.
- `type` is `home` or `away`.
- `season_id` is the year the season starts (`2026` for 2026/27).
- `season_type` is `pre`, `regular`, `playin`, `post` or `allstar`. ESPN labels All-Star games as regular season; the scraper tags them `allstar` so they don't mix into regular-season stats.

## Installation

Requires Python 3.11 or newer.

```
pip install -r requirements.txt
```

`pandasgui` is only needed by `bet_analyst.py` and `betfinder.py`, which use it to show results in a table window. The scrapers don't need it.

The old Selenium crawler in `nba2024/` has its own `nba2024/requirements.txt`.

## Usage

All commands are run from the repository root.

### 1. Update player statistics

```
python -m espn_scraper
```

This adds every finished game of the current season (2026/27) that isn't stored yet, then prints a summary:

```
2026/27: added 7 games, 202 player lines. 12 games not final yet.
```

- Games that haven't finished are skipped and picked up on the next run.
- `data/<season>/checked_through.txt` records the last date up to which every game is stored. Each run starts from the day after it, so a daily update takes a few seconds.
- Running it twice in a row is safe; nothing is duplicated.
- If ESPN's game summary returns 404 (it happens for a few games), the box score is rebuilt from ESPN's core API instead (`espn_scraper/core_api.py`). This is slower, about a minute per game, but gives the same data.
- Postponed and cancelled games are skipped; a makeup game is picked up on the date it's actually played.
- Players ESPN lists without an id or name are skipped with a warning, so in those games the players' points don't add up to the team score.

Other options:

```
python -m espn_scraper --season 2025                           # a past season (2025/26); seasons are named by start year
python -m espn_scraper --since 2026-10-01 --until 2026-10-15   # check a specific date range
python -m espn_scraper --game 401898398                        # re-scrape one game (ESPN game id), any season
python -m espn_scraper --rebuild                               # delete the season's data and scrape it again
python -m espn_scraper -v                                      # verbose: also log players who didn't play, with the reason
```

Dates are US Eastern dates, the same ones ESPN uses for its schedule. `--since`, `--until` and `--rebuild` apply to the season chosen with `--season` (default: current).

To add a new season, add its start year and ESPN calendar dates to `SEASONS` in `espn_scraper/__init__.py`, and update `CURRENT_SEASON`.

### 2. See today's Superbet offers

```
python superbet_fetcher.py
```

Prints each NBA game starting in the next 36 hours with its number of player props, then every prop:

```
{'name': 'Barrett, RJ', 'name_ESPN': 'RJBarrett', 'odds': 1.87, 'line': 18.5, 'over_under': 'Over',
 'home': 'tor', 'away': 'lac', 'bet_type': 'PTS', ...}
```

### 3. Check today's lines against the statistics

Update the statistics first (step 1), then:

```
python betfinder.py
```

For each line it prints whether the line falls between the player's 30th and 70th percentile, and how many games that's based on:

```
       RJBarrett PR betline: 24.5  is_in_percentiles:True (23.4 - 26.6, 3 games)
```

A line outside that range is more interesting: the bookmaker's line is unusually low or high compared with the player's results. "no gamelogs found" means the player has no games in the data yet, or their Superbet name maps to a different ESPN name.

### 4. Use the data in your own code

```python
import pandas as pd
from bet_analizator import all_nba_players, game_players

logs = all_nba_players()                     # all players of the 30 NBA teams
regular = logs[logs['season_type'] == 'regular']
celtics_vs_sixers = game_players('bos', 'phi')

# the analysis code uses the current season; load past seasons explicitly
from espn_scraper.storage import load_player_gamelogs
three_seasons = load_player_gamelogs([2024, 2025, 2026])

from betfinder import check_bet
print(check_bet({'name_ESPN': 'RJBarrett', 'home': 'tor', 'away': 'lac',
                 'bet_type': 'PTS', 'line': 18.5}))
```

### 5. Rule-based assessment (`bet_analyst.py`)

`BetAssessment` scores a bet with these rules, using only games played before the bet closed:

- **Quantiles**: is the line below the player's 20th/30th/40th percentile, or above the matching upper one?
- **Median**: is the line far from the median or a trimmed mean?
- **Last games**: did the player go over/under the line in 6 of the last 8, 4 of 5, or 2 of 2 games?
- **Averages**: how far is the 2-game and 5-game average from the line?
- **Trend**: average change over the last 5 games.
- **Bet history**: have this player's Overs or Unders hit more than 65% of the time?
- **Info**: doubtful players in the game (from RotoWire).

A player needs at least 4 games before any rule votes. Each rule adds a column to the bet, so you can filter for bets where several rules agree:

```python
from bet_analyst import BetAssessment

bet = {'player_ESPN': 'RJBarrett', 'bet_type': 'PTS', 'odds': 1.9, 'line': 18.5,
       'over_under': 'Over', 'home': 'tor', 'away': 'lac', 'bet_id': 1,
       'closed_date': '2026-10-25T00:00:00Z'}
assessment = BetAssessment([bet])
print(assessment.assess_bets_from_list([bet]))
```

Creating `BetAssessment` fetches RotoWire's lineups page, so it needs an internet connection. Running `python bet_analyst.py` directly uses Unibet as its source of offers, which doesn't work at the moment.

## Known limitations

- **No NBA player props during preseason.** Superbet lists the preseason games but only offers game-level markets for them, so `betfinder.py` reports 0 offers until props appear. The prop market IDs in `superbet_fetcher.py` (`PLAYER_MARKETS`) were taken from EuroLeague games. If the regular season shows 0 props while Superbet's website shows player bets, those IDs need updating.
- **PTS+REB+AST isn't fetched from Superbet.** It's only offered as "X+" milestones there, not as an over/under line.
- **Unibet doesn't respond.** `bet_fetcher.py` and `bet_scrapper.py` time out, so `bet_analyst.py`'s "analyze today" mode can't get offers.
- **Name mismatches.** Bookmaker names are converted to ESPN's format automatically ("Jackson Jr., Jaren" → `JarenJacksonJr.`). Names spelled differently at the two sources (nicknames, missing suffixes) need an entry in the mapping dict in `bet_analyst.py`.
- **Small samples early in the season.** Percentiles from 2–3 preseason games say little. Filter on `season_type == 'regular'` once the regular season has enough games.

## Notes and ideas

- zapisuj graczy po id i name
- jak przechowywać dane
- against_players - forward+center i guards liczeni osobno

|kto | przeciwko komu | data | pts | ...(reszta statsów z meczu) | [against_players] |

algorytmy
