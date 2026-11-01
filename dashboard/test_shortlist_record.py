"""The shortlist's record (tracking.shortlist_lines, tier_scorecard, paper_accumulators). Run with: python -m pytest
dashboard"""
import numpy as np
import pandas as pd
import pytest

from tracking import RECOMPUTED, RECORDED, paper_accumulators, shortlist_lines, tier_scorecard

START = '2026-10-22T23:30:00Z'   # 19:30 ET on Oct 22


def _snap(name, event, model_pct, fetched='2026-10-22T20:00:00Z', start=START, **kw):
    return {'fetched_at': fetched, 'name': name, 'name_ESPN': name, 'event_id': event, 'home': f'h{event}',
            'away': f'a{event}', 'start_time': start, 'bet_type': 'PTS', 'line': 20.5, 'over_odds': 1.9,
            'under_odds': 1.9, 'pick': 'Over', 'model_pct': model_pct, 'market_over_pct': 50.0, 'red_flag': ''} | kw


def test_older_nights_are_ranked_again_from_what_the_fetch_saved():
    snaps = pd.DataFrame([_snap('A', 1, 56.0), _snap('B', 2, 54.0), _snap('C', 3, 52.0, red_flag='Too few games'),
                          # a later fetch of A before tip-off is the one judged; one after tip-off is ignored
                          _snap('A', 1, 58.0, fetched='2026-10-22T22:00:00Z'),
                          _snap('A', 1, 10.0, fetched='2026-10-23T00:00:00Z')])
    lines = shortlist_lines(snaps)
    assert list(lines['name_ESPN']) == ['A', 'B'] and (lines['origin'] == RECOMPUTED).all()
    assert lines.loc[0, 'model_pct'] == 58.0 and list(lines['tier']) == ['top', 'top']
    assert lines['side market %'].tolist() == [50.0, 50.0]
    every = shortlist_lines(snaps, every_line=True)
    assert set(every['name_ESPN']) == {'A', 'B', 'C'} and every.set_index('name_ESPN').loc['C', 'tier'] == ''


def test_a_night_with_saved_tiers_keeps_them():
    snaps = pd.DataFrame([_snap('A', 1, 52.0, tier='look', night_rank=2, eval_side='Under', ev_net_100=-15.0),
                          _snap('B', 2, 51.0, tier='top', night_rank=1, eval_side='Over', ev_net_100=-14.0),
                          _snap('C', 3, 70.0, tier=np.nan, night_rank=np.nan, eval_side='Over', ev_net_100=-1.0)])
    lines = shortlist_lines(snaps).set_index('name_ESPN')
    assert set(lines.index) == {'A', 'B'} and (lines['origin'] == RECORDED).all()
    # the side settled is the evaluated side the fetch saved
    assert lines.loc['A', 'pick'] == 'Under' and lines.loc['A', 'side market %'] == 50.0


def _settled(rows):
    base = {'game_date': pd.Timestamp('2026-10-22'), 'name': 'A', 'pick': 'Over', 'line': 20.5, 'bet_type': 'PTS',
            'odds': 1.9, 'side market %': 50.0, 'status': 'settled'}
    out = pd.DataFrame([base | r for r in rows])
    out['profit'] = np.select([out['result'] == 'win', out['result'] == 'loss'], [out['odds'] - 1, -1.0], 0.0)
    out['profit std'] = np.select([out['result'] == 'win', out['result'] == 'loss'], [0.88 * out['odds'] - 1, -1.0],
                                  0.0)
    return out


def test_scorecard_per_tier_against_the_price_and_every_line():
    s = _settled([{'tier': 'top', 'result': 'win'}, {'tier': 'top', 'result': 'loss'},
                  {'tier': 'look', 'result': 'win'}, {'tier': '', 'result': 'loss'}, {'tier': '', 'result': 'push'}])
    card = tier_scorecard(s).set_index('tier')
    assert card.loc['top', 'bets'] == 2 and card.loc['top', 'hit %'] == 50.0
    assert card.loc['top', 'won − price pp'] == 0.0
    assert card.loc['top', 'ROI % std'] == pytest.approx(100 * (0.88 * 1.9 - 1 - 1) / 2)
    assert card.loc['every line', 'bets'] == 4          # the push is left out


def test_paper_accumulator_takes_the_tax_once_and_needs_every_leg():
    s = _settled([{'tier': 'top', 'night_rank': 1, 'result': 'win', 'odds': 2.0},
                  {'tier': 'top', 'night_rank': 2, 'result': 'win', 'odds': 1.5},
                  {'tier': 'top', 'night_rank': 3, 'result': 'push', 'odds': 1.8},
                  {'tier': 'top', 'night_rank': 4, 'result': 'loss', 'odds': 1.9},
                  # a night with a leg still pending is left out
                  {'game_date': pd.Timestamp('2026-10-23'), 'tier': 'top', 'night_rank': 1, 'result': 'win'},
                  {'game_date': pd.Timestamp('2026-10-23'), 'tier': 'top', 'night_rank': 2, 'result': None,
                   'status': 'pending'},
                  {'game_date': pd.Timestamp('2026-10-23'), 'tier': 'top', 'night_rank': 3, 'result': 'win'}])
    ako = paper_accumulators(s)
    assert len(ako) == 1 and ako.loc[0, 'result'] == 'win'
    assert ako.loc[0, 'odds'] == pytest.approx(3.0)                 # the push counts as odds 1, rank 4 isn't a leg
    assert ako.loc[0, 'profit std'] == pytest.approx(0.88 * 3.0 - 1)
    lost = paper_accumulators(_settled([{'tier': 'top', 'night_rank': k, 'result': r}
                                        for k, r in enumerate(['win', 'loss', 'win'], 1)]))
    assert lost.loc[0, 'profit std'] == -1.0


def test_nothing_to_record():
    assert shortlist_lines(pd.DataFrame()).empty
    assert tier_scorecard(pd.DataFrame()).empty and paper_accumulators(pd.DataFrame()).empty
