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
| `backtest/` | Backtest of the props model on Unibet's 2022/23 lines (`offers_resolved.csv`, `2022-players-logs.csv`). |
| `dashboard_v2/` | Second version of the dashboard, organised by task: tonight, research, review, data. Uses `dashboard/`'s models and calculations; `dashboard/` is unchanged. |
| `superbet_fetcher.py` | Fetches Superbet's NBA offers for the next 36 hours: over/under player props (PTS, REB, AST, 3PM, PA, PR, RA, PRA, STL, BLK, TO, FGM/FGA, FTM/FTA, 3PA, PF) and game markets (moneyline, handicap, total, team totals). |
| `lineup_fetcher.py` | Expected/confirmed starting fives and "may not play" players (with chance to play and injury tag) from RotoWire's lineups page. |
| `daily_snapshot.py` | Appends today's RotoWire lineups and Superbet offers to `data/<season>/` with a timestamp, plus the dashboard's pick and edge for every line, so the results tracker can settle them later. |
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
| `data/backtest/2022_lines.csv`, `2022_summary.md` | The props model's backtest on Unibet's 2022/23 lines (`python -m backtest.run`): every line priced and settled, and the summary tables. |
| `data/<season>/rotowire_lineups.csv` | RotoWire's lineups page: one row per listed player (starter or may-not-play) with `fetched_at`. Written by snapshot runs, and by the dashboards whenever a fetch differs from the last saved version of that day (confirmed lineups, late scratches, changed chances to play). |
| `data/<season>/superbet_props.csv` | Superbet player lines with over and under odds, one row per line and snapshot. |
| `data/<season>/superbet_game_odds.csv` | Superbet game markets, every line offered, one row per outcome and snapshot. |
| `data/<season>/superbet_props_replay.csv` | Every saved Superbet line priced again as of its fetch (`python daily_snapshot.py --reprice`), one block of rows per `model_version`, so several models can be compared on the same lines. A reprice replaces only the current version's block; `superbet_props.csv` is never changed by it. |
| `data/<season>/superbet_props_recorded_legacy.csv` | The model's numbers as each fetch first saved them, recovered from git (`python scripts/recover_recorded_predictions.py`), because before Oct 26 `--reprice` overwrote them in `superbet_props.csv`. The Oct 20 fetch was saved before picks were, so its rows are `historical_replay`. |
| `data/<season>/my_bets.csv` | Bets saved from the dashboard's bet slip: what, at which odds, the stake, and the model's chance and edge at the time. |
| `data/run_log.csv` | One row per scraper run started from dashboard v2's Data center and per Superbet fetch from either dashboard: time, job (`stats`, `snapshot`, `fetch`), command, exit code, duration and a summary (for a fetch: what was saved, or why it failed). Scheduled runs aren't logged; the Superbet card shows the last saved fetch from the data itself. |

Snapshots taken with this version also store the model's view of each line: `player_id_ESPN`, `pick` (the best side, even without an edge, so every line can be judged; the dashboards only show it as a pick with 🟢/🟡), `model_pct`, `edge_pp`, `edge_low`, `proj_avg`, `signal` (🟢/🟡/🔴), `red_flag` and the uncalibrated chances `raw_over_pct`, `raw_under_pct`, `market_over_pct` (what the calibration is refitted from) for props, `model_pct`, `edge_pp` and the game's projected score (`proj_home_pts`, `proj_away_pts`) for game outcomes. From Oct 26 every priced row also says what priced it: `model_version` (`nightly.MODEL_VERSION`, bumped whenever the pricing changes), `calibration_id` (a fingerprint of the calibration in use, props only) and `prediction_origin` (`recorded_live` for what the fetch itself saved, `historical_replay` for lines priced later). Older rows leave the newer columns empty.

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

