import pandas as pd

from backtest.news_lag_cases import find_events

NIGHT = pd.Timestamp('2026-11-09')
T = lambda h, m=0: pd.Timestamp('2026-11-09', tz='UTC') + pd.Timedelta(hours=h, minutes=m)


def version(*rows):
    return pd.DataFrame([{'player_id_ESPN': pid, 'team': team, 'play_pct': pct, 'name': name}
                         for pid, team, pct, name in rows])


def test_a_regular_going_out_between_two_close_versions_is_news():
    versions = {NIGHT: [(T(19), version((1, 'lal', 100, 'A'), (2, 'lal', 50, 'B'), (3, 'sa', 100, 'C'))),
                        (T(20), version((1, 'lal', 0, 'A'), (2, 'lal', 0, 'B'), (3, 'sa', 100, 'C'),
                                        (4, 'lal', 0, 'D')))]}
    events = find_events(versions, {NIGHT: {1, 2, 4}})
    # A and B were listed playing; D wasn't listed while his team was (healthy), so his Out is news too
    assert events['player_id_ESPN'].tolist() == [1, 2, 4]
    assert (events['seen_at'] == T(20)).all() and (events['prev_at'] == T(19)).all()


def test_no_news_from_bench_players_a_long_gap_or_an_already_out_player():
    versions = {NIGHT: [(T(10), version((1, 'lal', 100, 'A'), (2, 'lal', 0, 'B'))),
                        (T(15), version((1, 'lal', 0, 'A'), (2, 'lal', 0, 'B'))),          # 5 h gap: an outage
                        (T(15, 30), version((1, 'lal', 0, 'A'), (2, 'lal', 0, 'B'), (5, 'lal', 0, 'E')))]}
    assert find_events(versions, {NIGHT: {1, 2}}).empty                  # E isn't a regular; B was already out
