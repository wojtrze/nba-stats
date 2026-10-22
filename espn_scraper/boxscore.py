import logging
from datetime import datetime, timezone
from typing import Dict, List, Tuple
from zoneinfo import ZoneInfo

from . import play_by_play, team_code
from .schedule import season_type_name

log = logging.getLogger(__name__)

EASTERN = ZoneInfo("America/New_York")

# Same column order as 2022-players-logs.csv, so bet_analyst.py can read the output; extra columns go last.
PLAYER_COLUMNS = ['OPP', 'Result', 'MIN', 'FG%', '3P%', 'FT%', 'REB', 'AST', 'BLK', 'STL', 'PF', 'TO', 'PTS',
                  'FGM', 'FGA', '3PM', '3PA', 'FTM', 'FTA', 'type', 'Date', 'season_id', 'player_id_ESPN',
                  'player_name_ESPN', 'team',
                  'game_id', 'season_type', 'starter', 'position', 'OREB', 'DREB', 'PLUS_MINUS', 'player_display_name']

TEAM_STATS = ['FGM', 'FGA', '3PM', '3PA', 'FTM', 'FTA', 'OREB', 'DREB', 'REB', 'AST', 'STL', 'BLK', 'TO', 'PF']
GAME_COLUMNS = ['game_id', 'date', 'season_id', 'season_type', 'home', 'away', 'home_score', 'away_score'] + \
               [f'home_{s}' for s in TEAM_STATS] + [f'away_{s}' for s in TEAM_STATS] + ['scraped_at']

# ESPN team-total stat names -> our names (made-attempted pairs are split separately)
TEAM_STAT_NAMES = {'offensiveRebounds': 'OREB', 'defensiveRebounds': 'DREB', 'totalRebounds': 'REB',
                   'assists': 'AST', 'steals': 'STL', 'blocks': 'BLK', 'totalTurnovers': 'TO', 'fouls': 'PF'}
MADE_ATTEMPTED = {'fieldGoalsMade-fieldGoalsAttempted': ('FGM', 'FGA'),
                  'threePointFieldGoalsMade-threePointFieldGoalsAttempted': ('3PM', '3PA'),
                  'freeThrowsMade-freeThrowsAttempted': ('FTM', 'FTA')}


def _num(value: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _pct(made: int, attempted: int) -> float:
    return round(100 * made / attempted, 1) if attempted else 0.0


def _split(value: str) -> Tuple[int, int]:
    made, _, attempted = (value or "0-0").partition("-")
    return _num(made), _num(attempted)


def is_final(summary: dict) -> bool:
    return summary["header"]["competitions"][0]["status"]["type"].get("completed", False)


def game_date_eastern(summary: dict) -> str:
    utc = datetime.strptime(summary["header"]["competitions"][0]["date"], "%Y-%m-%dT%H:%MZ")
    return utc.replace(tzinfo=timezone.utc).astimezone(EASTERN).date().isoformat()


def parse_summary(summary: dict) -> Tuple[Dict, List[Dict]]:
    """Turn an ESPN summary response into (game row, player game-log rows)."""
    header = summary["header"]
    competition = header["competitions"][0]
    game_id = header["id"]
    season_id = header["season"]["year"] - 1   # ESPN year is the year the season ends
    game_date = game_date_eastern(summary)

    sides = {}
    for c in competition["competitors"]:
        sides[c["homeAway"]] = {"team": team_code(c["team"]), "score": _num(c.get("score"))}
    home, away = sides["home"], sides["away"]
    season_type = season_type_name(header["season"]["type"], home["team"], away["team"])

    game = {'game_id': game_id, 'date': game_date, 'season_id': season_id, 'season_type': season_type,
            'home': home["team"], 'away': away["team"], 'home_score': home["score"], 'away_score': away["score"]}
    for team in summary["boxscore"]["teams"]:
        side = team["homeAway"]
        stats = {s["name"]: s["displayValue"] for s in team["statistics"]}
        for espn_name, (made_col, att_col) in MADE_ATTEMPTED.items():
            game[f'{side}_{made_col}'], game[f'{side}_{att_col}'] = _split(stats.get(espn_name))
        for espn_name, col in TEAM_STAT_NAMES.items():
            game[f'{side}_{col}'] = _num(stats.get(espn_name))
    game['scraped_at'] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    players = []
    for team in summary["boxscore"]["players"]:
        team_abbr = team_code(team["team"])
        side = "home" if team_abbr == home["team"] else "away"
        own, opp = sides[side], sides["away" if side == "home" else "home"]
        result = f"{'W' if own['score'] > opp['score'] else 'L'}{own['score']}-{opp['score']}"
        block = team["statistics"][0]
        keys = block["keys"]
        box_ids = {a["athlete"]["id"] for a in block["athletes"] if "id" in a["athlete"]}
        for athlete in block["athletes"]:
            info = athlete["athlete"]
            name = info.get("displayName") or info.get("shortName", "?")
            if athlete.get("didNotPlay") or not athlete.get("stats"):
                log.info("DNP %s (%s) in game %s: %s", name, team_abbr, game_id, athlete.get("reason", ""))
                continue
            if "id" in info and "displayName" in info:
                s = dict(zip(keys, athlete["stats"]))
            else:
                # ESPN occasionally lists a player (e.g. a two-way signing) without id, name or stats; the
                # play-by-play still has their plays, tagged with their id
                found = play_by_play.missing_player(summary.get("plays") or [], team["team"].get("id"),
                                                    info.get("shortName", ""), box_ids)
                if found is None:
                    log.warning("Skipping player %r without ESPN id/name in game %s (%s)", name, game_id, team_abbr)
                    continue
                s = play_by_play.player_stats(summary["plays"], found["id"], found["displayName"], side)
                if _num(s["minutes"]) == 0 and _num(s["points"]) == 0:
                    continue
                info = {**info, **found}
                log.warning("Rebuilt %s (%s, id %s) from the play-by-play in game %s", found["displayName"],
                            team_abbr, found["id"], game_id)
            fgm, fga = _split(s.get('fieldGoalsMade-fieldGoalsAttempted'))
            tpm, tpa = _split(s.get('threePointFieldGoalsMade-threePointFieldGoalsAttempted'))
            ftm, fta = _split(s.get('freeThrowsMade-freeThrowsAttempted'))
            players.append({
                'OPP': opp["team"].upper(), 'Result': result, 'MIN': _num(s.get('minutes')),
                'FG%': _pct(fgm, fga), '3P%': _pct(tpm, tpa), 'FT%': _pct(ftm, fta),
                'REB': _num(s.get('rebounds')), 'AST': _num(s.get('assists')), 'BLK': _num(s.get('blocks')),
                'STL': _num(s.get('steals')), 'PF': _num(s.get('fouls')), 'TO': _num(s.get('turnovers')),
                'PTS': _num(s.get('points')), 'FGM': fgm, 'FGA': fga, '3PM': tpm, '3PA': tpa, 'FTM': ftm, 'FTA': fta,
                'type': side, 'Date': game_date, 'season_id': season_id,
                'player_id_ESPN': info["id"], 'player_name_ESPN': info["displayName"].replace(" ", ""),
                'team': team_abbr, 'game_id': game_id, 'season_type': season_type,
                'starter': athlete.get("starter", False),
                'position': info.get("position", {}).get("abbreviation", ""),
                'OREB': _num(s.get('offensiveRebounds')), 'DREB': _num(s.get('defensiveRebounds')),
                'PLUS_MINUS': _num(s.get('plusMinus')), 'player_display_name': info["displayName"],
            })
    return game, players
