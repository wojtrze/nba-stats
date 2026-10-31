"""The bet slip: suggested stakes, warnings about bets that win or lose together, and the saved bets
(data/<season>/my_bets.csv). No Streamlit, so it can be tested."""
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List

import numpy as np
import pandas as pd

from espn_scraper import CURRENT_SEASON
from espn_scraper.storage import snapshot_file
from decisions import OBSTAW
from metrics import ACTIVE_PROFILE, alpha
from safe_io import append_csv

BET_FIELDS = ['bet_id', 'placed_at', 'kind', 'event_id', 'start_time', 'home', 'away', 'name', 'name_ESPN',
              'player_id_ESPN', 'bet_type', 'market', 'side', 'team', 'line', 'odds', 'stake', 'model_pct', 'edge_pp',
              'edge_low']


def kelly_stake(chance: float, odds: float, bankroll: float, fraction: float = 0.25, cap: float = 0.05,
                profile: str = ACTIVE_PROFILE) -> float:
    """Fractional Kelly on the net price (metrics.COST_PROFILES: a win pays alpha × odds): fraction × (chance ×
    alpha × odds − 1) / (alpha × odds − 1) of the bankroll, at most `cap` of it, 0 without a positive expected
    return. A quarter Kelly gives up a little growth for far smaller swings when the model is too optimistic."""
    net = alpha(profile) * odds if pd.notna(odds) else np.nan
    if pd.isna(chance) or pd.isna(net) or net <= 1:
        return 0.0
    full = (chance * net - 1) / (net - 1)
    return round(bankroll * float(np.clip(full * fraction, 0, cap)), 2)


def staking_chance(bet: Dict) -> float:
    """The chance to size a bet on: the model's chance to win (model_pct), only for an offer whose decision is
    OBSTAW (decisions.py; bet['decision']). NaN (no stake) for every other bet: game outcomes (never admitted),
    props whose decision is NIE_OBSTAWIAJ / CZEKAJ / NIEDOSTEPNE, and bets saved without a decision. The 'edge low'
    range isn't used: it's only the sampling noise of the player's hit rate, not the model's uncertainty."""
    if bet.get('kind') != 'prop' or bet.get('decision') != OBSTAW or pd.isna(bet.get('model_pct')):
        return np.nan
    return bet['model_pct'] / 100


def describe(bet: Dict) -> str:
    """'Curry, Stephen Under 23.5 PTS' or 'NYK @ BOS: Total over 220.5'."""
    if bet['kind'] == 'prop':
        return f"{bet['name']} {bet['side']} {bet['line']:g} {bet['bet_type']}"
    words = {'ML': 'Moneyline', 'SPREAD': 'Handicap', 'TOTAL': 'Total', 'HOME_TOTAL': 'Home total',
             'AWAY_TOTAL': 'Away total'}
    team = bet.get('team') if isinstance(bet.get('team'), str) else ''   # NaN after a CSV round trip
    who = team.upper() if bet['market'] in ('ML', 'SPREAD') else bet['side']
    line = '' if pd.isna(bet['line']) else f" {bet['line']:+g}" if bet['market'] == 'SPREAD' else f" {bet['line']:g}"
    return f"{bet['away'].upper()} @ {bet['home'].upper()}: {words[bet['market']]} {who}{line}"


def _direction(bet: Dict) -> str:
    """'high' / 'low' when the bet needs a high- or low-scoring game (Overs and Unders), else ''."""
    side = str(bet['side']).lower()
    if bet['kind'] == 'prop' or bet['market'] in ('TOTAL', 'HOME_TOTAL', 'AWAY_TOTAL'):
        return 'high' if side == 'over' else 'low' if side == 'under' else ''
    return ''


def slip_warnings(slip: List[Dict], bankroll: float) -> List[str]:
    """Bets that depend on the same thing (one player, one game's scoring), both sides of a line, and a slip
    that stakes too much of the bankroll."""
    warnings = []
    if not slip:
        return warnings
    df = pd.DataFrame(slip)
    df['game'] = df['away'].str.upper() + ' @ ' + df['home'].str.upper()
    df['direction'] = [_direction(b) for b in slip]
    props = df[df['kind'] == 'prop']
    for name, part in props.groupby('name'):
        if len(part) > 1:
            warnings.append(f"{name}: {len(part)} bets on one player ({', '.join(part['bet_type'])}): one quiet "
                            f"night loses them all")
        both = part.groupby(['bet_type', 'line'])['side'].nunique()
        for (stat, line), sides in both.items():
            if sides > 1:
                warnings.append(f"{name} {stat} {line:g}: both Over and Under: at most one can win")
    for game, part in df.groupby('game'):
        for direction, word in (('high', 'Overs'), ('low', 'Unders')):
            same = part[part['direction'] == direction]
            if len(same) >= 2:
                warnings.append(f"{game}: {len(same)} {word} all need a {direction}-scoring game, so they tend to "
                                f"win or lose together")
        if len(part) >= 3:
            warnings.append(f"{game}: {len(part)} bets on one game")
    total = df['stake'].sum()
    if bankroll and total > 0.15 * bankroll:
        warnings.append(f"The slip stakes {total:.2f}, {100 * total / bankroll:.0f}% of the bankroll: more than 15% "
                        f"on one night")
    return warnings


def bets_file() -> str:
    return snapshot_file(CURRENT_SEASON, 'my_bets')


def load_bets(path: str = None) -> pd.DataFrame:
    path = path or bets_file()
    if not os.path.exists(path):
        return pd.DataFrame(columns=BET_FIELDS)
    return pd.read_csv(path)


def save_bets(slip: List[Dict], path: str = None) -> int:
    """Append the slip's bets (with an id and the time) to my_bets.csv. Returns how many were saved."""
    path = path or bets_file()
    placed = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    rows = pd.DataFrame([{**b, 'bet_id': uuid.uuid4().hex[:12], 'placed_at': placed} for b in slip]) \
        .reindex(columns=BET_FIELDS)
    if rows.empty:
        return 0
    return append_csv(rows, path, BET_FIELDS)


def as_snapshot_rows(bets: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Saved bets in the snapshot format tracking.settle_props / settle_games take: {'prop': ..., 'game': ...}.
    A prop's odds go to over_odds or under_odds by its side; `pick` is the side."""
    props = bets[bets['kind'] == 'prop'].copy()
    props['pick'] = props['side']
    props['over_odds'] = props['odds'].where(props['side'] == 'Over')
    props['under_odds'] = props['odds'].where(props['side'] == 'Under')
    games = bets[bets['kind'] == 'game'].copy()
    return {'prop': props, 'game': games}
