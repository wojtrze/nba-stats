"""The Overview's pick cards: one line of tonight in a few plain sentences (no Streamlit, tested in
test_v2_cards.py). A card describes a rated line; it never says to bet it (decisions.stars: 4★ is the best of
tonight, not an offer)."""
from typing import Dict, List

import pandas as pd

from i18n import t, value

STAT = {'ARP': 'PRA'}
LAST_GAMES = 10


def _known(v) -> bool:
    return v is not None and not (isinstance(v, float) and pd.isna(v)) and v is not pd.NA


def last_hits(pct, games):
    """(hits, games) of the side in the player's last LAST_GAMES games, from its % and his games played; None when
    either is unknown."""
    if not _known(pct) or not _known(games) or games <= 0:
        return None
    n = int(min(LAST_GAMES, games))
    return int(round(pct * n / 100)), n


def card(row, lang: str, tip: str = '') -> Dict[str, List[str]]:
    """{'title': ..., 'lines': [...]} of one priced line (decisions.stars row: name, side, line, bet_type, side odds,
    proj avg, p win %, side market %, break-even net %, pick % L10, games, wait)."""
    side = value(row['side'], lang)
    stat = STAT.get(row['bet_type'], row['bet_type'])
    title = f"{row['name']} · {side} {row['line']:g} {stat} · @{row['side odds']:.2f}"
    if tip:
        title += f" · {tip}"
    lines = []
    expect = []
    if _known(row.get('proj avg')):
        expect.append(t('card.expect', lang, proj=row['proj avg'], line=row['line']))
    hits = last_hits(row.get('pick % L10'), row.get('games'))
    if hits:
        expect.append(t('card.last', lang, side=side, hits=hits[0], n=hits[1]))
    if expect:
        lines.append(' · '.join(expect))
    chances = [t('card.ours', lang, p=row['p win %'])]
    if _known(row.get('side market %')):
        chances.append(t('card.superbet', lang, p=row['side market %']))
    if _known(row.get('break-even net %')):
        chances.append(t('card.needed', lang, p=row['break-even net %']))
    lines.append(' · '.join(chances))
    if row.get('wait'):
        lines.append(f"⏳ {row['wait']}")
    return {'title': title, 'lines': lines}
