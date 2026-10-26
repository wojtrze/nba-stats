"""Line movement and bet settling from daily_snapshot.py's files (no Streamlit, so it can be tested)."""
from typing import Optional

import numpy as np
import pandas as pd

from metrics import game_lines, grouped_rates, prop_signal, score_check, side_profit, side_result
from superbet_fetcher import main_lines

PROP_KEY = ['event_id', 'name_ESPN', 'bet_type']
GAME_KEY = ['event_id', 'market', 'side', 'line']


def _first_snapshot(snapshots: pd.DataFrame, key) -> pd.DataFrame:
    """Each key's row from its earliest fetch (a moneyline's NaN line counts as a key value)."""
    if snapshots.empty:
        return snapshots
    return snapshots.sort_values('fetched_at').drop_duplicates(key, keep='first')


def prop_movement(snapshots: pd.DataFrame, current: pd.DataFrame) -> pd.DataFrame:
    """current props with the first snapshot's line and odds: open line, line move (current − open, + = the line
    went up), open over / under odds and first seen. NaN where the line has no earlier snapshot."""
    cols = ['open line', 'line move', 'open over', 'open under', 'first seen']
    if snapshots.empty or current.empty:
        return current.assign(**{c: np.nan for c in cols})
    first = _first_snapshot(snapshots, PROP_KEY)[PROP_KEY + ['line', 'over_odds', 'under_odds', 'fetched_at']]
    first = first.rename(columns={'line': 'open line', 'over_odds': 'open over', 'under_odds': 'open under',
                                  'fetched_at': 'first seen'})
    out = current.merge(first, on=PROP_KEY, how='left')
    out['line move'] = out['line'] - out['open line']
    out.index = current.index
    return out


def game_odds_movement(snapshots: pd.DataFrame, current: pd.DataFrame) -> pd.DataFrame:
    """current game outcomes with the first snapshot's odds for the same market, side and line: open odds and
    odds move (current − open; falling odds = money came in on that outcome)."""
    if snapshots.empty or current.empty:
        return current.assign(**{'open odds': np.nan, 'odds move': np.nan})
    first = _first_snapshot(snapshots, GAME_KEY)[GAME_KEY + ['odds']].rename(columns={'odds': 'open odds'})
    out = current.merge(first, on=GAME_KEY, how='left')   # pandas matches the moneyline's NaN line to NaN
    out['odds move'] = out['odds'] - out['open odds']
    out.index = current.index
    return out


def opening_game_lines(snapshots: pd.DataFrame) -> pd.DataFrame:
    """metrics.game_lines of each event's earliest fetch: the opening main handicap and total."""
    if snapshots.empty:
        return pd.DataFrame(columns=['home_spread', 'total', 'home_implied', 'away_implied'])
    first = snapshots[snapshots['fetched_at'] == snapshots.groupby('event_id')['fetched_at'].transform('min')]
    return game_lines(pd.DataFrame(main_lines(first.drop(columns='fetched_at').to_dict('records'))))


# --- settling: what happened to every line the snapshots saw ---

# 'last line' / 'last odds': the last quote the snapshots saw before tip-off (two or three snapshots a day, so
# not the true closing line); 'h before tip': how long before tip-off the bet's quote / that last quote was taken
PROP_RESULT_COLUMNS = ['game_date', 'name', 'game', 'bet_type', 'line', 'pick', 'odds', 'model_pct', 'edge_pp',
                       'edge_low', 'signal', 'actual', 'status', 'result', 'profit', 'h before tip', 'last line',
                       'last odds', 'last h before tip', 'line vs last', 'odds vs last %']
GAME_RESULT_COLUMNS = ['game_date', 'game', 'market', 'side', 'team', 'line', 'odds', 'model_pct', 'edge_pp',
                       'main', 'score', 'status', 'result', 'profit', 'h before tip', 'last odds', 'last h before tip',
                       'odds vs last %']
# columns of a bet-slip row (bets.py) that settling keeps
BET_COLUMNS = ['bet_id', 'placed_at', 'stake']


def _et_date(start_time: pd.Series) -> pd.Series:
    """The game's US Eastern date, the date ESPN (and the stored game logs) use."""
    return pd.to_datetime(start_time, utc=True).dt.tz_convert('US/Eastern').dt.tz_localize(None).dt.normalize()


def _open_and_close(snapshots: pd.DataFrame, key):
    """Each key's first and last snapshot before tip-off: the line as first offered, and the last observed one."""
    fetched = pd.to_datetime(snapshots['fetched_at'], utc=True)
    pre = snapshots[fetched < pd.to_datetime(snapshots['start_time'], utc=True)].sort_values('fetched_at')
    return pre.drop_duplicates(key, keep='first'), pre.drop_duplicates(key, keep='last')


