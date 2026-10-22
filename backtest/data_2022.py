"""2022/23 data for the backtest: the old game logs (2022-players-logs.csv) and Unibet's resolved lines
(offers_resolved.csv), reshaped into what models.price_props expects. No Streamlit, tested in test_backtest.py.

The old logs were scraped from ESPN's player pages, so they lack columns today's scraper stores: game ids,
positions, starters and season types are rebuilt here (see load_logs_2022).
"""
import unicodedata
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

from espn_scraper import NBA_TEAM_ABBRS

LOGS_FILE = '2022-players-logs.csv'
LINES_FILE = 'offers_resolved.csv'
SEASON = 2022
STAT_COLUMNS = ['MIN', 'FG%', '3P%', 'FT%', 'REB', 'AST', 'BLK', 'STL', 'PF', 'TO', 'PTS', 'FGM', 'FGA', '3PM', '3PA',
                'FTM', 'FTA']
# last day of each part of 2022/23 (ESPN dates); anything later is the playoffs
REGULAR_SEASON_END, PLAY_IN_END = pd.Timestamp('2023-04-09'), pd.Timestamp('2023-04-14')
# Unibet's names that don't match ESPN's once spaces are removed (bet_analyst.UB_to_ESPN_player_name; that module
# fetches RotoWire when imported, so the dict is copied)
UNIBET_TO_ESPN = {'J.Brown': 'JaylenBrown', 'D.Sabonis': 'DomantasSabonis', 'M.Beasley': 'MalikBeasley',
                  'B.Simmons': 'BenSimmons', 'J.Poeltl': 'JakobPoeltl', 'NicolasClaxton': 'NicClaxton',
                  'TroyBrown': 'TroyBrownJr.', 'C.LeVert': 'CarisLeVert', 'CameronReddish': 'CamReddish'}


def strip_accents(name: str) -> str:
    """'LukaDončić' -> 'LukaDoncic'."""
    return ''.join(c for c in unicodedata.normalize('NFKD', name) if not unicodedata.combining(c))


def espn_name(unibet_name: str) -> str:
    return UNIBET_TO_ESPN.get(unibet_name, strip_accents(unibet_name))


# --- game logs ---

def clean_logs(raw: pd.DataFrame) -> pd.DataFrame:
    """Drop the repeated header rows, All-Star games and duplicate (player, date) rows; numbers as numbers."""
    logs = raw[raw['season_id'].astype(str) != 'season_id'].copy()
    logs['OPP'] = logs['OPP'].str.strip()
    logs = logs[logs['OPP'].str.lower().isin(NBA_TEAM_ABBRS) & logs['team'].isin(NBA_TEAM_ABBRS)]
    for col in STAT_COLUMNS:
        logs[col] = pd.to_numeric(logs[col], errors='coerce')
    logs['Date'] = pd.to_datetime(logs['Date'])
    logs['player_id_ESPN'] = pd.to_numeric(logs['player_id_ESPN']).astype('int64')
    logs['season_id'] = SEASON
    return logs.drop_duplicates(['player_id_ESPN', 'Date']).reset_index(drop=True)


