import numpy as np
import pandas as pd
import pytest

from absence_window import MAX_GAME_NO, missed_in_a_row, out_tonight, signal_rows, situations

NIGHT = pd.Timestamp('2026-11-15')
T = lambda h, m=0: pd.Timestamp('2026-11-15', tz='UTC') + pd.Timedelta(hours=h, minutes=m)
STAR, MATE, BENCH = 1, 2, 3


def logs(star_missed=(5, 6, 7, 8)):
    """phi's games on Nov 1–12: the star sits `star_missed`; the mate grabs 10 boards with him, 14 without; the
    bench player always 4."""
    rows = []
    for day in range(1, 13):
        date = pd.Timestamp(f'2026-11-{day:02d}')
        star_out = day in star_missed
        for pid, name, reb, minutes in ((STAR, 'Star', 12, 34), (MATE, 'Mate', 14 if star_out else 10, 30),
                                        (BENCH, 'Bench', 4, 15)):
            if pid == STAR and star_out:
                continue
            rows.append({'player_id_ESPN': pid, 'player_display_name': name, 'team': 'phi', 'Date': date,
                         'game_id': f'g{day}', 'season_id': 2026, 'MIN': minutes, 'REB': reb, 'PTS': 10})
    return pd.DataFrame(rows).astype({'player_id_ESPN': 'Int64'})


def version(*rows):
    return pd.DataFrame([{'player_id_ESPN': pid, 'team': 'phi', 'play_pct': pct, 'injury': injury, 'name': name}
                         for pid, pct, injury, name in rows])


def test_a_fresh_absence_is_the_first_game_without_him():
    assert missed_in_a_row(logs(), STAR, 'phi', NIGHT) == 0
    assert missed_in_a_row(logs(star_missed=(11, 12)), STAR, 'phi', NIGHT) == 2


def test_out_in_the_latest_version_with_since_and_game_no():
    saved = [(T(9), version((MATE, 100, None, 'Mate'))), (T(12), version((STAR, 0, 'Out', 'Star')))]
    out = out_tonight(saved, logs(), NIGHT, {STAR, MATE})
    assert out[['player_id_ESPN', 'since', 'game_no', 'now_ques']].values.tolist() == [[STAR, T(12), 1, False]]


def test_out_then_ques_stays_marked_and_a_real_return_drops_off():
    ques = [(T(9), version((STAR, 0, 'Out', 'Star'))), (T(21), version((STAR, 100, 'Ques', 'Star')))]
    out = out_tonight(ques, logs(), NIGHT, {STAR})
    assert out[['since', 'now_ques']].values.tolist() == [[T(9), True]]
    back = [(T(9), version((STAR, 0, 'Out', 'Star'))), (T(21), version((MATE, 100, None, 'Mate')))]
    assert out_tonight(back, logs(), NIGHT, {STAR}).empty


def test_only_regulars_count():
    saved = [(T(9), version((BENCH, 0, 'Out', 'Bench')))]
    assert out_tonight(saved, logs(), NIGHT, {STAR}).empty


def priced(**over):
    rows = [{'player_id': MATE, 'team': 'phi', 'event_id': 'e1', 'name': 'Mate', 'name_ESPN': 'Mate', 'bet_type': 'REB',
             'line': 11.5, 'over_odds': 1.9, 'under_odds': 1.9, 'side': 'Over', 'p win %': 60.0, 'p push %': 0.0},
            {'player_id': BENCH, 'team': 'phi', 'event_id': 'e1', 'name': 'Bench', 'name_ESPN': 'Bench',
             'bet_type': 'REB', 'line': 3.5, 'over_odds': 1.9, 'under_odds': 1.9, 'side': 'Over', 'p win %': 55.0,
             'p push %': 0.0}]
    return pd.DataFrame([r | over for r in rows])


def out_row(game_no=1):
    return pd.DataFrame([{'night': NIGHT, 'team': 'phi', 'player_id_ESPN': STAR, 'name': 'Star', 'since': T(9),
                          'game_no': game_no, 'now_ques': False}])


def history():
    """Superbet's mate REB 10.5 on Nov 12 (the star played)."""
    return pd.DataFrame([{'player_id_ESPN': MATE, 'bet_type': 'REB', 'line': 10.5, 'fetched_at': '2026-11-12T18:00:00Z',
                          'start_time': '2026-11-13T00:00:00Z'}])


def test_the_mate_is_listed_on_the_side_of_his_change_and_the_bench_player_isnt():
    table = situations(priced(), logs(), out_row(), history(), {('e1', 'Mate', 'REB'): T(10)})
    assert table['name'].tolist() == ['Mate']
    r = table.iloc[0]
    assert r['side'] == 'Over' and r['change'] > 0 and r['game_no'] == 1
    # 4 games without: change (14 − 10) × 4 / (4 + 5)
    assert r['change'] == pytest.approx(4 * 4 / 9)
    assert r['previous line'] == 10.5 and r['shift'] == 1.0 and r['new line']
    assert r['price %'] == pytest.approx(50) and r['gap pp'] == pytest.approx(10)
    assert r['break-even net %'] == pytest.approx(100 / (0.88 * 1.9))


