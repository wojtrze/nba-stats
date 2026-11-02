"""Run with: python -m pytest backtest"""
import numpy as np
import pandas as pd

import backtest  # noqa: F401  (puts dashboard/ on the path)
from backtest.mispricing_eval import offers, settle, signals, takeable, verdict

TIP = '2026-11-03T00:00:00Z'


def _fetches(*times, event=1):
    return pd.DataFrame({'fetched_at': list(times), 'event_id': event, 'start_time': TIP})


def _quotes(rows):
    return pd.DataFrame(rows, columns=['fetched_at', 'event_id', 'name_ESPN', 'bet_type', 'line', 'over_odds',
                                       'under_odds'])


def test_offers_rebuilds_every_read_from_the_changes():
    reads = _fetches('2026-11-02T18:00:00Z', '2026-11-02T20:00:00Z', '2026-11-02T22:00:00Z',
                     '2026-11-02T23:00:00Z', '2026-11-03T01:00:00Z')        # the last one after tip-off
    quotes = _quotes([('2026-11-02T18:00:00Z', 1, 'A', 'PTS', 20.5, 1.85, 1.85),
                      ('2026-11-02T22:00:00Z', 1, 'A', 'PTS', 21.5, 1.85, 1.85),
                      ('2026-11-02T23:00:00Z', 1, 'A', 'PTS', np.nan, np.nan, np.nan),   # withdrawn
                      ('2026-11-02T20:00:00Z', 1, 'A', 'REB', 5.5, 1.9, 1.8)])
    o = offers(pd.DataFrame(), quotes, reads)
    pts = o[o['bet_type'] == 'PTS'].set_index('at')['line']
    assert pts.tolist() == [20.5, 20.5, 21.5]       # carried over the read without a change, gone when withdrawn
    reb = o[o['bet_type'] == 'REB']
    assert len(reb) == 3 and reb['at'].min() == pd.Timestamp('2026-11-02T20:00:00Z')   # not before it was listed
    assert (o['source'] == 'schedule').all()


def test_offers_takes_snapshots_only_for_games_the_schedule_didnt_read():
    props = pd.DataFrame({'fetched_at': ['2026-11-02T18:00:00Z'] * 2 + ['2026-11-03T02:00:00Z'],
                          'start_time': [TIP, TIP, TIP], 'event_id': [1, 2, 2], 'name_ESPN': 'B',
                          'bet_type': 'PTS', 'line': 10.5, 'over_odds': 1.85, 'under_odds': 1.85})
    quotes = _quotes([('2026-11-02T18:00:00Z', 1, 'A', 'PTS', 20.5, 1.85, 1.85)])
    o = offers(props, quotes, _fetches('2026-11-02T18:00:00Z'))
    assert set(zip(o['event_id'], o['source'])) == {(1, 'schedule'), (2, 'snapshot')}
    assert len(o) == 2                               # the snapshot after tip-off is left out


def _offered():
    at = pd.to_datetime(['2026-11-02T18:00:00Z', '2026-11-02T20:00:00Z'], utc=True)
    return pd.DataFrame({'at': at, 'event_id': 1, 'name_ESPN': 'A', 'bet_type': 'PTS', 'line': [20.5, 20.5],
                         'over_odds': [1.85, 1.80], 'under_odds': [1.85, 1.90]})


def _rows(**over):
    base = {'at': pd.Timestamp('2026-11-02T18:00:00Z'), 'event_id': 1, 'name_ESPN': 'A', 'bet_type': 'PTS',
            'line': 20.5, 'side': 'Under', 'odds': 1.85}
    return pd.DataFrame([base | over])


def test_takeable_needs_the_same_line_and_odds_not_worse_at_the_next_read():
    offered = _offered()
    assert takeable(_rows(), offered).tolist() == ['yes']                 # Under 1.85, then 1.90
    assert takeable(_rows(side='Over'), offered).tolist() == ['no']       # Over 1.85, then 1.80
    late = _rows(at=pd.Timestamp('2026-11-02T20:00:00Z'), odds=1.90)
    assert takeable(late, offered).tolist() == ['unchecked']              # the game's last read


