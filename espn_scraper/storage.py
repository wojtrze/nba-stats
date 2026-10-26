import os
import shutil
from typing import Dict, Iterable, List, Optional, Set

import pandas as pd

from . import CURRENT_SEASON, data_dir
from safe_io import append_csv, atomic_to_csv, atomic_write_text, locked

from .boxscore import GAME_COLUMNS, PLAYER_COLUMNS


def games_file(season: int) -> str:
    return os.path.join(data_dir(season), "games.csv")


def players_file(season: int) -> str:
    return os.path.join(data_dir(season), "player_gamelogs.csv")


def snapshot_file(season: int, name: str) -> str:
    """Daily RotoWire/Superbet snapshots: 'rotowire_lineups', 'superbet_props' or 'superbet_game_odds'."""
    return os.path.join(data_dir(season), f"{name}.csv")


def _checked_file(season: int) -> str:
    return os.path.join(data_dir(season), "checked_through.txt")


# current season's files, used by the analysis code
GAMES_FILE = games_file(CURRENT_SEASON)
PLAYERS_FILE = players_file(CURRENT_SEASON)


def _read(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path, dtype={'game_id': str})


def stored_game_ids(season: int) -> Set[str]:
    games = _read(games_file(season))
    return set(games['game_id']) if not games.empty else set()


def checked_through(season: int) -> Optional[str]:
    """Last date (YYYY-MM-DD) up to which every day's games are known to be stored."""
    if not os.path.exists(_checked_file(season)):
        return None
    with open(_checked_file(season)) as f:
        return f.read().strip() or None


def set_checked_through(season: int, day: str):
    atomic_write_text(_checked_file(season), day + '\n')


def _append(season: int, path: str, rows: List[Dict], columns: List[str]):
    append_csv(pd.DataFrame(rows, columns=columns), path, columns)


def _drop_game(path: str, game_id: str):
    with locked(path):
        df = _read(path)
        if not df.empty and (df['game_id'] == game_id).any():
            atomic_to_csv(df[df['game_id'] != game_id], path)


def save_game(season: int, game: Dict, players: List[Dict], replace: bool = False):
    """Store one game. Player rows go first and the game row last, so an interrupted
    save leaves the game unrecorded and it gets re-scraped on the next run.
    replace=True first removes rows already stored for this game (needed when re-scraping it)."""
    if replace:
        _drop_game(games_file(season), game['game_id'])
        _drop_game(players_file(season), game['game_id'])
    _append(season, players_file(season), players, PLAYER_COLUMNS)
    _append(season, games_file(season), [game], GAME_COLUMNS)


def load_player_gamelogs(seasons: Iterable[int]) -> pd.DataFrame:
    """Player game logs of several seasons in one DataFrame, e.g. load_player_gamelogs([2024, 2025, 2026])."""
    frames = [_read(players_file(season)) for season in seasons]
    return pd.concat([f for f in frames if not f.empty], ignore_index=True)


def load_games(seasons: Iterable[int]) -> pd.DataFrame:
    """games.csv of several seasons in one DataFrame, with `date` parsed."""
    frames = [_read(games_file(season)) for season in seasons]
    df = pd.concat([f for f in frames if not f.empty], ignore_index=True)
    df['date'] = pd.to_datetime(df['date'])
    return df


def wipe(season: int):
    if os.path.isdir(data_dir(season)):
        shutil.rmtree(data_dir(season))
