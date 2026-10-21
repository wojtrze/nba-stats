"""Game-market wording shared by the Overview and Games pages."""
import pandas as pd

MARKET_LABELS = {'ML': 'Moneyline', 'SPREAD': 'Handicap', 'TOTAL': 'Total', 'HOME_TOTAL': 'Home team total',
                 'AWAY_TOTAL': 'Away team total'}


def describe_outcome(outcome) -> str:
    """'Handicap DET +1.5', 'Total over 220.5', 'Moneyline BOS'."""
    who = outcome['team'].upper() if outcome['market'] in ('ML', 'SPREAD') else outcome['side']
    line = '' if pd.isna(outcome['line']) else \
        f" {outcome['line']:+g}" if outcome['market'] == 'SPREAD' else f" {outcome['line']:g}"
    return f"{MARKET_LABELS[outcome['market']]} {who}{line}"


def winner(projection, home: str, away: str) -> str:
    """'BOS by 3.5': the projected winner and margin."""
    return f"{(home if projection['margin'] >= 0 else away).upper()} by {abs(projection['margin']):.1f}"