Opens `http://localhost:8501` with eight pages. Superbet blocks frequent requests, so the dashboard never fetches it on its own: it's fetched when you press **Fetch from Superbet** (on Today's props and Games) or take a snapshot, at most once every 5 minutes (the buttons are greyed out until then). **Every fetch is saved** to `superbet_props.csv` / `superbet_game_odds.csv` with the dashboard's pick for every line, so it's still there after a restart. The pages use the newest fetch: its games that haven't tipped off, earliest first (⏰ marks a tip-off within the hour); a game leaves the pages at tip-off. When every game of the last fetch has tipped off, Today's props and Games say so (when it was fetched, how many lines, which night), ask for a new fetch, and link to *Bet slip & results → Previous night*: the same night overview as in dashboard v2 (`dashboard/night_view.py`, numbers from `dashboard/nightly.py`).

- **Today's props:** every Superbet line for the next 36 hours next to the player's average, hit rate over/under the line (season and last 10) and where the line sits in their results. The RotoWire column shows tonight's role (starter, bench, or injury tag with chance to play; ✔ = confirmed lineup); `adj avg` adds the player's usual change when RotoWire's out teammates miss games, and `proj avg` also scales it by the game (Superbet's implied team total vs the team's usual points) and the matchup (what the opponent allows to the player's position), each damped to half and capped at ±8%. Players RotoWire lists as out are hidden by default.
  - **The edge** is the model's chance minus the break-even chance of the odds (1 / odds). The model's chance averages two estimates, both pulled toward Superbet's margin-free chance as if the market were worth 10 games: the player's hit rate, and the chance from `proj avg` and their usual spread of results. That chance (`raw model %`) is then **calibrated** on the 2022/23 backtest and every settled Superbet line (see section 7): it was overconfident, and the calibration keeps only as much of it as held up, so `model %` sits close to the market's margin-free chance and few lines show an edge. **pick** is Over or Under only where the edge is positive (🟢/🟡); every other line is a *pass* (`best side`, the less bad side, is still shown). **lean** says which way `proj avg` points when it's at least 10% off the line, for information only. 🟢 = an edge at least as big as the threshold whose picks beat break-even on 10+ unseen Superbet nights, even at the low end of their range (`green_edge_pp` in the calibration; no threshold = no 🟢), 🟡 = any other positive estimated edge (not validated). 🔴 = a reason to pass whatever the numbers say, named in the `red flag` column: fewer than 8 games, preseason only, may not play (RotoWire), minutes swinging a lot, or the line moving 1.5+ against the pick. 🔴 lines are listed after the others. On Games, 🔴 marks a market with a red flag (early season, no RotoWire lineup yet, an edge over 15 pp). Game outcomes get no 🟢/🟡, no Bet/Lean verdict and no stake: the game model isn't calibrated, and on the first settled nights it predicted worse than the margin-free price and was overconfident (its old +5 pp 🟢 picks expected 68% and won 55%; see the game section of `data/backtest/calibration.md`). Its edges are estimates for research until a calibration is fitted (300+ settled main-line outcomes on 10+ nights). The flags are the same ones that make the Bet/Lean/Pass verdict say Pass.
  - **Click a row** for the reasons to bet or pass: ✅ for / ❌ against with their numbers (price, recent and season hit rate, expected vs line, minutes trend, teammates out, home/away, back-to-back, matchup, record against the opponent, game total, blowout risk, line movement), red flags that alone mean pass (fewer than 8 games, preseason only, questionable, unstable minutes, line moved against the pick), a **Bet / Lean / Pass** verdict, the last 10 games against the line, and buttons to add it to the bet slip or open the player.
  - `line move` / `open line`: the change since the first snapshot. A line checker works even when Superbet has no props (preseason).
