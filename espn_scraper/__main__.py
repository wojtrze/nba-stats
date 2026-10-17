"""Usage:
    python -m espn_scraper                                   # add all new final games of the current season (2026/27)
    python -m espn_scraper --season 2025                     # 2025/26 season (seasons are named by their start year)
    python -m espn_scraper --since 2026-10-01 --until 2026-10-15
    python -m espn_scraper --game 401898398                  # (re)scrape one game, stored under its own season
    python -m espn_scraper --rebuild                         # wipe the season's data and rescrape it
"""
import argparse
import logging
from datetime import date, datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

import requests

from . import CURRENT_SEASON, SEASONS, client, core_api, espn_year, storage
from .boxscore import is_final, parse_summary
from .schedule import list_games

log = logging.getLogger("espn_scraper")


def scrape_game(game_id: str, replace: bool = False) -> int:
    try:
        data = client.summary(game_id)
    except requests.HTTPError as e:
        if e.response is None or e.response.status_code != 404:
            raise
        # ESPN's summary is missing for a few games; the core API still has their box score
        log.info("Summary for game %s returns 404, rebuilding it from the core API", game_id)
        data = core_api.summary(game_id)
    if not is_final(data):
        log.info("Game %s is not final yet, skipping", game_id)
        return -1
    game, players = parse_summary(data)
    storage.save_game(game['season_id'], game, players, replace=replace)
    log.info("Saved %s %s@%s %s-%s %s (%d player lines)", game['date'], game['away'], game['home'],
             game['away_score'], game['home_score'], game['season_type'], len(players))
    return len(players)


def update(season: int, since: date, until: date) -> Optional[date]:
    """Scrape all final, not yet stored games of the season between since and until.
    Returns the first day that still has unfinished games, or None if every day is complete."""
    stored = storage.stored_game_ids(season)
    added_games = added_lines = not_final = 0
    first_incomplete_day = None
    day = since
    while day <= until:
        for g in list_games(day):
            if g['season_year'] != espn_year(season) or g['game_id'] in stored:
                continue
            if g['status'] in ("STATUS_POSTPONED", "STATUS_CANCELED"):
                # never completes on this day; a makeup game is listed again under its new date
                log.info("%s %s@%s: %s, skipping", g['date'], g['away'], g['home'], g['status'])
                continue
            try:
                lines = scrape_game(g['game_id']) if g['completed'] else -1
            except Exception:
                # don't stop a whole-season run on one odd game; it's retried next run
                log.exception("Failed to scrape game %s (%s %s@%s)", g['game_id'], g['date'], g['away'], g['home'])
                lines = -1
            if lines < 0:
                not_final += 1
                first_incomplete_day = first_incomplete_day or day
                log.info("%s %s@%s: %s, will retry next run", g['date'], g['away'], g['home'], g['status'])
                continue
            stored.add(g['game_id'])
            added_games += 1
            added_lines += lines
        day += timedelta(days=1)
    print(f"{season}/{(season + 1) % 100:02d}: added {added_games} games, {added_lines} player lines. "
          f"{not_final} games not final yet.")
    return first_incomplete_day


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def main():
    parser = argparse.ArgumentParser(prog="python -m espn_scraper", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--season", type=int, default=CURRENT_SEASON, choices=sorted(SEASONS),
                        help=f"season start year (default: {CURRENT_SEASON})")
    parser.add_argument("--since", type=parse_date, help="first day to check (YYYY-MM-DD, US Eastern)")
    parser.add_argument("--until", type=parse_date, help="last day to check (default: today or season end)")
    parser.add_argument("--game", help="scrape a single ESPN game id, replacing stored data for it")
    parser.add_argument("--rebuild", action="store_true", help="delete stored season data and rescrape")
    parser.add_argument("-v", "--verbose", action="store_true", help="also log DNPs and every request")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    if not args.verbose:
        logging.getLogger("espn_scraper.boxscore").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)

    if args.game:
        scrape_game(args.game, replace=True)
        return

    season = args.season
    season_start, season_end = (parse_date(d) for d in SEASONS[season])
    if args.rebuild:
        storage.wipe(season)

    today = datetime.now(ZoneInfo("America/New_York")).date()
    until = min(args.until or today, season_end)
    checked = storage.checked_through(season)
    # first day not yet known to be complete; days up to `checked` have all their games stored
    next_unchecked = parse_date(checked) + timedelta(days=1) if checked else season_start
    since = max(args.since or next_unchecked, season_start)

    first_incomplete_day = update(season, since, until)

    # advance the marker only if this run continued from it without leaving a gap
    if since <= next_unchecked:
        complete_through = first_incomplete_day - timedelta(days=1) if first_incomplete_day else until
        if complete_through >= next_unchecked:
            storage.set_checked_through(season, complete_through.isoformat())


if __name__ == "__main__":
    main()
