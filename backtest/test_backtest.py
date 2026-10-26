"""Run with: python -m pytest backtest"""
import numpy as np
import pandas as pd
import pytest

import backtest  # noqa: F401  (puts dashboard/ on the path)
from backtest.data_2022 import add_game_columns, espn_name, fix_teams, mark_main_lines, pair_sides
from backtest.run import known_absences, price_season, side_result
from models import prepare_logs


def test_espn_name():
    assert espn_name('J.Brown') == 'JaylenBrown'
    assert espn_name('LukaDončić') == 'LukaDoncic'
    assert espn_name('StephenCurry') == 'StephenCurry'


def test_fix_teams_moves_a_traded_players_old_games():
    # the trade: player 9 is listed with 'bkn' (his final team) for a game 'dal' played against 'PHX'
    logs = pd.DataFrame({'Date': pd.to_datetime(['2023-01-01'] * 4 + ['2023-03-01'] * 2),
                         'OPP': ['PHX', 'PHX', 'PHX', 'DAL', 'BOS', 'BOS'],
                         'team': ['dal', 'dal', 'bkn', 'phx', 'bkn', 'bkn'],
                         'player_id_ESPN': [1, 2, 9, 3, 9, 4]})
    fixed, moved = fix_teams(logs)
    assert moved == 1
    assert fixed.loc[2, 'team'] == 'dal'
    assert fixed.loc[4, 'team'] == 'bkn'          # after the trade, unchanged


def test_add_game_columns():
    logs = pd.DataFrame({'Date': pd.to_datetime(['2022-11-10'] * 7 + ['2023-04-12', '2023-04-20']),
                         'team': ['por'] * 6 + ['cha', 'lal', 'lal'], 'OPP': ['CHA'] * 6 + ['POR', 'MIN', 'DEN'],
                         'MIN': [30, 35, 10, 20, 25, 28, 40, 30, 30]})
    out = add_game_columns(logs)
    assert out['game_id'].iloc[0] == '2022-11-10_cha_por' == out['game_id'].iloc[6]   # same id from both sides
    assert out['season_type'].tolist()[-3:] == ['regular', 'playin', 'post']
    assert out['starter'].iloc[:6].tolist() == [True, True, False, True, True, True]   # all but the 10-minute one


def test_pair_sides_and_main_line():
    offers = pd.DataFrame({'player_ESPN': 'A', 'bet_type': 'PTS', 'home': 'bos', 'away': 'ny',
                           'closed_date': '2022-11-11T00:30:00Z', 'actual': 25.0,
                           'line': [20.5, 20.5, 22.5, 22.5, 24.5],
                           'over_under': ['Over', 'Under', 'Over', 'Under', 'Over'],
                           'odds': [1.6, 2.3, 1.9, 1.9, 2.4]})
    lines = pair_sides(offers)
    assert lines['line'].tolist() == [20.5, 22.5]     # 24.5 has no Under: dropped
    assert lines['over_odds'].tolist() == [1.6, 1.9] and lines['under_odds'].tolist() == [2.3, 1.9]
    lines = lines.assign(player_id_ESPN=1, game_date=pd.Timestamp('2022-11-10'))
    assert mark_main_lines(lines)['main'].tolist() == [False, True]


def _season(days=12, extreme_day=None):
    """Player 1 (G) scores 10 a game for 'bos' vs 'ny'; on extreme_day he scores 60. Player 2 plays every game but
    the last (a rotation player who misses it)."""
    rows = []
    for i in range(days):
        date = pd.Timestamp('2022-11-01') + pd.Timedelta(days=i)
        gid = f"{date:%Y-%m-%d}_bos_ny"
        pts = 60.0 if date == extreme_day else 10.0
        rows.append({'player_id_ESPN': 1, 'Date': date, 'PTS': pts, 'MIN': 30.0, 'game_id': gid})
        if i < days - 1:
            rows.append({'player_id_ESPN': 2, 'Date': date, 'PTS': 15.0, 'MIN': 32.0, 'game_id': gid})
    logs = pd.DataFrame(rows)
    return logs.assign(team='bos', OPP='NY', type='home', REB=5.0, AST=3.0, season_id=2022, season_type='regular',
                       position='G', starter=True, player_display_name=logs['player_id_ESPN'].astype(str),
                       player_name_ESPN=logs['player_id_ESPN'].map({1: 'One', 2: 'Two'}), **{'3PM': 1.0, 'FGA': 10.0})


