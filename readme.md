# nba-stats

Tools for NBA player-prop betting analysis. The project:

1. **Scrapes player statistics** from ESPN: every game of the 2026/27 season and each player's box-score line.
2. **Fetches bookmaker offers**: over/under player lines from Superbet.
3. **Compares the two**: checks where a bookmaker's line sits within a player's recent results, and scores bets with a set of statistical rules.

## Contents

| Path | What it does |
|---|---|
| `espn_scraper/` | Scrapes games and player game logs from ESPN's JSON API into `data/<season>/` (2024/25, 2025/26 and the current 2026/27). Run on demand; only new games are added. |
| `dashboard/` | Browser dashboard (Streamlit): today's props, games, player deep-dive, lineup lab, teams & matchups, rule backtest, data status. |
| `superbet_fetcher.py` | Fetches Superbet's NBA offers for the next 36 hours: over/under player props (PTS, REB, AST, 3PM, PA, PR, RA, PRA, STL, BLK, TO, FGM/FGA, FTM/FTA, 3PA, PF) and game markets (moneyline, handicap, total, team totals). |
| `lineup_fetcher.py` | Expected/confirmed starting fives and "may not play" players (with chance to play and injury tag) from RotoWire's lineups page. |
| `daily_snapshot.py` | Appends today's RotoWire lineups and Superbet offers to `data/<season>/` with a timestamp. |
| `name_resolver.py` | Matches RotoWire and Superbet player names to ESPN player ids. |
| `betfinder.py` | Takes today's Superbet props and checks whether each line falls between the player's 30th and 70th percentile. |
| `bet_analyst.py` | Rule engine (`BetAssessment`): each rule votes Over or Under for a bet. Also resolves past offers against actual results. |
| `bet_analizator.py` | Helpers for loading game logs (`game_players`, `all_nba_players`, `NBA_TEAMS`) and older percentile analysis. |
| `bet_fetcher.py`, `bet_scrapper.py` | Unibet/Kambi offer fetchers. Unibet's feed currently doesn't respond (see [Known limitations](#known-limitations)). |
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
| `data/<season>/rotowire_lineups.csv` | RotoWire snapshots: one row per listed player (starter or may-not-play) with `fetched_at`. |
| `data/<season>/superbet_props.csv` | Superbet player lines with over and under odds, one row per line and snapshot. |
| `data/<season>/superbet_game_odds.csv` | Superbet game markets, every line offered, one row per outcome and snapshot. |

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
- ESPN sometimes lists a player without id, name or stats (e.g. Lachlan Olbrich on a two-way contract in 2025/26). The scraper then rebuilds the line from the play-by-play, which tags the player's plays with their id (`espn_scraper/play_by_play.py`). Checked against real box scores, minutes, points, rebounds, assists, steals, blocks, turnovers and free throws match exactly; shot attempts are occasionally off by one and plus-minus by 1–3. Position isn't available for those rows. If the play-by-play doesn't have the player either, the line is skipped with a warning and that game's player points won't add up to the team score.

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

### 2. Dashboard in the browser

```
streamlit run dashboard/app.py
```

Opens `http://localhost:8501` with seven pages:

- **Today's props:** every Superbet line for the next 36 hours next to the player's average, hit rate over/under the line (season and last 10), where the line sits in their results, and the edge versus the odds' implied probability. The RotoWire column shows tonight's role (starter, bench, or injury tag with chance to play; ✔ = confirmed lineup), and `adj avg` adds the player's usual change when RotoWire's out teammates miss games. Players RotoWire lists as out are hidden by default. Click a row to open the player. A line checker works even when Superbet has no props (preseason).
- **Games:** Superbet's moneyline, handicap, total and team totals for each game next to a projection: offensive/defensive rating and pace (this season blended with last season, which is first pulled 30% toward the league average), home court, and how each team scores and allows points without the players RotoWire lists as out. Shows the model's chance, the odds' implied chance and the edge for every outcome, plus both RotoWire lineups.
- **Player:** game-log chart with the line and a 5-game average, hit rates, splits (home/away, starter/bench, back-to-back, minutes), results against each opponent, and with/without a chosen teammate.
- **Lineup lab:** pick a team's starting five and who's out (default: RotoWire's projected lineup and out players for teams playing today; otherwise their last game's starters, or the most frequent starters of the last 10 games). A heatmap shows how each player's stat changes when each rotation teammate doesn't play; the scenario table turns the absences into an estimate per player (the exact-match average from games with the same starters and absences, plus a sample-size-weighted estimate).
- **Teams & matchups:** points/rebounds/assists each defense allows to guards, forwards and centers compared with the league average, plus offensive/defensive ratings and pace.
- **Rule backtest:** how `bet_analyst.py`'s rules did on the stored 2022/23 bets (`assessed_bets.csv`): hit rate and ROI per rule, by number of agreeing rules, by rule combination (with confidence intervals), by odds and bet type.
- **Data status:** stored games per season, an "Update stats" button that runs the scraper, the RotoWire/Superbet snapshot files with a "Take snapshot now" button, today's names that don't match an ESPN player, and data-quality checks.

The sidebar picks the seasons and game types (preseason, regular, play-in, playoffs) the pages use. Unit tests: `python -m pytest dashboard tests` (the feed parsers are tested against pages saved in `tests/fixtures/`).

### 3. See today's Superbet offers and RotoWire lineups

```
python superbet_fetcher.py
python lineup_fetcher.py
```

`superbet_fetcher.py` prints each NBA game starting in the next 36 hours with its number of player props, the main line of each game market, then every prop:

```
{'name': 'Barrett, RJ', 'name_ESPN': 'RJBarrett', 'odds': 1.87, 'line': 18.5, 'over_under': 'Over',
 'home': 'tor', 'away': 'lac', 'bet_type': 'PTS', ...}
```

`lineup_fetcher.py` prints RotoWire's game lines, then every listed player:

```
{'game_date': '2026-10-20', 'tip_et': '3:00 PM ET', 'away': 'bos', 'home': 'det', 'team': 'bos', 'side': 'away',
 'lineup_status': 'expected', 'role': 'starter', 'pos': 'PG', 'name': 'Derrick White', 'rotowire_id': 4195,
 'play_pct': 100, 'injury': None}
```

To keep a record of lines and lineups (for line movement and for checking bets later), save a snapshot:

```
python daily_snapshot.py              # appends to data/<season>/rotowire_lineups.csv, superbet_props.csv, superbet_game_odds.csv
python daily_snapshot.py --tomorrow   # RotoWire's lineups for tomorrow
```

Each run adds rows with a `fetched_at` time, so running it a few times a day (morning, an hour before tip-off) keeps the changes. If RotoWire or Superbet can't be reached, the dashboard falls back to the latest snapshot.

### 4. Check today's lines against the statistics

Update the statistics first (step 1), then:

```
python betfinder.py
```

For each line it prints whether the line falls between the player's 30th and 70th percentile, and how many games that's based on:

```
       RJBarrett PR betline: 24.5  is_in_percentiles:True (23.4 - 26.6, 3 games)
```

A line outside that range is more interesting: the bookmaker's line is unusually low or high compared with the player's results. "no gamelogs found" means the player has no games in the data yet, or their Superbet name maps to a different ESPN name.

### 5. Use the data in your own code

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

### 6. Rule-based assessment (`bet_analyst.py`)

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

- **No NBA player props during preseason.** Superbet lists the preseason games but only offers game-level markets for them, so `betfinder.py` reports 0 offers until props appear.
- **Superbet IDs can change.** The NBA's tournament id changed from 2176 to 164 for 2026/27. If `superbet_fetcher.py` finds no games while Superbet's website shows them, check `NBA_TOURNAMENT_ID`; market ids are in `PLAYER_MARKETS` and `GAME_MARKETS`.
- **The game model is simple.** Early in the season it's mostly last season's ratings, which don't know about summer trades, and absences only count when the team has played without that player before. Treat large edges as a prompt to look closer, not as a bet.
- **RotoWire players without a game** (rookies, players injured all last season) can't be matched to an ESPN id and don't enter the absence adjustments; the Data status page lists them.
- **Unibet doesn't respond.** `bet_fetcher.py` and `bet_scrapper.py` time out, so `bet_analyst.py`'s "analyze today" mode can't get offers.
- **Name mismatches.** Bookmaker names are converted to ESPN's format automatically ("Jackson Jr., Jaren" → `JarenJacksonJr.`). Names spelled differently at the two sources (nicknames, missing suffixes) need an entry in the mapping dict in `bet_analyst.py`.
- **Small samples early in the season.** Percentiles from 2–3 preseason games say little. Filter on `season_type == 'regular'` once the regular season has enough games.

## Notes and ideas

- zapisuj graczy po id i name
- jak przechowywać dane
- against_players - forward+center i guards liczeni osobno

|kto | przeciwko komu | data | pts | ...(reszta statsów z meczu) | [against_players] |

algorytmy
