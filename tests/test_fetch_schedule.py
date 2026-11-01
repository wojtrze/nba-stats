"""Run with: python -m pytest tests"""
import os
from datetime import datetime, timedelta, timezone

import pandas as pd

import fetch_loop
import fetch_schedule
from fetch_schedule import due, night_slots

UTC = timezone.utc
TIP = datetime(2026, 11, 3, 0, 0, tzinfo=UTC)
M = lambda n: timedelta(minutes=n)


def kinds(slots):
    return [(s.at, s.kind) for s in slots]


def test_last_hour_of_one_tip_and_hourly_before():
    slots = night_slots([(1, TIP), (2, TIP)], TIP - timedelta(hours=3, minutes=30))
    last_hour = [s for s in slots if any(k.startswith('T-') for k in s.kinds)]
    assert [s.at for s in last_hour] == [TIP - M(m) for m in (60, 40, 20, 10, 5)]
    assert all(s.rotowire and s.event_ids == {1, 2} for s in last_hour)
    assert [s.at for s in slots if s.kinds == ('hourly',)] == [TIP - timedelta(hours=3), TIP - timedelta(hours=2)]
    assert last_hour[0].priced and not last_hour[1].priced            # T-60 priced; the hourly at T-60 folded in
    assert 'hourly' in last_hour[0].kinds and last_hour[0].all_events


def test_two_tips_half_an_hour_apart_merge_close_slots():
    slots = night_slots([(1, TIP), (2, TIP + M(30))], TIP - M(61))
    # T-10 of the first tip (23:50) and T-40 of the second (23:50) are one run over both games
    merged = [s for s in slots if s.at == TIP - M(10)]
    assert len(merged) == 1 and set(merged[0].kinds) == {'T-10', 'T-40'} and merged[0].event_ids == {1, 2}
    assert all(b.at - a.at > fetch_schedule.MERGE_GAP for a, b in zip(slots, slots[1:]))


def test_hourly_stops_at_the_last_tip_and_takes_games_within_24h():
    tomorrow = TIP + timedelta(hours=30)
    slots = night_slots([(1, TIP), (9, tomorrow)], TIP - timedelta(hours=2, minutes=30))
    first = slots[0]
    assert first.kinds == ('hourly',) and first.event_ids == {1}       # tomorrow's game isn't within 24 h yet
    assert max(s.at for s in slots) < tomorrow


def test_started_games_and_past_slots_are_left_out():
    assert night_slots([(1, TIP)], TIP + M(1)) == []
    assert [s.kind for s in night_slots([(1, TIP)], TIP - M(15))] == ['T-10', 'T-5']


def test_late_slots_are_skipped_not_caught_up():
    slots = night_slots([(1, TIP)], TIP - M(61))
    slot, skipped = due(slots, TIP - M(9), None)                        # woke at T-9: T-60..T-20 missed
    assert slot.kind == 'T-10' and [s.kind for s in skipped][-1] == 'T-20'
    slot, skipped = due(slots, TIP - M(9), slot.at)                     # once run, nothing is due again
    assert slot is None


def test_quotes_record_only_changes_and_withdrawals(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    event = {'home': 'bos', 'away': 'ny', 'event_id': 7, 'start_time': '2026-11-03T00:00:00Z'}

    def offers(over, line=27.5, game=1.5, also_ast=True):
        props = [{'name': 'Tatum, Jayson', 'name_ESPN': 'JaysonTatum', 'bet_type': 'PTS', 'line': line,
                  'over_under': s, 'odds': o, **event} for s, o in (('Over', over), ('Under', 1.85))]
        if also_ast:
            props += [{'name': 'Tatum, Jayson', 'name_ESPN': 'JaysonTatum', 'bet_type': 'AST', 'line': 5.5,
                       'over_under': s, 'odds': 1.9, **event} for s in ('Over', 'Under')]
        return {'props': props, 'game_odds': [{'market': 'ML', 'side': 'home', 'line': None, 'odds': game, **event}],
                'fetched': [7], 'events': [{'event_id': 7, 'start_time': event['start_time']}]}

    assert fetch_loop.save_quotes(offers(1.9), '2026-11-02T22:00:00Z', 'T-60') == \
        {'prop_quotes': 2, 'game_quotes': 1, 'event_fetches': 1}
    assert fetch_loop.save_quotes(offers(1.9), '2026-11-02T22:20:00Z', 'T-40')['prop_quotes'] == 0
    counts = fetch_loop.save_quotes(offers(2.0, also_ast=False), '2026-11-02T22:40:00Z', 'T-20')
    assert counts['prop_quotes'] == 2                                   # PTS repriced, AST withdrawn
    quotes = pd.read_csv(os.path.join('data', '2026', 'superbet_prop_quotes.csv'))
    last = quotes[quotes['fetched_at'] == '2026-11-02T22:40:00Z'].set_index('bet_type')
    assert last.loc['PTS', 'over_odds'] == 2.0 and pd.isna(last.loc['AST', 'over_odds'])
    fetches = pd.read_csv(os.path.join('data', '2026', 'superbet_event_fetches.csv'))
    assert list(fetches['run_kind']) == ['T-60', 'T-40', 'T-20']        # every read is on record, changed or not


def test_one_worker_at_a_time(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    now = datetime(2026, 11, 2, 20, tzinfo=UTC)
    assert fetch_loop.claim_worker('a', now)
    assert not fetch_loop.claim_worker('b', now + M(1))
    assert fetch_loop.claim_worker('b', now + M(4))                     # a's heartbeat went stale
    fetch_loop.release_worker('a')                                      # not a's any more: kept
    assert not fetch_loop.claim_worker('a', now + M(5))