def _line(day):
    return pd.DataFrame([{'name': 'One', 'name_ESPN': 'One', 'player_ESPN': 'One', 'home': 'bos', 'away': 'ny',
                          'bet_type': 'PTS', 'line': 20.5, 'event_id': 'e', 'start_time': '2022-11-12T00:00:00Z',
                          'closed_date': '2022-11-12T00:00:00Z', 'over_odds': 1.9, 'under_odds': 1.9,
                          'player_id_ESPN': 1, 'game_date': day, 'main': True, 'file_actual': 60.0}])


def test_no_look_ahead_the_game_itself_is_not_used():
    day = pd.Timestamp('2022-11-11')
    logs = prepare_logs(_season(extreme_day=day))
    out = price_season(logs, _line(day), 'none').iloc[0]
    assert out['games'] == 10 and out['avg'] == 10        # only the 10 games before the 11th
    assert out['best side'] == 'Under'                    # a 60-point night it can't know about
    assert out['actual'] == 60 and out['pick result'] == 'loss'


def test_known_absences_lists_the_missing_rotation_player():
    logs = prepare_logs(_season(days=12))
    out = known_absences(logs, pd.Timestamp('2022-11-12'), ['bos'])
    assert out['player_id_ESPN'].tolist() == [2] and out['play_pct'].tolist() == [0]
    assert known_absences(logs, pd.Timestamp('2022-11-11'), ['bos']).empty


def test_side_result_push_and_profit():
    t = pd.DataFrame({'actual': [25, 20, 15, 20], 'line': [20.5, 20.0, 20.5, 20.5]})
    r = side_result(t, pd.Series(['Over', 'Over', 'Over', np.nan]), pd.Series([1.9] * 4), 'x')
    assert r['x result'].tolist()[:3] == ['win', 'push', 'loss'] and pd.isna(r['x result'].iloc[3])
    assert r['x profit'].tolist()[:3] == pytest.approx([0.9, 0.0, -1.0])


# --- the dashboard's strategy tester ---

def _priced():
    return pd.DataFrame({
        'game_date': pd.to_datetime(['2022-11-10', '2022-11-10', '2022-12-01', '2022-12-01', '2023-01-05']),
        'name_ESPN': ['A', 'B', 'A', 'B', 'A'], 'bet_type': ['PTS', 'REB', 'PTS', 'PTS', 'AST'],
        'line': [20.5, 5.5, 20.5, 10.0, 4.5], 'actual': [25.0, 3.0, 18.0, 10.0, 6.0],
        'over_odds': [1.9, 2.0, 1.8, 1.9, 1.9], 'under_odds': [1.9, 1.8, 2.0, 1.9, 1.9],
        'avg': [22.0, 6.0, 19.0, 12.0, 4.0], 'avg L5': 1.0, 'proj avg': 1.0,
        'best side': ['Over', 'Under', 'Under', 'Over', 'Under'], 'edge pp': [6.0, 2.0, -1.0, 8.0, 3.0],
        'signal': ['🟢', '🟡', np.nan, '🟢', '🟡'], 'games': [8, 8, 20, 20, 30], 'main': [True, True, True, True, False]})


def test_filter_lines():
    from backtest.explore import filter_lines
    t = _priced()
    assert len(filter_lines(t)) == 4                                   # the alternative line is out
    assert len(filter_lines(t, main_only=False)) == 5
    assert filter_lines(t, players=['A'])['line'].tolist() == [20.5, 20.5]
    assert filter_lines(t, signals=['none'])['line'].tolist() == [20.5]
    assert len(filter_lines(t, min_edge=5)) == 2 and len(filter_lines(t, min_games=10)) == 2
    assert len(filter_lines(t, since='2022-12-01', until='2022-12-01')) == 2


def test_bets_totals_and_cumulative():
    from backtest.explore import bets, cumulative, totals
    t = _priced()[lambda d: d['main']]
    b = bets(t, 'model')
    assert b['bet result'].tolist() == ['win', 'win', 'win', 'push']
    s = totals(b)
    assert s['bets'] == 3 and s['pushes'] == 1 and s['hit %'] == 100
    assert s['profit'] == pytest.approx(0.9 + 0.8 + 1.0)
    assert s['ROI %'] == pytest.approx(100 * 2.7 / 4)                   # the push returns its stake
    assert cumulative(b)['total'].tolist() == pytest.approx([1.7, 2.7])
    unders = bets(t, 'under', side='Under')
    assert unders['bet side'].eq('Under').all() and len(bets(t, 'model', side='Over')) == 2
    assert bets(t, 'average')['bet side'].tolist() == ['Over', 'Over', 'Under', 'Over']