def test_settle_sums_a_combo_and_leaves_a_player_who_didnt_play_unsettled():
    logs = pd.DataFrame({'player_id_ESPN': pd.array([7], dtype='Int64'), 'Date': [pd.Timestamp('2026-11-02')],
                         'PTS': [20], 'REB': [8], 'AST': [5]})
    rows = pd.DataFrame({'player_id_ESPN': pd.array([7, 7, 8], dtype='Int64'),
                         'night': pd.Timestamp('2026-11-02'), 'bet_type': ['ARP', 'PTS', 'PTS'],
                         'line': [32.5, 20.5, 20.5], 'side': ['Over', 'Under', 'Over']})
    s = settle(rows, logs)
    assert s['actual'].tolist()[:2] == [33, 20]
    assert s['won'].tolist()[:2] == [1.0, 1.0] and np.isnan(s['won'].iloc[2])


def test_signals_counts_each_side_once_at_its_first_takeable_read():
    offered = _offered()
    common = {'night': pd.Timestamp('2026-11-02'), 'event_id': 1, 'name_ESPN': 'A', 'player_id_ESPN': 7,
              'hypothesis': 'H2', 'bet_type': 'PTS', 'line': 20.5, 'over_odds': 1.85, 'under_odds': 1.85,
              'p_ours': 0.7, 'p_book': 0.5, 'gap_pp': 20.0}
    outputs = pd.DataFrame([common | {'at': offered['at'][0], 'side': 'Under', 'odds': 1.85, 'clears': True},
                            common | {'at': offered['at'][1], 'side': 'Under', 'odds': 1.90, 'clears': True},
                            common | {'at': offered['at'][0], 'side': 'Over', 'odds': 1.85, 'clears': False}])
    outputs['player_id_ESPN'] = outputs['player_id_ESPN'].astype('Int64')
    logs = pd.DataFrame({'player_id_ESPN': pd.array([7], dtype='Int64'), 'Date': [pd.Timestamp('2026-11-02')],
                         'PTS': [18], 'REB': [1], 'AST': [1]})
    s = signals(outputs, offered, logs)
    assert len(s) == 1 and s['taken'].iloc[0] == 'yes' and s['at'].iloc[0] == offered['at'][0]
    assert s['profit std'].iloc[0] == 0.88 * 1.85 - 1


def _r(**over):
    base = {'nights': 12, 'signals': 80, 'with a close': 80, 'CLV after tax %': 1.0, 'CLV low': -1.0,
            'CLV high': 3.0, 'ROI after tax %': 1.0, 'ROI low': -20.0, 'ROI high': 20.0}
    return base | over


def test_verdict_follows_the_registry():
    assert verdict(_r(nights=9))['verdict'] == 'wait'
    assert verdict(_r(signals=2))['verdict'] == 'no signals'
    assert verdict(_r(**{'CLV low': 0.5}))['verdict'] == 'admitted'
    assert verdict(_r(signals=40, **{'CLV low': 0.5}))['verdict'] == 'wait'           # too few to admit
    assert verdict(_r(**{'CLV high': -0.5}))['verdict'] == 'rejected'
    assert verdict(_r(signals=150, **{'CLV after tax %': -0.1}))['verdict'] == 'rejected'
    assert verdict(_r(**{'CLV low': 0.5, 'ROI high': -1.0}))['verdict'] == 'wait'     # the ranges disagree
    no_close = _r(**{'with a close': 0, 'CLV low': np.nan, 'CLV high': np.nan, 'CLV after tax %': np.nan})
    assert verdict(no_close | {'signals': 150, 'ROI after tax %': -2.0})['verdict'] == 'rejected'
