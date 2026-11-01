"""The stars' record (tracking.star_lines, star_scorecard, paper_accumulators). Run with: python -m pytest
dashboard"""
import numpy as np
import pandas as pd
import pytest

from tracking import EVERY_LINE, RECOMPUTED, RECORDED, paper_accumulators, star_lines, star_scorecard

START = '2026-10-22T23:30:00Z'   # 19:30 ET on Oct 22


def _snap(name, event, model_pct, fetched='2026-10-22T20:00:00Z', start=START, **kw):
    return {'fetched_at': fetched, 'name': name, 'name_ESPN': name, 'event_id': event, 'home': f'h{event}',
            'away': f'a{event}', 'start_time': start, 'bet_type': 'PTS', 'line': 20.5, 'over_odds': 1.9,
            'under_odds': 1.9, 'pick': 'Over', 'model_pct': model_pct, 'market_over_pct': 50.0, 'red_flag': ''} | kw


def test_older_nights_are_rated_again_from_what_the_fetch_saved():
    snaps = pd.DataFrame([_snap('A', 1, 56.0), _snap('B', 2, 54.0), _snap('C', 3, 52.0, red_flag='Too few games'),
                          # a later fetch of A before tip-off is the one judged; one after tip-off is ignored
                          _snap('A', 1, 58.0, fetched='2026-10-22T22:00:00Z'),
                          _snap('A', 1, 10.0, fetched='2026-10-23T00:00:00Z')])
    lines = star_lines(snaps).set_index('name_ESPN')
    assert set(lines.index) == {'A', 'B', 'C'} and (lines['origin'] == RECOMPUTED).all()
    assert lines.loc['A', 'model_pct'] == 58.0 and lines.loc['A', 'stars'] > lines.loc['B', 'stars']
    assert lines.loc['C', 'stars'] == 0                                 # its saved red flag
    assert lines['side market %'].tolist() == [50.0, 50.0, 50.0]


def test_a_night_with_saved_stars_keeps_them():
    snaps = pd.DataFrame([_snap('A', 1, 52.0, stars=3, night_rank=2, eval_side='Under', ev_net_100=-15.0),
                          _snap('B', 2, 51.0, stars=4, night_rank=1, eval_side='Over', ev_net_100=-14.0),
                          _snap('C', 3, 70.0, stars=np.nan, night_rank=np.nan, eval_side='Over', ev_net_100=-1.0)])
    lines = star_lines(snaps).set_index('name_ESPN')
    assert (lines['origin'] == RECORDED).all() and lines.loc['B', 'stars'] == 4
    assert pd.isna(lines.loc['C', 'stars'])                             # saved without a rating: stays so
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


def test_scorecard_per_level_against_the_price_and_every_line():
    s = _settled([{'stars': 4, 'result': 'win'}, {'stars': 4, 'result': 'loss'}, {'stars': 3, 'result': 'win'},
                  {'stars': 1, 'result': 'loss'}, {'stars': 1, 'result': 'push'},
                  {'stars': pd.NA, 'result': 'loss'}])
    s['stars'] = s['stars'].astype('Int64')
    card = star_scorecard(s).set_index('stars')
    assert card.loc[4, 'bets'] == 2 and card.loc[4, 'hit %'] == 50.0
    assert card.loc[4, 'won − price pp'] == 0.0
    assert card.loc[4, 'ROI % std'] == pytest.approx(100 * (0.88 * 1.9 - 1 - 1) / 2)
    assert card.loc[EVERY_LINE, 'bets'] == 5             # the push is left out, the unrated line counts here
    assert card.loc[5, 'bets'] == 0
    assert card.loc['4★ − 1★', 'won − price pp'] == pytest.approx(50.0)  # 4★ 50% − 1★ 0%, at a 50% price


def test_paper_accumulator_takes_the_tax_once_and_needs_every_leg():
    s = _settled([{'stars': 4, 'night_rank': 1, 'result': 'win', 'odds': 2.0},
                  {'stars': 4, 'night_rank': 2, 'result': 'win', 'odds': 1.5},
                  {'stars': 4, 'night_rank': 3, 'result': 'push', 'odds': 1.8},
                  {'stars': 4, 'night_rank': 4, 'result': 'loss', 'odds': 1.9},
                  # a night with a leg still pending is left out
                  {'game_date': pd.Timestamp('2026-10-23'), 'stars': 4, 'night_rank': 1, 'result': 'win'},
                  {'game_date': pd.Timestamp('2026-10-23'), 'stars': 4, 'night_rank': 2, 'result': None,
                   'status': 'pending'},
                  {'game_date': pd.Timestamp('2026-10-23'), 'stars': 4, 'night_rank': 3, 'result': 'win'}])
    ako = paper_accumulators(s)
    assert len(ako) == 1 and ako.loc[0, 'result'] == 'win'
    assert ako.loc[0, 'odds'] == pytest.approx(3.0)                 # the push counts as odds 1, rank 4 isn't a leg
    assert ako.loc[0, 'profit std'] == pytest.approx(0.88 * 3.0 - 1)
    lost = paper_accumulators(_settled([{'stars': 4, 'night_rank': k, 'result': r}
                                        for k, r in enumerate(['win', 'loss', 'win'], 1)]))
    assert lost.loc[0, 'profit std'] == -1.0


def test_nothing_to_record():
    assert star_lines(pd.DataFrame()).empty
    assert star_scorecard(pd.DataFrame()).empty and paper_accumulators(pd.DataFrame()).empty