def test_lines_summary():
    from backtest.explore import lines_summary
    s = lines_summary(_priced()).set_index('bet_type')
    assert s.loc['PTS', 'lines'] == 3 and s.loc['PTS', 'over %'] == 50     # the 10.0 push is left out
    assert s.loc['PTS', 'actual − line'] == pytest.approx((4.5 - 2.5 + 0) / 3)


# --- calibration fit ---

def test_fit_recovers_known_coefficients():
    from backtest.calibrate import COEFS, apply, features, fit
    rng = np.random.default_rng(0)
    n = 40000
    market, model = rng.uniform(0.35, 0.65, n), rng.uniform(0.2, 0.8, n)
    over = rng.integers(0, 2, n).astype(bool)
    truth = {'a': 1.0, 'b': 0.25, 'c': -0.15, 'd': 0.02}
    won = (rng.uniform(size=n) < apply(truth, market, model, over)).astype(float)
    beta = fit(features(market, model, over), won)
    assert dict(zip(COEFS, beta)) == {k: pytest.approx(v, abs=0.05) for k, v in truth.items()}


def test_vectorised_apply_matches_metrics_calibrate():
    from backtest.calibrate import apply
    from metrics import calibrate
    coef = {'a': 0.9, 'b': 0.3, 'c': -0.1, 'd': 0.05}
    market, model, over = np.array([0.4, 0.55, np.nan]), np.array([0.6, 0.3, 0.7]), np.array([True, False, True])
    expected = [calibrate(p, m, 'Over' if o else 'Under', coef) for p, m, o in zip(model, market, over)]
    assert apply(coef, market, model, over) == pytest.approx(expected)


# --- Superbet lines, the 🟢 threshold and the refresh ---

def _snap(fetched, line, actual_night='2026-10-21', **kw):
    row = {'fetched_at': fetched, 'name': 'A', 'name_ESPN': 'APlayer', 'home': 'bos', 'away': 'ny', 'bet_type': 'PTS',
           'line': line, 'event_id': 1, 'start_time': f'{actual_night}T23:30:00Z', 'over_odds': 1.9,
           'under_odds': 1.9, 'player_id_ESPN': 7, 'pick': 'Under', 'edge_pp': -2.0, 'signal': '',
           'raw_over_pct': 55.0, 'raw_under_pct': 45.0, 'market_over_pct': 50.0}
    return row | kw


def _stats():
    logs = pd.DataFrame({'player_id_ESPN': [7], 'player_name_ESPN': ['APlayer'], 'Date': pd.to_datetime(['2026-10-21']),
                         'PTS': [25.0]})
    games = pd.DataFrame({'date': pd.to_datetime(['2026-10-21']), 'home': ['bos'], 'away': ['ny']})
    return logs, games


def test_superbet_lines_judges_the_last_fetch_before_tip_off():
    from backtest.calibrate import sides, superbet_lines
    logs, games = _stats()
    snaps = pd.DataFrame([_snap('2026-10-21T10:00:00Z', 19.5),
                          _snap('2026-10-21T20:00:00Z', 20.5, raw_over_pct=60.0),
                          _snap('2026-10-21T23:45:00Z', 30.5),                                  # after tip-off
                          _snap('2026-10-21T20:00:00Z', 4.5, bet_type='AST'),                   # no AST stat: dropped
                          _snap('2026-10-21T20:00:00Z', 25.0, bet_type='PTS', event_id=2),      # a push
                          _snap('2026-10-22T20:00:00Z', 20.5, actual_night='2026-10-22', event_id=4),   # not played yet
                          _snap('2026-10-21T20:00:00Z', 9.5, bet_type='PTS', event_id=3, raw_over_pct=np.nan)])
    t = superbet_lines(snaps, logs, games)
    assert sorted(t['line']) == [20.5, 25.0] and (t['source'] == 'superbet').all()
    assert t.loc[t['line'] == 20.5, 'raw over %'].iloc[0] == 60.0 and t['actual'].tolist() == [25.0, 25.0]
    s = sides(t)
    assert len(s) == 2 and set(s['side']) == {'Over', 'Under'}                                 # the push is out
    assert s.loc[s['side'] == 'Over', 'won'].iloc[0] == 1.0


