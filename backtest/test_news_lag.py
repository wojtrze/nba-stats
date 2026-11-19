import pandas as pd

import backtest  # noqa: F401  (puts dashboard/ on the path)
from backtest.news_lag import evaluate, speed, summary
from news import cases

T = lambda day, h, m=0: pd.Timestamp(f'2026-11-{day:02d}', tz='UTC') + pd.Timedelta(hours=h, minutes=m)
TEAM_OF = {1: 'lal', 11: 'lal', 12: 'lal', 21: 'sa'}
TEAMS = pd.DataFrame({'home': ['lal', 'lal'], 'away': ['sa', 'sa']}, index=['g18', 'g20'])


def game(day):
    """A game whose teammate M1 moved by our read and M2 still stood at it (then stayed: takeable)."""
    rows = []
    for at in (T(day, 19), T(day, 20, 2), T(day, 21)):
        for name, pid, stat, line in (('A', 1, 'PTS', 25.5), ('M1', 11, 'PTS', 14.5 if at == T(day, 19) else 16.5),
                                      ('M2', 12, 'REB', 6.5), ('O1', 21, 'PTS', 10.5)):
            rows.append({'at': at, 'event_id': f'g{day}', 'tip': T(day, 23, 30), 'name_ESPN': name,
                         'player_id_ESPN': pid, 'bet_type': stat, 'line': line, 'over_odds': 1.9, 'under_odds': 1.9,
                         'source': 'schedule'})
    return pd.DataFrame(rows)


def events():
    return pd.DataFrame([{'night': pd.Timestamp(f'2026-11-{day}'), 'seen_at': T(day, 20), 'prev_at': T(day, 19),
                          'team': 'lal', 'player_id_ESPN': 1, 'name': 'A', 'kind': 'out'} for day in (18, 20)])


def logs():
    return pd.DataFrame([{'player_id_ESPN': pid, 'Date': pd.Timestamp(f'2026-11-{day}'), 'PTS': 20, 'REB': 8,
                          'AST': 3} for day in (18, 20) for pid in (11, 12, 21)]).astype({'player_id_ESPN': 'Int64'})


def test_the_signal_is_the_line_that_stood_and_d_splits_the_nights():
    offered = pd.concat([game(18), game(20)], ignore_index=True)
    found = cases(events(), offered, TEAMS, TEAM_OF)
    result = evaluate(found, offered, logs(), d='2026-11-19')
    for period in ('recognition', 'evaluation'):
        a = result['a'][period]
        assert a['nights'] == 1 and a['signals'] == 1 and a['won %'] == 100     # M2's Over 6.5, he had 8
        sp = result['speed'][period].set_index('news')
        assert sp.at['out', 'moved by our read'] == 1 and sp.at['out', 'moved later'] == 0
        assert sp.at['out', 'never'] == 1
    assert summary(result, '2026-11-19')['evaluation']['verdict'] == 'wait'      # 1 of the 10 nights


def test_speed_of_no_events_is_empty_not_an_error():
    sp = speed([])
    assert sp['events'].tolist() == [0, 0, 0]
