# Matching player names from RotoWire and Superbet to ESPN player ids in the game logs.
import re
import unicodedata
from typing import Dict

import pandas as pd

SUFFIXES = {'jr', 'sr', 'ii', 'iii', 'iv', 'v'}

# normalized external name -> normalized ESPN name, for names spelled differently at the sources
OVERRIDES: Dict[str, str] = {}


def normalize(name: str) -> str:
    """"Jackson Jr., Jaren" / "Jaren Jackson Jr." / "JAREN JACKSON" -> "jaren jackson"; accents and dots removed."""
    name = unicodedata.normalize('NFKD', str(name)).encode('ascii', 'ignore').decode()
    if ',' in name:
        last, first = name.split(',', 1)
        name = f"{first} {last}"
    words = [w for w in re.sub(r"[.'`]", '', name.lower()).replace('-', ' ').split() if w not in SUFFIXES]
    key = ' '.join(words)
    return OVERRIDES.get(key, key)


class NameResolver:
    """Built once from game logs (sorted by date); resolve() returns an ESPN player id or None."""

    def __init__(self, logs: pd.DataFrame):
        latest = logs.sort_values('Date').groupby('player_id_ESPN').tail(1)
        self.players = pd.DataFrame({'player_id_ESPN': latest['player_id_ESPN'].values,
                                     'team': latest['team'].values,
                                     'key': latest['player_display_name'].map(normalize).values})
        self.players['first'] = self.players['key'].str.split().str[0].fillna('')
        self.players['last'] = self.players['key'].str.split().str[-1].fillna('')

    def resolve(self, name: str, team=None):
        """team: an ESPN abbreviation, or several (e.g. both teams of a game) when the player's team isn't known."""
        key = normalize(name)
        teams = [team] if isinstance(team, str) else list(team) if team is not None else []
        on_team = self.players[self.players['team'].isin(teams)]
        for pool in (on_team, self.players):
            hit = pool[pool['key'] == key]
            if len(hit) == 1:
                return hit['player_id_ESPN'].iloc[0]
        # same last name and first initial on the team ("Nic Claxton" vs "Nicolas Claxton")
        words = key.split()
        if words and len(on_team):
            hit = on_team[(on_team['last'] == words[-1]) & (on_team['first'].str[:1] == words[0][:1])]
            if len(hit) == 1:
                return hit['player_id_ESPN'].iloc[0]
        return None

    def add_ids(self, df: pd.DataFrame, name_col: str = 'name', team_cols=('team',)) -> pd.DataFrame:
        """df with a player_id_ESPN column (None where the name couldn't be matched). team_cols: the column(s)
        holding the player's team, or both teams of the game."""
        teams = zip(*(df[c] for c in team_cols)) if len(df) else []
        ids = [self.resolve(n, list(t)) for n, t in zip(df[name_col], teams)]
        return df.assign(player_id_ESPN=pd.array(ids, dtype=object))
