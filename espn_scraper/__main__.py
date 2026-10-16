"""Usage:
    python -m espn_scraper                                   # add all new final games of 2026/27 up to today
    python -m espn_scraper --since 2026-10-01 --until 2026-10-15
    python -m espn_scraper --game 401898398                  # (re)scrape one game
    python -m espn_scraper --rebuild                         # wipe data and rescrape the whole season
"""
import argparse
import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from . import ESPN_SEASON_YEAR, SEASON_END, SEASON_START, client, storage
from .boxscore import is_final, parse_summary
from .schedule import list_games

log = logging.getLogger("espn_scraper")


def scrape_game(game_id: str) -> int:
    data = client.summary(game_id)
    if not is_final(data):
        log.info("Game %s is not final yet, skipping", game_id)
        return -1
    game, players = parse_summary(data)
    storage.save_game(game, players)
    log.info("Saved %s %s@%s %s-%s (%d player lines)", game['date'], game['away'], game['home'],
             game['away_score'], game['home_score'], len(players))
    return len(players)


def update(since: date, until: date) -> None:
    stored = storage.stored_game_ids()
    added_games = added_lines = not_final = 0
    day = since
    while day <= until:
        for g in list_games(day):
            if g['season_year'] != ESPN_SEASON_YEAR or g['game_id'] in stored:
                continue
            if not g['completed']:
                not_final += 1
                log.info("%s %s@%s: %s, will retry next run", g['date'], g['away'], g['home'], g['status'])
                continue
            lines = scrape_game(g['game_id'])
            if lines >= 0:
                stored.add(g['game_id'])
                added_games += 1
                added_lines += lines
        day += timedelta(days=1)
    print(f"Added {added_games} games, {added_lines} player lines. {not_final} games not final yet.")


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def main():
    parser = argparse.ArgumentParser(prog="python -m espn_scraper", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--since", type=parse_date, help="first day to check (YYYY-MM-DD, US Eastern)")
    parser.add_argument("--until", type=parse_date, help="last day to check (default: today)")
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
        scrape_game(args.game)
        return

    if args.rebuild:
        storage.wipe()

    today = datetime.now(ZoneInfo("America/New_York")).date()
    until = min(args.until or today, parse_date(SEASON_END))
    if args.since:
        since = args.since
    else:
        last = storage.last_stored_date()
        # re-check the last stored day too, in case some of its games weren't final yet
        since = parse_date(last) - timedelta(days=1) if last else parse_date(SEASON_START)
    update(max(since, parse_date(SEASON_START)), until)


if __name__ == "__main__":
    main()