def _lines(n, over_won, market=50.0, raw_over=50.0, night='2026-10-21'):
    return pd.DataFrame({'game_date': pd.Timestamp(night), 'line': 10.5, 'actual': np.where(over_won, 12, 9),
                         'over_odds': 1.9, 'under_odds': 1.9, 'market over %': market, 'raw over %': raw_over,
                         'raw under %': 100 - raw_over, 'source': 'superbet'}, index=range(n))


def _spread(n, over_won, nights, raw_over=60.0):
    """n lines spread evenly over `nights` nights from Oct 1."""
    t = _lines(n, over_won, raw_over=raw_over)
    return t.assign(game_date=pd.Timestamp('2026-10-01') + pd.to_timedelta(np.arange(n) % nights, unit='D'))


def test_choose_green_edge_needs_many_nights_and_a_clear_margin_over_break_even():
    from backtest.calibrate import choose_green_edge, threshold_scan
    coef = {'a': 1.0, 'b': 1.0, 'c': 0.0, 'd': 0.0}                     # identity: the raw chance is the chance
    # the model says 60% Over (edge 60 − 52.6 = +7.4 pp); break-even at 1.9 is 52.6%
    good = _spread(150, np.arange(150) % 3 != 0, nights=12)            # won 2 of 3: 95% range 59–74%
    assert choose_green_edge(good, coef) == 1.0
    scan = threshold_scan(good, coef).set_index('edge ≥ pp')
    assert scan.loc[5, 'bets'] == 150 and scan.loc[5, 'nights'] == 12
    assert scan.loc[5, 'break-even %'] == pytest.approx(100 / 1.9) and scan.loc[5, 'expected %'] == pytest.approx(60)
    assert choose_green_edge(_spread(150, np.arange(150) % 3 != 0, nights=2), coef) is None      # 2 nights
    assert choose_green_edge(good.iloc[:30], coef) is None                                       # too few bets
    paid_but_unclear = _spread(60, np.arange(60) < 36, nights=12)      # won 60%, paid, but the range starts at 47%
    assert threshold_scan(paid_but_unclear, coef).set_index('edge ≥ pp').loc[1, 'ROI %'] > 0
    assert choose_green_edge(paid_but_unclear, coef) is None
    assert choose_green_edge(_spread(150, np.arange(150) % 3 == 0, nights=12), coef) is None    # the same edges lost
    assert choose_green_edge(good.iloc[0:0], coef) is None


def test_refresh_refits_only_after_a_new_night(tmp_path, monkeypatch):
    import json
    from backtest import calibrate
    rng = np.random.default_rng(1)
    nights = pd.concat([_lines(200, rng.uniform(size=200) < 0.5, night=f'2026-10-{d}') for d in (21, 22, 23)],
                       ignore_index=True)
    nights['market over %'] = rng.uniform(40, 60, len(nights))
    nights['raw over %'] = rng.uniform(30, 70, len(nights))
    nights['raw under %'] = 100 - nights['raw over %']
    monkeypatch.setattr(calibrate, '_superbet_sources', lambda logs, games: nights)
    out = tmp_path / 'calibration.json'
    missing_2022 = str(tmp_path / 'none.csv')
    assert calibrate.refresh(None, None, str(out), missing_2022)
    saved = json.loads(out.read_text())
    assert saved['superbet_through'] == '2026-10-23' and 'green_edge_pp' in saved
    assert (tmp_path / 'calibration.md').exists()
    assert not calibrate.refresh(None, None, str(out), missing_2022)                    # nothing new
    monkeypatch.setattr(calibrate, '_superbet_sources', lambda logs, games: (_ for _ in ()).throw(OSError("x")))
    assert not calibrate.refresh(None, None, str(out), missing_2022)                    # error: old file kept
    assert json.loads(out.read_text()) == saved


def test_lines_2022_only_of_the_current_model(tmp_path):
    from backtest.calibrate import LEGACY_2022_VERSION, lines_2022
    from nightly import MODEL_VERSION
    rows = pd.DataFrame({'game_date': ['2022-11-10'] * 3, 'variant': 'none', 'main': True, 'games': 10,
                         'line': [10.5, 11.5, 12.5]})
    legacy = tmp_path / 'legacy.csv'
    rows.to_csv(legacy, index=False)                                   # written before model_version was saved
    assert len(lines_2022(str(legacy), LEGACY_2022_VERSION)) == 3 and lines_2022(str(legacy), 'next').empty
    tagged = tmp_path / 'tagged.csv'
    rows.assign(model_version=[MODEL_VERSION, MODEL_VERSION, 'old']).to_csv(tagged, index=False)
    assert lines_2022(str(tagged))['line'].tolist() == [10.5, 11.5]