def _game_missing(game_date: pd.Series, in_games: pd.Series, games: pd.DataFrame) -> pd.Series:
    """The game isn't stored although games of a later date are: postponed, cancelled or skipped by the scraper.
    It stays unresolved (not void: nothing says how the bookmaker settled it) until it's stored."""
    stored_through = games['date'].max() if len(games) else pd.NaT
    return ~in_games & pd.notna(stored_through) & (game_date < stored_through)


def edge_signal(edge_pp: pd.Series) -> pd.Series:
    """🟢 / 🟡 from the saved edge with the current 🟢 threshold, for fetches saved without a signal."""
    from models import load_green_edge
    return prop_signal(pd.to_numeric(edge_pp, errors='coerce'), load_green_edge())


def _signal(bets: pd.DataFrame) -> pd.Series:
    """The signal saved with the fetch (🔴 included), else the one its edge gives."""
    computed = edge_signal(bets['edge_pp'])
    if 'signal' not in bets:
        return computed
    saved = bets['signal'].astype(object)
    return saved.where(saved.notna() & (saved != '') | bets['edge_pp'].isna(), computed).fillna('')


def _hours_before_tip(fetched_at: pd.Series, start_time: pd.Series) -> pd.Series:
    """How many hours before tip-off a quote was fetched."""
    gap = pd.to_datetime(start_time, utc=True) - pd.to_datetime(fetched_at, utc=True)
    return (gap.dt.total_seconds() / 3600).round(1)


def _last_quote(snapshots: pd.DataFrame, key, cols) -> pd.DataFrame:
    """Each key's last snapshot before tip-off: `cols` and 'last h before tip'."""
    if snapshots.empty:
        return pd.DataFrame(columns=key + cols + ['last h before tip'])
    last = _open_and_close(snapshots, key)[1]
    return last[key + cols].assign(**{'last h before tip': _hours_before_tip(last['fetched_at'], last['start_time'])})


