import os
import shutil
from typing import Dict, List, Optional, Set

import pandas as pd

from . import DATA_DIR
from .boxscore import GAME_COLUMNS, PLAYER_COLUMNS

GAMES_FILE = os.path.join(DATA_DIR, "games.csv")
PLAYERS_FILE = os.path.join(DATA_DIR, "player_gamelogs.csv")


def _read(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path, dtype={'game_id': str})


def stored_game_ids() -> Set[str]:
    games = _read(GAMES_FILE)
    return set(games['game_id']) if not games.empty else set()


def last_stored_date() -> Optional[str]:
    games = _read(GAMES_FILE)
    return games['date'].max() if not games.empty else None


def _append(path: str, rows: List[Dict], columns: List[str]):
    os.makedirs(DATA_DIR, exist_ok=True)
    df = pd.DataFrame(rows, columns=columns)
    df.to_csv(path, mode='a', header=not os.path.exists(path), index=False)


def _drop_game(path: str, game_id: str):
    df = _read(path)
    if not df.empty and (df['game_id'] == game_id).any():
        df[df['game_id'] != game_id].to_csv(path, index=False)


def save_game(game: Dict, players: List[Dict]):
    """Store one game. Player rows go first and the game row last, so an interrupted
    save leaves the game unrecorded and it gets re-scraped on the next run."""
    _drop_game(GAMES_FILE, game['game_id'])
    _drop_game(PLAYERS_FILE, game['game_id'])
    _append(PLAYERS_FILE, players, PLAYER_COLUMNS)
    _append(GAMES_FILE, [game], GAME_COLUMNS)


def wipe():
    if os.path.isdir(DATA_DIR):
        shutil.rmtree(DATA_DIR)
