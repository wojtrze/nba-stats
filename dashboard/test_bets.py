"""Run with: python -m pytest dashboard"""
import numpy as np
import pandas as pd
import pytest

from bets import as_snapshot_rows, describe, kelly_stake, load_bets, save_bets, slip_warnings, staking_chance
from tracking import settle_games, settle_props


def _prop(**kw):
    bet = {'kind': 'prop', 'event_id': 1, 'start_time': '2026-10-22T23:30:00Z', 'home': 'bos', 'away': 'nyk',
           'name': 'A Player', 'name_ESPN': 'APlayer', 'player_id_ESPN': 7, 'bet_type': 'PTS', 'side': 'Over',
           'line': 20.5, 'odds': 1.9, 'stake': 10.0, 'model_pct': 60.0, 'edge_pp': 7.4, 'edge_low': 1.0}
    return bet | kw


def _game(**kw):
    bet = {'kind': 'game', 'event_id': 1, 'start_time': '2026-10-22T23:30:00Z', 'home': 'bos', 'away': 'nyk',
           'market': 'TOTAL', 'side': 'over', 'team': None, 'line': 210.5, 'odds': 1.9, 'stake': 10.0,
           'model_pct': 60.0, 'edge_pp': 7.4}
    return bet | kw


def test_kelly_stake():
    # 60% at 2.0: full Kelly 20%, a quarter 5%
    assert kelly_stake(0.6, 2.0, 1000) == 50
    assert kelly_stake(0.6, 2.0, 1000, cap=0.02) == 20
    assert kelly_stake(0.4, 2.0, 1000) == 0
    assert kelly_stake(np.nan, 2.0, 1000) == 0


def test_staking_chance_uses_the_low_end_for_props():
    assert staking_chance(_prop(model_pct=60.0, edge_pp=7.4, edge_low=1.0)) == pytest.approx(0.536)
    assert kelly_stake(staking_chance(_prop(edge_low=-3.0)), 1.9, 1000) == 0      # 🟡: no stake
    assert np.isnan(staking_chance(_game()))                                       # an uncalibrated game model
    assert kelly_stake(staking_chance(_game()), 1.9, 1000) == 0


def test_no_stake_on_an_uncalibrated_prop():
    assert np.isnan(staking_chance(_prop(edge_low=1.0), calibrated=False))
    assert kelly_stake(staking_chance(_prop(edge_low=1.0), calibrated=False), 1.9, 1000) == 0


def test_describe():
    assert describe(_prop()) == "A Player Over 20.5 PTS"
    assert describe(_game()) == "NYK @ BOS: Total over 210.5"
    assert describe(_game(market='SPREAD', side='away', team='nyk', line=5.5)) == "NYK @ BOS: Handicap NYK +5.5"


def test_slip_warnings():
    slip = [_prop(), _prop(bet_type='PR', line=26.5), _game(), _prop(side='Under')]
    warnings = slip_warnings(slip, bankroll=100)
    assert any('3 bets on one player' in w for w in warnings)
    assert any('both Over and Under' in w for w in warnings)
    assert any('3 Overs all need a high-scoring game' in w for w in warnings)
    assert any('4 bets on one game' in w for w in warnings)
    assert any('40% of the bankroll' in w for w in warnings)
    assert slip_warnings([_prop()], bankroll=1000) == []


def test_save_and_settle_my_bets(tmp_path):
    path = str(tmp_path / 'my_bets.csv')
    assert save_bets([_prop(), _game()], path) == 2
    saved = load_bets(path)
    assert len(saved) == 2 and saved['bet_id'].notna().all()
    rows = as_snapshot_rows(saved)
    logs = pd.DataFrame([{'player_id_ESPN': 7, 'player_name_ESPN': 'APlayer', 'Date': pd.Timestamp('2026-10-22'),
                          'PTS': 25}])
    games = pd.DataFrame([{'date': pd.Timestamp('2026-10-22'), 'home': 'bos', 'away': 'nyk', 'home_score': 110,
                           'away_score': 104}])
    prop = settle_props(pd.DataFrame(), logs, games, bets=rows['prop']).iloc[0]
    assert prop['result'] == 'win' and prop['profit'] == pytest.approx(0.9) and prop['stake'] == 10
    game = settle_games(pd.DataFrame(), games, bets=rows['game']).iloc[0]
    assert game['result'] == 'win' and game['bet_id'] == saved['bet_id'].iloc[1]