def fix_teams(logs: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """The logs were scraped from end-of-season rosters, so a traded player's games before the trade carry his
    final team. On a date each team plays one opponent, so the real team of a row is the team most rows with the
    same (date, opponent) have. Returns the fixed logs and how many rows changed."""
    real = logs.groupby(['Date', 'OPP'])['team'].agg(lambda t: t.mode().iloc[0]).rename('real_team')
    fixed = logs.join(real, on=['Date', 'OPP'])
    changed = int((fixed['real_team'] != fixed['team']).sum())
    return fixed.assign(team=fixed['real_team']).drop(columns='real_team'), changed


def season_type(dates: pd.Series) -> pd.Series:
    return pd.Series(np.select([dates <= REGULAR_SEASON_END, dates <= PLAY_IN_END], ['regular', 'playin'], 'post'),
                     index=dates.index)


def add_game_columns(logs: pd.DataFrame) -> pd.DataFrame:
    """game_id ('2022-11-10_cha_por', the two teams sorted), season_type, and starter = the team's 5 players with
    the most minutes in the game (the old logs don't say who started)."""
    opp = logs['OPP'].str.lower()
    first, second = np.minimum(logs['team'], opp), np.maximum(logs['team'], opp)
    logs = logs.assign(game_id=logs['Date'].dt.strftime('%Y-%m-%d') + '_' + first + '_' + second,
                       season_type=season_type(logs['Date']))
    rank = logs.groupby(['game_id', 'team'])['MIN'].rank(method='first', ascending=False)
    return logs.assign(starter=rank <= 5)


def add_positions(logs: pd.DataFrame, later_logs: pd.DataFrame) -> pd.DataFrame:
    """Each player's latest position in later seasons' logs (the old logs have none); NaN for players who
    weren't in the league any more. Without a position the matchup factor stays 1."""
    if later_logs.empty:
        return logs.assign(position=np.nan)
    latest = later_logs.sort_values('Date').groupby('player_id_ESPN')['position'].last()
    latest.index = pd.to_numeric(latest.index).astype('int64')
    return logs.assign(position=logs['player_id_ESPN'].map(latest))


def load_logs_2022(later_logs: Optional[pd.DataFrame] = None, path: str = LOGS_FILE) -> Tuple[pd.DataFrame, Dict]:
    """The 2022/23 logs in today's column layout (ready for models.prepare_logs) and a report of the cleanup.
    later_logs: logs of later seasons for positions (default: every stored season)."""
    if later_logs is None:
        from espn_scraper import SEASONS
        from espn_scraper.storage import load_player_gamelogs
        later_logs = load_player_gamelogs(sorted(SEASONS))
    raw = pd.read_csv(path, low_memory=False)
    logs = clean_logs(raw)
    logs, moved = fix_teams(logs)
    logs = add_positions(add_game_columns(logs), later_logs)
    logs = logs.assign(player_display_name=logs['player_name_ESPN'], OREB=np.nan, DREB=np.nan, PLUS_MINUS=np.nan)
    report = {'raw rows': len(raw), 'player games': len(logs), 'players': logs['player_id_ESPN'].nunique(),
              'rows moved to the real team': moved,
              'player games with a position': f"{100 * logs['position'].notna().mean():.0f}%"}
    return logs, report


# --- lines ---

def pair_sides(offers: pd.DataFrame) -> pd.DataFrame:
    """One row per line with over_odds and under_odds (the file has a row per side). Lines missing a side are
    dropped."""
    keys = ['player_ESPN', 'bet_type', 'line', 'home', 'away', 'closed_date']
    sides = offers.drop_duplicates(keys + ['over_under']).pivot_table(index=keys, columns='over_under', values='odds',
                                                                      aggfunc='first')
    sides = sides.rename(columns={'Over': 'over_odds', 'Under': 'under_odds'}).dropna(subset=['over_odds', 'under_odds'])
    actual = offers.drop_duplicates(keys).set_index(keys)['actual'].rename('file_actual')
    return sides.join(actual).reset_index()


def mark_main_lines(lines: pd.DataFrame) -> pd.DataFrame:
    """main = the line whose two prices are closest, per player, stat and game (the bookmaker's main line);
    the others are alternative lines or earlier versions of it."""
    gap = (lines['over_odds'] - lines['under_odds']).abs()
    best = gap.groupby([lines['player_id_ESPN'], lines['bet_type'], lines['game_date']]).transform('min')
    main = gap == best
    # a tie (two equally balanced lines): keep the first as main
    first = ~lines[main].duplicated(['player_id_ESPN', 'bet_type', 'game_date'])
    return lines.assign(main=main & first.reindex(lines.index, fill_value=False))


def load_lines_2022(logs: pd.DataFrame, path: str = LINES_FILE) -> Tuple[pd.DataFrame, Dict]:
    """Unibet's 2022/23 lines as price_props input (name, name_ESPN, home, away, bet_type, line, event_id,
    start_time, over_odds, under_odds, player_id_ESPN), plus game_date, main and file_actual; only lines whose
    player has a game that date against one of the line's teams. logs: load_logs_2022 output."""
    offers = pd.read_csv(path)
    lines = pair_sides(offers)
    report = {'lines in the file': len(lines)}
    lines['name_ESPN'] = lines['player_ESPN'].map(espn_name)
    ids = logs.drop_duplicates('player_name_ESPN', keep='last').set_index('player_name_ESPN')['player_id_ESPN']
    lines['player_id_ESPN'] = lines['name_ESPN'].map(ids)
    report['lines without a matching player'] = int(lines['player_id_ESPN'].isna().sum())
    lines = lines.dropna(subset=['player_id_ESPN']).astype({'player_id_ESPN': 'int64'})
    # the line closes at tip-off (UTC); 6 hours earlier is the game's US date
    closed = pd.to_datetime(lines['closed_date'], utc=True)
    lines['game_date'] = (closed - pd.Timedelta(hours=6)).dt.tz_localize(None).dt.normalize()
    played = logs[['player_id_ESPN', 'Date', 'team', 'OPP']].rename(columns={'Date': 'game_date'})
    lines = lines.merge(played, on=['player_id_ESPN', 'game_date'], how='left')
    in_game = (lines['team'] == lines['home']) | (lines['team'] == lines['away'])
    report["lines where the player didn't play that game"] = int((~in_game).sum())
    lines = lines[in_game].drop(columns=['team', 'OPP'])
    lines = lines.assign(name=lines['player_ESPN'], start_time=lines['closed_date'],
                         event_id=lines['game_date'].dt.strftime('%Y-%m-%d') + '_' + lines['away'] + '_' + lines['home'])
    lines = mark_main_lines(lines.reset_index(drop=True))
    report['lines priced'] = len(lines)
    report['main lines'] = int(lines['main'].sum())
    return lines, report