def test_our_chance_of_the_other_side_when_the_model_evaluates_the_opposite():
    table = situations(priced(side='Under', **{'p win %': 58.0}), logs(), out_row())
    assert table.iloc[0]['p side %'] == pytest.approx(42)
    assert not table.iloc[0]['new line'] and np.isnan(table.iloc[0]['shift'])


def test_few_games_without_or_a_stale_absence_list_nothing():
    assert situations(priced(), logs(star_missed=(5, 6)), out_row()).empty      # 2 games without him
    assert situations(priced(), logs(), out_row(game_no=MAX_GAME_NO + 1)).empty


def offered():
    rows = []
    for at in (T(8), T(10), T(12)):
        rows.append({'at': at, 'event_id': 'e1', 'name_ESPN': 'Mate', 'player_id_ESPN': MATE, 'bet_type': 'REB',
                     'line': 10.5 if at == T(8) else 11.5, 'over_odds': 1.9, 'under_odds': 1.9})
        if at == T(12):   # a line first offered after the news
            rows.append({'at': at, 'event_id': 'e1', 'name_ESPN': 'Mate', 'player_id_ESPN': MATE, 'bet_type': 'PTS',
                         'line': 9.5, 'over_odds': 1.9, 'under_odds': 1.9})
    return pd.DataFrame(rows).astype({'player_id_ESPN': 'Int64'})


def test_signals_take_each_line_at_its_first_read_once_out_was_known():
    s = signal_rows(NIGHT, out_row(), offered(), logs(), {MATE: 'phi', STAR: 'phi'})
    assert s[['bet_type', 'at', 'line', 'side', 'hypothesis']].values.tolist() == [['REB', T(10), 11.5, 'Over', 'H10']]
    assert bool(s['clears'].all())


# --- who gains ---

from absence_window import who_gains  # noqa: E402

WING = 4


def team_logs(missed=(5, 6, 7, 8)):
    """The star (C) sits `missed`; the backup center (C, bench) plays 14 min with him, 26 without; the wing (F)
    scores 12 with him, 20 without; the bench guard never changes."""
    rows = []
    for day in range(1, 13):
        out = day in missed
        for pid, name, pos, minutes, pts, start in (
                (STAR, 'Star', 'C', 34, 20, True), (MATE, 'Backup', 'C', 26 if out else 14, 8, False),
                (WING, 'Wing', 'F', 32, 20 if out else 12, True), (BENCH, 'Bench', 'G', 15, 6, False)):
            if pid == STAR and out:
                continue
            rows.append({'player_id_ESPN': pid, 'player_display_name': name, 'position': pos, 'team': 'phi',
                         'Date': pd.Timestamp(f'2026-11-{day:02d}'), 'game_id': f'g{day}', 'season_id': 2026,
                         'MIN': minutes, 'PTS': pts + day % 3, 'REB': 5 + day % 2, 'AST': 2 + day % 2,
                         'starter': start})
    return pd.DataFrame(rows).astype({'player_id_ESPN': 'Int64'})


def latest(backup_starts=True):
    rows = [(STAR, 0, 'Out', 'Star', 'may_not_play', 'C')]
    if backup_starts:
        rows.append((MATE, 100, None, 'Backup', 'starter', 'C'))
    return pd.DataFrame([{'player_id_ESPN': pid, 'team': 'phi', 'play_pct': pct, 'injury': inj, 'name': name,
                          'role': role, 'pos': pos} for pid, pct, inj, name, role, pos in rows])


def star_out():
    return out_row().iloc[0]


def test_the_promoted_backup_at_his_position_replaces_him_and_the_wing_changes_most():
    lines = pd.DataFrame([{'player_id': WING, 'bet_type': 'PTS', 'line': 15.5}])
    g = who_gains(star_out(), latest(), team_logs(), lines, [STAR])
    assert g['position'] == 'C' and not g['too_few']
    assert [(r['name'], r['promoted']) for r in g['replacements']] == [('Backup', True)]
    assert g['replacements'][0]['min_change'] > 0
    wing = g['affected'][0]
    assert (wing['name'], wing['stat'], wing['line']) == ('Wing', 'PTS', 15.5) and wing['change'] > 0
    assert 'Bench' not in [r['name'] for r in g['affected'] + g['replacements']]      # no change at all


def test_a_bench_backup_still_replaces_him_by_minutes_and_a_missing_line_is_none():
    g = who_gains(star_out(), latest(backup_starts=False), team_logs(), None, [STAR])
    assert [(r['name'], r['promoted']) for r in g['replacements']] == [('Backup', False)]
    assert g['affected'][0]['line'] is None


def test_too_few_games_without_him_names_nobody():
    g = who_gains(star_out(), latest(), team_logs(missed=(5, 6)), None, [STAR])
    assert g['too_few'] and not g['replacements'] and not g['affected']