def settle_props(snapshots: pd.DataFrame, logs: pd.DataFrame, games: pd.DataFrame,
                 bets: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """One row per snapshotted prop (event, player, stat), as first offered before tip-off, with the dashboard's
    pick at that moment (the pick / edge columns daily_snapshot.py saves; empty for older snapshots), the player's
    actual number and the result.

    status: settled; void = the game is stored, complete (its players' points add up to the score) and the player
    didn't play (Superbet refunds those); pending = the game isn't in games.csv yet (run the scraper); unresolved =
    it can't be settled from what's stored: the player isn't identified (no saved id, and the name matches no
    player or several), the game's box score is incomplete (metrics.score_check), or the game is still missing
    while later games are stored (postponed?). Only settled lines get a win / loss / push. h before tip: how long before tip-off the
    bet's quote was fetched; last line / last odds / last h before tip: the last quote the snapshots saw before
    tip-off (not the true closing line: there are only a few snapshots a day); line vs last: how much better the
    bet's line was than that last one in the pick's direction (+1 = an Over at 20.5 whose last quote was 21.5);
    odds vs last %: the same with the odds, when the line didn't change.
    logs: prepare_logs output; games: games.csv rows (date parsed). bets: rows in the snapshot format (with a
    pick) to settle instead of every line's first snapshot, e.g. the bet slip; the snapshots then only give the
    last quote."""
    if bets is None:
        bets = _open_and_close(snapshots, PROP_KEY)[0] if len(snapshots) else snapshots
    if bets.empty:
        return pd.DataFrame(columns=PROP_RESULT_COLUMNS)
    keep = [c for c in BET_COLUMNS if c in bets]
    last = _last_quote(snapshots, PROP_KEY, ['line', 'over_odds', 'under_odds']).rename(
        columns={'line': 'last line', 'over_odds': 'last over', 'under_odds': 'last under'})
    bets = bets.merge(last, on=PROP_KEY, how='left')
    for col in ['pick', 'model_pct', 'edge_pp', 'edge_low', 'player_id_ESPN']:
        if col not in bets:
            bets[col] = np.nan
    bets['game_date'] = _et_date(bets['start_time'])
    bets['game'] = bets['away'].str.upper() + ' @ ' + bets['home'].str.upper()

    # the player: the id saved with the snapshot, else the ESPN-style name when it belongs to exactly one player
    named = logs.drop_duplicates(['player_name_ESPN', 'player_id_ESPN'])
    unique = named.groupby('player_name_ESPN')['player_id_ESPN'].transform('size') == 1
    ids = named[unique].set_index('player_name_ESPN')['player_id_ESPN']
    pid = pd.to_numeric(bets['player_id_ESPN'], errors='coerce')
    bets['player_id'] = pid.fillna(bets['name_ESPN'].map(ids)).astype('Int64')
    lines = logs.assign(player_id=logs['player_id_ESPN'].astype('Int64'), game_date=logs['Date'].dt.normalize())
    stats = sorted(set(bets['bet_type']) & set(lines.columns))
    bets = bets.merge(lines[['player_id', 'game_date'] + stats].drop_duplicates(['player_id', 'game_date']),
                      on=['player_id', 'game_date'], how='left')
    bets['actual'] = [row[t] if t in stats else np.nan for t, (_, row) in zip(bets['bet_type'], bets.iterrows())]

    stored = set(zip(games['date'].dt.normalize(), games['home'], games['away']))
    in_games = pd.Series([k in stored for k in zip(bets['game_date'], bets['home'], bets['away'])], index=bets.index)
    bad = score_check(games, logs)
    incomplete = set(zip(pd.to_datetime(bad['date']).dt.normalize(), bad['home'], bad['away'])) if len(bad) else set()
    partial = pd.Series([k in incomplete for k in zip(bets['game_date'], bets['home'], bets['away'])],
                        index=bets.index)
    bets['status'] = np.select(
        [bets['actual'].notna(), in_games & (bets['player_id'].isna() | partial), in_games,
         _game_missing(bets['game_date'], in_games, games)],
        ['settled', 'unresolved', 'void', 'unresolved'], 'pending')

    over = bets['pick'] == 'Over'
    bets['odds'] = pd.Series(np.where(over, bets['over_odds'], bets['under_odds']), index=bets.index) \
        .where(bets['pick'].notna())
    direction = np.where(over, 1, -1)
    bets['result'] = side_result((bets['actual'] - bets['line']) * direction, bets['status'] == 'settled')
    bets.loc[bets['status'] == 'void', 'result'] = 'void'
    bets['result'] = bets['result'].where(bets['pick'].notna())
    bets['profit'] = side_profit(bets['result'], bets['odds'])
    bets['h before tip'] = _hours_before_tip(bets['fetched_at'], bets['start_time']) if 'fetched_at' in bets \
        else np.nan
    bets['last odds'] = np.where(over, bets['last over'], bets['last under'])
    bets['line vs last'] = ((bets['last line'] - bets['line']) * direction).where(bets['pick'].notna())
    bets['odds vs last %'] = (100 * (bets['odds'] / bets['last odds'] - 1)).where(bets['last line'] == bets['line'])
    bets['signal'] = _signal(bets).where(bets['pick'].notna(), '')
    return bets[PROP_RESULT_COLUMNS + ['player_id', 'start_time'] + keep]


def _main_keys(snapshots: pd.DataFrame) -> set:
    """(event, market, side, line) of every outcome that was Superbet's main line in some snapshot."""
    keys = set()
    for _, snap in snapshots.groupby('fetched_at'):
        for r in main_lines(snap.drop(columns='fetched_at').to_dict('records')):
            keys.add((r['event_id'], r['market'], r['side'], None if pd.isna(r['line']) else r['line']))
    return keys


def settle_games(snapshots: pd.DataFrame, games: pd.DataFrame, bets: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """One row per snapshotted game outcome (event, market, side, line) as first offered before tip-off, with the
    model's chance and edge at that moment (saved by daily_snapshot.py), the final score and the result.
    main = it was Superbet's main line in a snapshot. h before tip / last odds / last h before tip / odds vs last
    %: as in settle_props (+ = a better price than the last quote before tip-off). status: settled, pending (not stored yet) or unresolved (still
    missing while later games are stored). bets: as in settle_props."""
    if bets is None:
        bets = _open_and_close(snapshots, GAME_KEY)[0] if len(snapshots) else snapshots
    if bets.empty:
        return pd.DataFrame(columns=GAME_RESULT_COLUMNS)
    keep = [c for c in BET_COLUMNS if c in bets]
    main = _main_keys(snapshots) if len(snapshots) else set()
    last = _last_quote(snapshots, GAME_KEY, ['odds']).rename(columns={'odds': 'last odds'})
    bets = bets.merge(last, on=GAME_KEY, how='left')
    for col in ['model_pct', 'edge_pp']:
        if col not in bets:
            bets[col] = np.nan
    bets['main'] = [(e, m, s, None if pd.isna(l) else l) in main
                    for e, m, s, l in zip(bets['event_id'], bets['market'], bets['side'], bets['line'])]
    bets['game_date'] = _et_date(bets['start_time'])
    bets['game'] = bets['away'].str.upper() + ' @ ' + bets['home'].str.upper()
    finals = games.assign(game_date=games['date'].dt.normalize())[['game_date', 'home', 'away', 'home_score',
                                                                    'away_score']]
    bets = bets.merge(finals.drop_duplicates(['game_date', 'home', 'away']), on=['game_date', 'home', 'away'],
                      how='left')
    h, a = bets['home_score'], bets['away_score']
    side_margin = np.where(bets['side'] == 'home', h - a, a - h)
    scored = np.select([bets['market'] == 'TOTAL', bets['market'] == 'HOME_TOTAL', bets['market'] == 'AWAY_TOTAL'],
                       [h + a, h, a], np.nan)
    over = np.where(bets['side'] == 'over', 1, -1)
    margin = pd.Series(np.select([bets['market'] == 'ML', bets['market'] == 'SPREAD'],
                                 [side_margin, side_margin + bets['line'].fillna(0)], (scored - bets['line']) * over),
                       index=bets.index)
    stored = set(zip(games['date'].dt.normalize(), games['home'], games['away']))
    in_games = pd.Series([k in stored for k in zip(bets['game_date'], bets['home'], bets['away'])], index=bets.index)
    bets['status'] = np.select([h.notna(), _game_missing(bets['game_date'], in_games, games)],
                               ['settled', 'unresolved'], 'pending')
    bets['result'] = side_result(margin, bets['status'] == 'settled')
    bets['profit'] = side_profit(bets['result'], bets['odds'])
    bets['score'] = [f"{x:.0f} – {y:.0f}" if pd.notna(y) else '' for x, y in zip(a, h)]
    bets['h before tip'] = _hours_before_tip(bets['fetched_at'], bets['start_time']) if 'fetched_at' in bets \
        else np.nan
    bets['odds vs last %'] = 100 * (bets['odds'] / bets['last odds'] - 1)
    return bets[GAME_RESULT_COLUMNS + keep]


def edge_bucket(edge_pp: pd.Series) -> pd.Series:
    return pd.cut(edge_pp, [-np.inf, 0, 5, 10, np.inf], labels=['≤ 0', '0–5', '5–10', '10+'])


EDGE_THRESHOLDS = (0, 1, 2, 3, 5)


def threshold_table(settled: pd.DataFrame, thresholds=EDGE_THRESHOLDS) -> pd.DataFrame:
    """Signal efficiency: for each threshold, every decided pick whose saved edge reached it (cumulative, 'edge ≥
    pp'; 0 means any positive edge) with expected % (the model's chance), hit %, its 95% range and ROI.
    🔴 lines count too: the threshold alone is judged."""
    decided = settled[settled['result'].isin(['win', 'loss']) & settled['edge_pp'].notna()] \
        .assign(is_hit=lambda d: d['result'] == 'win')
    rows = []
    for thr in thresholds:
        part = decided[decided['edge_pp'] > 0] if thr == 0 else decided[decided['edge_pp'] >= thr]
        if len(part):
            rows.append({'edge ≥ pp': thr, **grouped_rates(part.assign(all=''), 'all').drop(columns='all').iloc[0]})
    return pd.DataFrame(rows)


def results_table(settled: pd.DataFrame, by) -> pd.DataFrame:
    """metrics.grouped_rates of the won and lost bets (pushes and voids left out), plus the average odds vs the
    last quote before tip-off."""
    decided = settled[settled['result'].isin(['win', 'loss'])].assign(is_hit=lambda d: d['result'] == 'win')
    if decided.empty:
        return pd.DataFrame()
    table = grouped_rates(decided, by)
    keys = [by] if isinstance(by, str) else list(by)
    vs_last = decided.groupby(keys, observed=True)['odds vs last %'].mean().rename('avg odds vs last %').reset_index()
    return table.merge(vs_last, on=keys, how='left')


def calibration(settled: pd.DataFrame, width: float = 10) -> pd.DataFrame:
    """Decided bets grouped by the model's chance (bins of `width` pp): the average model % and how often they
    actually won. A calibrated model sits on the diagonal."""
    decided = settled[settled['result'].isin(['win', 'loss']) & settled['model_pct'].notna()]
    if decided.empty:
        return pd.DataFrame(columns=['bin', 'bets', 'model %', 'actual %'])
    grouped = decided.assign(bin=(decided['model_pct'] // width) * width, won=decided['result'] == 'win') \
        .groupby('bin')
    return pd.DataFrame({'bets': grouped.size(), 'model %': grouped['model_pct'].mean(),
                         'actual %': 100 * grouped['won'].mean()}).reset_index()