def test_refresh_refits_for_a_new_model_version_and_waits_for_its_lines(tmp_path, monkeypatch):
    import json
    from backtest import calibrate
    rng = np.random.default_rng(2)
    nights = pd.concat([_lines(200, rng.uniform(size=200) < 0.5, night=f'2026-10-{d}') for d in (21, 22, 23)],
                       ignore_index=True)
    nights['market over %'] = rng.uniform(40, 60, len(nights))
    nights['raw over %'] = rng.uniform(30, 70, len(nights))
    nights['raw under %'] = 100 - nights['raw over %']
    monkeypatch.setattr(calibrate, '_superbet_sources', lambda logs, games: nights)
    out, missing_2022 = tmp_path / 'calibration.json', str(tmp_path / 'none.csv')
    assert calibrate.refresh(None, None, str(out), missing_2022)
    assert json.loads(out.read_text())['model_version'] == calibrate.MODEL_VERSION
    assert not calibrate.refresh(None, None, str(out), missing_2022)                    # same model, nothing new
    monkeypatch.setattr(calibrate, 'MODEL_VERSION', 'next')
    monkeypatch.setattr(calibrate, '_superbet_sources', lambda logs, games: pd.DataFrame())
    before = out.read_text()
    assert not calibrate.refresh(None, None, str(out), missing_2022)    # no lines of the new model yet: kept
    assert out.read_text() == before
    monkeypatch.setattr(calibrate, '_superbet_sources', lambda logs, games: nights)
    assert calibrate.refresh(None, None, str(out), missing_2022)        # its lines are there: refitted for it
    assert json.loads(out.read_text())['model_version'] == 'next'


def test_game_lines_margin_free_chance_and_report():
    from backtest.calibrate import game_lines, game_report
    tip = '2026-10-21T23:30:00Z'

    def odd(fetched, market, side, line, odds, model):
        return {'fetched_at': fetched, 'market': market, 'side': side, 'line': line, 'odds': odds,
                'team': {'home': 'bos', 'away': 'ny'}.get(side), 'home': 'bos', 'away': 'ny', 'event_id': 1,
                'start_time': tip, 'model_pct': model, 'edge_pp': model - 100 / odds}
    snaps = pd.DataFrame([odd('2026-10-21T10:00:00Z', 'ML', 'home', None, 1.4, 70.0),        # superseded
                          odd('2026-10-21T10:00:00Z', 'ML', 'away', None, 2.9, 30.0),
                          odd('2026-10-21T20:00:00Z', 'ML', 'home', None, 1.5, 72.0),
                          odd('2026-10-21T20:00:00Z', 'ML', 'away', None, 2.6, 28.0),
                          odd('2026-10-21T20:00:00Z', 'SPREAD', 'home', -4.5, 1.9, 60.0),
                          odd('2026-10-21T20:00:00Z', 'SPREAD', 'away', 4.5, 1.9, 40.0),
                          odd('2026-10-21T20:00:00Z', 'TOTAL', 'over', 211.5, 1.9, 45.0),
                          odd('2026-10-21T20:00:00Z', 'TOTAL', 'under', 211.5, 1.9, 55.0),
                          odd('2026-10-22T00:00:00Z', 'TOTAL', 'over', 212.5, 1.9, 40.0)])      # after tip-off
    games = pd.DataFrame({'date': pd.to_datetime(['2026-10-21']), 'home': ['bos'], 'away': ['ny'],
                          'home_score': [110], 'away_score': [101]})
    t = game_lines(snaps, games).set_index(['market', 'side'])
    assert len(t) == 6                                                    # one row per outcome, last pre-tip fetch
    ml = t.loc[('ML', 'home')]
    assert ml['model %'] == 72.0 and ml['won'] == 1.0
    assert ml['market %'] == pytest.approx(100 * (1 / 1.5) / (1 / 1.5 + 1 / 2.6))
    assert t.loc[('SPREAD', 'away'), 'market %'] == pytest.approx(50)     # -4.5 and +4.5 are one market
    assert t.loc[('SPREAD', 'home'), 'won'] == 1.0 and t.loc[('TOTAL', 'under'), 'won'] == 1.0
    report = game_report(t.reset_index())
    assert 'Game model' in report and 'the old 🟢' in report and '6 settled main-line outcomes on 1 nights' in report
    assert 'No settled' in game_report(pd.DataFrame())
