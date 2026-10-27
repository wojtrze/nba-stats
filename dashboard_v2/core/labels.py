"""Game-market wording shared by the Overview and Games pages, in the chosen language (i18n)."""
import pandas as pd

from i18n import t, value

MARKET_LABELS = {'ML': 'Moneyline', 'SPREAD': 'Handicap', 'TOTAL': 'Total', 'HOME_TOTAL': 'Home team total',
                 'AWAY_TOTAL': 'Away team total'}


def market_label(market: str, lang: str = 'en') -> str:
    return t(f'market.{market}', lang)


def describe_outcome(outcome, lang: str = 'en') -> str:
    """'Handicap DET +1.5', 'Total over 220.5', 'Winner BOS' (Polish: 'Suma powyżej 220.5'...)."""
    who = outcome['team'].upper() if outcome['market'] in ('ML', 'SPREAD') else value(outcome['side'], lang)
    line = '' if pd.isna(outcome['line']) else \
        f" {outcome['line']:+g}" if outcome['market'] == 'SPREAD' else f" {outcome['line']:g}"
    return f"{market_label(outcome['market'], lang)} {who}{line}"


def winner(projection, home: str, away: str, lang: str = 'en') -> str:
    """'BOS by 3.5': the projected winner and margin."""
    return t('winner', lang, team=(home if projection['margin'] >= 0 else away).upper(),
             margin=abs(projection['margin']))