- **Games:** Superbet's moneyline, handicap, total and team totals for each game next to a projection: offensive/defensive rating and pace (this season blended with last season, which is first pulled 30% toward the league average), home court, and how each team scores and allows points without the players RotoWire lists as out. Shows the model's chance, the odds' implied chance and the edge for every outcome, how the odds and main lines moved since the first snapshot, and both RotoWire lineups. Each game shows the reasons for and against its best bet (or the market row you click) with a verdict, and can add it to the bet slip.
- **Player:** game-log chart with the line and a 5-game average, hit rates, splits (home/away, starter/bench, back-to-back, minutes), results against each opponent, and with/without a chosen teammate.
- **Lineup lab:** pick a team's starting five and who's out (default: RotoWire's projected lineup and out players for teams playing today; otherwise their last game's starters, or the most frequent starters of the last 10 games). A heatmap shows how each player's stat changes when each rotation teammate doesn't play; the scenario table turns the absences into an estimate per player (the exact-match average from games with the same starters and absences, plus a sample-size-weighted estimate).
- **Teams & matchups:** points/rebounds/assists each defense allows to guards, forwards and centers compared with the league average, plus offensive/defensive ratings and pace.
- **Bet slip & results:** the bets you added, with a suggested stake (a quarter Kelly by default, at most 5% of the bankroll; props are sized on the low end of the model's range, so a thin edge gets less; game outcomes and props without a valid calibration get no suggested stake) and warnings about bets that win or lose together (one player, several Overs in one game, both sides of a line, too much of the bankroll on one night). "Save as placed" writes them to `my_bets.csv`. *My bets* settles them against the stored stats (profit, ROI, closing line value); *Dashboard's picks* settles every snapshotted line with the pick the dashboard showed then, by signal, edge, bet type, side and market, with a calibration chart (does a 60% pick win 60% of the time?). *Signal efficiency* shows every pick whose edge reached +0, 1, 2, 3 and 5 pp, with the chance the model expected next to how often it won: an accurate signal wins about as often as it said.
- **Rule backtest:** how `bet_analyst.py`'s rules did on the stored 2022/23 bets (`assessed_bets.csv`): hit rate and ROI per rule, by number of agreeing rules, by rule combination (with confidence intervals), by odds and bet type.
- **Data status:** stored games per season, an "Update stats" button that runs the scraper, the RotoWire/Superbet snapshot files with a "Take snapshot now" button, today's names that don't match an ESPN player, and data-quality checks.

Every table marks where each column comes from, with an icon in the header and a matching tint on the column: 💰 orange = Superbet, 📋 blue = RotoWire, 📊 green = calculated from the scraped ESPN stats (including edges that compare those numbers with Superbet's odds). Hover a header for what the number means. The columns that decide a bet (pick, edge, odds) come first after the player, bet and line; the rest are grouped by source. Sources and their colours are defined in `dashboard/glossary.py` (`SOURCES`), so a new data source is one entry there.

The sidebar picks the seasons and game types (preseason, regular, play-in, playoffs) the pages use; preseason is left out by default (starters play short minutes), and on the props pages a player with fewer than 10 games this season is topped up with his latest games of last season. Unit tests: `python -m pytest dashboard tests` (the feed parsers are tested against pages saved in `tests/fixtures/`).

### 2b. Dashboard v2

```
streamlit run dashboard_v2/app.py --server.port 8502
```

The same data and models as the dashboard above, laid out around the daily workflow. Both can run at the same time (the old one on port 8501). Every page has the same shape: a title with one line on what it answers, one row of filters, key numbers, one main table, and the selected row's details in tabs. The sidebar always shows how fresh the data is: 🟢 / 🟠 / 🔴 for the ESPN stats (stored through yesterday?), Superbet's odds and RotoWire's lineups (fetched or read from a snapshot, and how long ago), with a link to the Data center when something is out of date. The *Scope* button in the header picks the seasons and game types for every page.

- **Tonight**
  - **Overview:** tonight's games as cards (tip-off in Polish time, Superbet's moneyline, handicap and total, the projected winner and the best-priced bet, each team's RotoWire lineup status and who's out), the 10 best player lines and the 5 biggest game edges (estimates: the game model isn't calibrated). Pick one to open it on Props or Games.
  - **Props:** Superbet's player lines priced as on Today's props, with a note on which games are adjusted for RotoWire's lineups. The table shows the 12 columns that decide a bet (*More → Show every column* for the rest). A selected line has four tabs: *Verdict* (reasons for and against, and how the expected number was built: average → teammates out → game and matchup), *Teammates* (the player's row of the with/without matrix as a chart, tonight's out players outlined; works without RotoWire too), *History* (last 20 games vs the line, distribution, splits, record against the opponent) and *Line movement* (every snapshot of the line). A line checker for any player and line is at the bottom.
  - **Games:** one row per game, then the selected game's markets with the reasons for the best (or the clicked) outcome, and each team's ratings, lineup and absences. Model settings are in a popover.
- **Research**
  - **Player history:** form (last 5/10 vs average, minutes), and tabs for the game log (bars vs a line, 5/10-game averages, minutes), the distribution with percentiles, per-season and per-month averages over every stored season, splits, averages against each opponent, with/without one teammate and the full game log.
  - **Team history:** record and league ranks of the ratings, then the margin of every game, rolling offensive/defensive rating and pace, what the defense allows to guards, forwards and centers, and the roster.
  - **Lineup lab:** any team, also without an expected lineup. *Lineup from* picks RotoWire's lineup when it lists the team today, otherwise the last game's or the most frequent starters (or your own). The matrix covers the whole rotation, then the estimate for the chosen lineup and absences. *Use every stored season* (on by default) gives the matrix enough games early in the season; earlier seasons only count while both players were on the team.
- **Review**
  - **Results:** two tabs. **🌙 Previous night** (the default): pick one night or several (a period; newest first) and see how every line and game resolved against our last projection before its tip-off: lines settled, how our picks did (all, 🟢🟡, 🔴) and how often our projected average was closer to the result than Superbet's line. *Player lines*: projected average vs result per stat, our picks by signal and by stat, every line (with the opening line and our pick at the open) with filters. *Where bets won*: the settled lines grouped by any combination of stat, position, home/away, our pick's side, signal, team or game; per group how often betting Over and betting Under won and paid, the side to bet with its 95% range, and how our picks did, groups where a bet was most likely to win first (with a minimum number of lines, since one night is a small sample). *Games*: projected vs final score, winner called, total miss. Our picks, projections and red flags are saved with each fetch from Oct 21 (projected scores from Oct 22); for lines and games fetched before that, they're recomputed as the dashboard would have made them, from the games before that night and the lineups and odds saved before tip-off (marked recomputed). A night whose results aren't stored yet links to the stats update. **All saved nights:** every snapshotted line, settled against the stored stats. *Lines vs averages* compares each line with the player's average before that game (only earlier games, so nothing you couldn't have known): how often the side toward the average won and its ROI at the opening odds, by how far the line was from the average and by bet type, and how far the results landed from the lines. *Dashboard's picks* and *Game markets* show how the saved picks did (hit rate, ROI, cumulative profit, calibration). *All settled lines* lists them all, with a CSV download.
  - **Backtest 2022/23:** the backtest of the props model (section 7), when `data/backtest/2022_lines.csv` exists. *Tonight's lineup* switches between the two variants. *Summary*: the model against simple strategies on the same lines, calibration, and the model's picks by signal, edge, stat and month. *Strategy tester*: pick the lines (dates, players, stats, the model's signal, minimum edge and games, main lines only) and what to bet (the model's pick, toward the season average, always Under or Over; one side only) and see bets, hit rate against break-even, profit, ROI, the cumulative profit by date, results by stat and side, and every bet (CSV download). *Player*: how a player's lines resolved (how often they went over, the average miss), a chart of each line against the result and the season average before it, and how the model's picks on them did.
- **Data**
  - **Data center:** a card per source with its status and buttons: *Update 2026/27* (or another season, a date range, one game, a rebuild), *Fetch & save* (Superbet), *Snapshot with lineups* (the same plus RotoWire's lineups; also for tomorrow), and *Run both* for the morning routine (stats, then a snapshot). As in the first dashboard, Superbet is contacted only when one of these buttons is pressed, at most once every 5 minutes, every fetch is saved, and the pages use the newest fetch until its games tip off. When they all have, Overview, Props and Games say so and link to *Results → All settled lines* for that night. RotoWire is fetched when a page needs it and kept for 30 minutes; a fetch is saved when it's the day's first or something changed, and the RotoWire card shows the last saved version and what changed. The output streams into the page while the job runs, and every run is logged to `data/run_log.csv` (*Recent runs*). Tabs below show the stored seasons and snapshot files, names that don't match an ESPN player, and the points-add-up check.

The bet slip and the rule backtest are only in the first dashboard. Unit tests: `python -m pytest dashboard dashboard_v2 tests`.

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

Each run adds rows with a `fetched_at` time, so running it a few times a day (morning, an hour before tip-off) keeps the changes. The dashboards read Superbet's offers from the newest saved fetch (a snapshot run or a dashboard fetch, see above); they fetch RotoWire live every 30 minutes and save it whenever it changed (logged in `data/run_log.csv` with what changed, e.g. "Jaylen Brown (BOS): Ques 50% → Out 0%"); if RotoWire can't be reached, they fall back to its latest saved version. Each run also prices every line with the dashboard's default settings (about 15 seconds); if that fails, the odds are saved without picks. Before pricing, a run (or a dashboard fetch) refits the calibration and the 🟢 threshold when a newer night has settled since the last fit (`backtest.calibrate.refresh`). After a model change, `python daily_snapshot.py --reprice` prices every saved line again as of its fetch, into `superbet_props_replay.csv`; what each fetch showed stays in `superbet_props.csv` as it was saved.

The results tracker treats a line's first snapshot before tip-off as the bet and its last one as the closing line, so schedule two runs a day. On Windows, run these once in a Command Prompt (not PowerShell: `%CD%` must expand to the repository folder) opened in the repository root:

```
schtasks /Create /TN "nba-snapshot-morning" /SC DAILY /ST 10:00 /TR "cmd /c cd /d %CD% && python daily_snapshot.py"
schtasks /Create /TN "nba-snapshot-evening" /SC DAILY /ST 23:30 /TR "cmd /c cd /d %CD% && python daily_snapshot.py"
schtasks /Create /TN "nba-stats-update"     /SC DAILY /ST 09:00 /TR "cmd /c cd /d %CD% && python -m espn_scraper"
```

Times are local (Polish) time: most games start between 00:00 and 04:30, so 23:30 is close to the first tip-off; weekend afternoon games tip off earlier and only get the morning snapshot (no closing line). The scraper run in the morning stores last night's games, which settles their lines.

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

### 7. Backtest the props model on 2022/23

```
python -m backtest.run                                                  # both variants, about 10 minutes
python -m backtest.run --variant none --since 2022-11-10 --until 2022-11-20   # a quick partial run
```

Prices Unibet's 2022/23 player lines (`offers_resolved.csv`, about 40,000 lines from Nov 10 to May 9) with today's props model (`models.price_props`, unchanged), each from the games before its date only, and settles them. Writes `data/backtest/2022_lines.csv` and `data/backtest/2022_summary.md`; dashboard v2 shows them on the *Backtest 2022/23* page (see below).

- The old `2022-players-logs.csv` lacks columns today's scraper stores, so `backtest/data_2022.py` rebuilds them: game ids from date and teams, season type from the date, starters as each team's top 5 by minutes, positions from the 2024–26 logs (86% of player games; the rest get no matchup factor). The file was scraped from end-of-season rosters, so a traded player's earlier games carry his final team; the real team is taken from the date and opponent (2,395 games moved).
- There are no historical game odds, so the implied-team-total factor is off. Variant `none` knows nothing about tonight's lineup; `absences` treats every rotation player (15+ min a game over the team's last 10) who didn't play as out, an upper bound for RotoWire's value.
- Results before calibration (main lines, players with 5+ games, 29,331 lines): the model's picks won 51.0% at −3.6% ROI, worse than always betting the Under (52.2%, −2.7%); 🟢 picks 52.1% at −1.9% (2,181 bets, not significantly better than break-even). The model is overconfident: picks it gave 60–70% won 54.5%, 70–80% won 55%. Knowing tonight's absences perfectly barely changes this (🟢 −0.8%). Overs lost 6.7%, Unders 1.0%.

**Calibration** (`python -m backtest.calibrate`, after `backtest.run`; `--no-superbet` for the 2022/23 lines only): fits `model % = sigmoid(a·logit(market) + b·(logit(raw model) − logit(market)) + c·[Over] + d)` (`metrics.calibrate`) on each line's both sides, pooling the 2022/23 lines and every settled Superbet line (its last fetch before tip-off). Only chances of the current model (`nightly.MODEL_VERSION`) go into the fit: a Superbet line's own when that version saved it, else its replay from `superbet_props_replay.csv`; the 2022/23 lines when `backtest.run` was run with it. After a model change, run `python daily_snapshot.py --reprice` (and `python -m backtest.run`) so the new version has lines to be fitted on; until then the old calibration stays and the reason is logged. The check fits on the earlier part of each source (2022: Nov–Jan; Superbet: all but the latest 30% of nights) and scores the rest, games the fit never saw. The **🟢 threshold** is the smallest of +1…+5 pp whose picks on the unseen Superbet lines numbered 50+ over 10+ nights, paid, and won more often than their average break-even even at the low end of the hit rate's 95% range; when none did there's no 🟢. It's chosen on the same held-out nights it's judged on and re-chosen as nights settle, so treat it as exploratory: 🟡 is a positive *estimated* edge, 🟢 one that has held up so far, neither a proven betting advantage. The report's threshold table shows each threshold's bets, nights, hit rate with its range and break-even. Then everything is refitted for the dashboards (`data/backtest/calibration.json`: coefficients, `green_edge_pp`, `superbet_through`, `model_version`). Without a calibration fitted for the current model (`models.calibration_status`: missing, or fitted for another model version) the pages show a warning, model % is the raw (or the old) chance for research only, and no prop gets 🟢/🟡, a Bet/Lean verdict or a Kelly stake and refreshed automatically as nights settle. Report: `data/backtest/calibration.md`, also on the *Backtest 2022/23* page → *Calibration*.

- 2022/23 alone (before Superbet lines were added): a = 1.005, b = 0.079, c = −0.120, d = 0.060. The model's opinion beyond the price is worth about 8%; Overs are marked down.
- On the unseen 2022 Feb–May lines the calibrated chances match the results (predicted 57% → won 56%, 62% → 60%) and predict slightly better than the price itself (log loss 0.6889 vs 0.6895; uncalibrated 0.7055). But only 91 of 13,763 lines kept a positive edge (−4.5% ROI) and the 14 🟢 picks lost: no reliable edge left. Always Under was −0.6% on those months.
- With the Superbet lines through Oct 25, 2026 (8,222 lines, pooled with 2022/23): a = 1.093, b = 0.079, c = −0.103, d = 0.052. On the unseen Superbet nights (Oct 24–25, 2,463 lines) the calibrated chances held up (predicted 57% → won 56%, 62% → 59%) but no line had a positive edge, and Always Under lost 12% while Overs won 51.8%: the Under lean of 2022/23 and the first nights doesn't hold every night. No 🟢 threshold qualified, so there is no 🟢 until one does.
- Every pick, edge, signal, verdict and Kelly stake in both dashboards (and the picks saved with each fetch) now uses the calibrated chance; `raw model %` is in the extra columns. The backtest's full-season numbers are then in-sample (fitted on the same games), so the held-out report is the one to trust.

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
