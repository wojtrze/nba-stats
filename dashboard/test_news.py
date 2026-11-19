import pandas as pd

from news import (MOVED_EARLY, MOVED_LATER, NEVER, WITHDRAWN, cases, find_events, reactions, signal_rows)

NIGHT = pd.Timestamp('2026-11-09')
T = lambda h, m=0: pd.Timestamp('2026-11-09', tz='UTC') + pd.Timedelta(hours=h, minutes=m)
TIP = T(23, 30)


def version(*rows):
    return pd.DataFrame([{'player_id_ESPN': pid, 'team': team, 'play_pct': pct, 'name': name}
                         for pid, team, pct, name in rows])


def test_out_and_return_news_between_two_close_versions():
    versions = {NIGHT: [(T(19), version((1, 'lal', 100, 'A'), (2, 'lal', 0, 'B'), (3, 'sa', 100, 'C'))),
                        (T(20), version((1, 'lal', 0, 'A'), (2, 'lal', 75, 'B'), (3, 'sa', 100, 'C')))]}
    events = find_events(versions, {NIGHT: {1, 2, 3}})
    assert events[['player_id_ESPN', 'kind']].values.tolist() == [[1, 'out'], [2, 'return']]


def test_a_return_also_when_he_drops_off_the_list_while_his_team_is_listed():
    versions = {NIGHT: [(T(19), version((2, 'lal', 0, 'B'), (5, 'lal', 50, 'E'))),
                        (T(19, 30), version((5, 'lal', 50, 'E')))]}
    events = find_events(versions, {NIGHT: {2}})
    assert events[['player_id_ESPN', 'kind']].values.tolist() == [[2, 'return']]


def quote(at, name, pid, stat, line, over, under):
    return {'at': at, 'event_id': 'g1', 'tip': TIP, 'name_ESPN': name, 'player_id_ESPN': pid, 'bet_type': stat,
            'line': line, 'over_odds': over, 'under_odds': under, 'source': 'schedule'}


def game():
    rows = []
    for at in (T(19), T(20, 2), T(21), T(22)):
        rows.append(quote(at, 'A', 1, 'PTS', 25.5, 1.9, 1.9))                     # the news's player
        # M1 moved by our read; M2 stood, then moved; M3 never moved; M4 was gone at our read
        rows.append(quote(at, 'M1', 11, 'PTS', 14.5 if at == T(19) else 16.5, 1.9, 1.9))
        rows.append(quote(at, 'M2', 12, 'REB', 6.5 if at < T(22) else 7.5, 1.9, 1.9))
        rows.append(quote(at, 'M3', 13, 'AST', 4.5, 1.9, 1.9))
        if at == T(19):
            rows.append(quote(at, 'M4', 14, 'PRA', 20.5, 1.9, 1.9))
        rows.append(quote(at, 'O1', 21, 'PTS', 10.5, 1.9, 1.9))                    # the other team
    return pd.DataFrame(rows)


TEAM_OF = {1: 'lal', 11: 'lal', 12: 'lal', 13: 'lal', 14: 'lal', 21: 'sa'}


def event(kind='out'):
    return next(pd.DataFrame([{'night': NIGHT, 'seen_at': T(20), 'prev_at': T(19), 'team': 'lal',
                               'player_id_ESPN': 1, 'name': 'A', 'kind': kind}]).itertuples())


def test_reactions_say_which_teammate_lines_moved_and_when():
    c = reactions(event(), game(), TEAM_OF)
    kinds = dict(zip(c['lines']['player'], c['lines']['kind']))
    assert kinds == {'M1': MOVED_EARLY, 'M2': MOVED_LATER, 'M3': NEVER, 'M4': WITHDRAWN}
    minutes = dict(zip(c['lines']['player'], c['lines']['minutes to move']))
    assert minutes['M1'] == 2 and minutes['M2'] == 120 and pd.isna(minutes['M3'])
    assert c['own'] == 'still offered at our first read' and c['others'] == (0, 1)


def test_no_reactions_when_the_game_wasnt_read_at_the_news_slot():
    late = game()
    late = late[late['at'] != T(20, 2)]                                           # next read only at 21:00
    assert reactions(event(), late, TEAM_OF) is None


def test_signals_are_the_lines_that_still_stood_on_the_side_fixed_by_the_news():
    c = reactions(event(), game(), TEAM_OF)
    out = signal_rows(event(), c)
    assert sorted(out['name_ESPN']) == ['M2', 'M3'] and (out['side'] == 'Over').all()
    assert (out['at'] == T(20, 2)).all() and (out['hypothesis'] == 'H4').all() and out['clears'].all()
    assert (signal_rows(event('return'), c)['side'] == 'Under').all()


def test_cases_find_the_events_game_by_team():
    teams = pd.DataFrame({'home': ['lal'], 'away': ['sa']}, index=['g1'])
    events = pd.DataFrame([event()._asdict()]).drop(columns='Index')
    found = cases(events, game(), teams, TEAM_OF)
    assert len(found) == 1 and found[0][1]['after'] == T(20, 2)
