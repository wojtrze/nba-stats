"""Line movement and bet settling from daily_snapshot.py's files (no Streamlit, so it can be tested)."""
from typing import Optional

import numpy as np
import pandas as pd

from metrics import (SUPERBET_STANDARD, alpha, game_lines, grouped_rates, prop_signal, score_check, side_profit,
                     side_result, wilson_interval)
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
                       'edge_low', 'signal', 'actual', 'status', 'result', 'profit', 'profit std', 'h before tip',
                       'last line',
                       'last odds', 'last h before tip', 'line vs last', 'odds vs last %']
GAME_RESULT_COLUMNS = ['game_date', 'game', 'market', 'side', 'team', 'line', 'odds', 'model_pct', 'edge_pp',
                       'main', 'score', 'status', 'result', 'profit', 'profit std', 'h before tip', 'last odds',
                       'last h before tip',
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


# --- the closing line: the scheduled fetches' last quote before tip-off (fetch_loop: T-10 and T-5 minutes) ---

CLOSE_MAX_AGE_MIN = 10      # a close is valid when the game was last read at most this long before tip-off
CLOSE_COLUMNS = ['close line', 'close over', 'close under', 'close age min']
CLV_COLUMNS = ['close line', 'close odds', 'close age min', 'line vs close', 'clv %', 'clv % std', 'clv pp']


def closing_props(quotes: pd.DataFrame, event_fetches: pd.DataFrame) -> pd.DataFrame:
    """Each line's closing quote from fetch_loop's files: the last quote of its key before tip-off (quotes holds
    only changes, so that's the line and odds as the game was last read) and 'close age min', how long before
    tip-off the game was last read (its superbet_event_fetches row: a game read and unchanged still counts). A
    line withdrawn before tip-off (empty odds) has no close."""
    if quotes.empty or event_fetches.empty:
        return pd.DataFrame(columns=PROP_KEY + CLOSE_COLUMNS)
    reads = event_fetches.assign(at=pd.to_datetime(event_fetches['fetched_at'], utc=True),
                                 tip=pd.to_datetime(event_fetches['start_time'], utc=True))
    reads = reads[reads['at'] < reads['tip']]
    last_read = reads.groupby('event_id').agg(tip=('tip', 'first'), last=('at', 'max'))
    last_read['close age min'] = ((last_read['tip'] - last_read['last']).dt.total_seconds() / 60).round(1)
    q = quotes.merge(last_read[['tip']], left_on='event_id', right_index=True)
    q = q[pd.to_datetime(q['fetched_at'], utc=True) < q['tip']].sort_values('fetched_at', kind='stable')
    close = q.drop_duplicates(PROP_KEY, keep='last')
    close = close[close['over_odds'].notna() & close['under_odds'].notna()]
    close = close.rename(columns={'line': 'close line', 'over_odds': 'close over', 'under_odds': 'close under'})
    return close.merge(last_read[['close age min']], left_on='event_id', right_index=True)[PROP_KEY + CLOSE_COLUMNS]


def _no_vig(side_odds, other_odds):
    return (1 / side_odds) / (1 / side_odds + 1 / other_odds)


def add_clv(bets: pd.DataFrame, closing: pd.DataFrame) -> pd.DataFrame:
    """bets (with pick, line, over_odds, under_odds, odds) and their close: close line / close odds (the pick's),
    close age min, line vs close (+ = the bet's line was better in the pick's direction), and, when the close is
    valid (close age min ≤ CLOSE_MAX_AGE_MIN) at the same line: clv % = the bet's expected return at the closing
    margin-free price (odds × p_close − 1; the standard measure of having beaten the market), clv % std = the same
    after the 12% stake tax, clv pp = the closing margin-free chance minus the one at the bet's quote. Pushes
    aren't modelled (half lines mostly)."""
    out = bets.drop(columns=[c for c in CLOSE_COLUMNS if c in bets]).merge(closing, on=PROP_KEY, how='left')
    out.index = bets.index
    over = out['pick'] == 'Over'
    direction = np.where(over, 1, -1)
    out['close odds'] = np.where(over, out['close over'], out['close under'])
    out['line vs close'] = ((out['close line'] - out['line']) * direction).where(out['pick'].notna())
    valid = (out['close age min'] <= CLOSE_MAX_AGE_MIN) & (out['close line'] == out['line']) & out['pick'].notna()
    p_close = pd.Series(np.where(over, _no_vig(out['close over'], out['close under']),
                                 _no_vig(out['close under'], out['close over'])), index=out.index)
    p_bet = pd.Series(np.where(over, _no_vig(out['over_odds'], out['under_odds']),
                               _no_vig(out['under_odds'], out['over_odds'])), index=out.index)
    out['clv %'] = (100 * (out['odds'] * p_close - 1)).where(valid)
    out['clv % std'] = (100 * (alpha(SUPERBET_STANDARD) * out['odds'] * p_close - 1)).where(valid)
    out['clv pp'] = (100 * (p_close - p_bet)).where(valid)
    return out


def settle_props(snapshots: pd.DataFrame, logs: pd.DataFrame, games: pd.DataFrame,
                 bets: Optional[pd.DataFrame] = None, closing: Optional[pd.DataFrame] = None) -> pd.DataFrame:
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
    last quote. closing: closing_props output, which adds CLV_COLUMNS (add_clv)."""
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
    # the same with Superbet's 12% stake tax (metrics.COST_PROFILES), next to the plain-odds profit
    bets['profit std'] = side_profit(bets['result'], bets['odds'], SUPERBET_STANDARD)
    bets['h before tip'] = _hours_before_tip(bets['fetched_at'], bets['start_time']) if 'fetched_at' in bets \
        else np.nan
    bets['last odds'] = np.where(over, bets['last over'], bets['last under'])
    bets['line vs last'] = ((bets['last line'] - bets['line']) * direction).where(bets['pick'].notna())
    bets['odds vs last %'] = (100 * (bets['odds'] / bets['last odds'] - 1)).where(bets['last line'] == bets['line'])
    bets['signal'] = _signal(bets).where(bets['pick'].notna(), '')
    if closing is not None:
        bets = add_clv(bets, closing)
        keep = CLV_COLUMNS + keep
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
    # the same with Superbet's 12% stake tax (metrics.COST_PROFILES), next to the plain-odds profit
    bets['profit std'] = side_profit(bets['result'], bets['odds'], SUPERBET_STANDARD)
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


# --- the stars' record (decisions.stars): what each level did, as shown before tip-off ---

RECORDED, RECOMPUTED = 'recorded', 'recomputed'
ACCUMULATOR_LEGS = 3
EVERY_LINE = 'every line'


def star_lines(snapshots: pd.DataFrame) -> pd.DataFrame:
    """Every line as of its last fetch before tip-off, in the snapshot format with 'pick' = the evaluated side,
    stars (NA = no rating), night_rank, 'side market %' and origin. RECORDED: the stars the fetch saved (live
    fetches from Nov 2); RECOMPUTED: older nights, rated again by decisions.stars from the fields the fetch saved
    before the game (its side and expected return when saved, else its pick and that pick's model %; no RotoWire
    chance to play, so only the saved red flag gives 0★). Nothing is recalibrated."""
    from decisions import stars
    needed = {'fetched_at', 'start_time', 'over_odds', 'under_odds', 'model_pct', 'pick'}
    if snapshots.empty or not needed <= set(snapshots.columns):
        return pd.DataFrame()
    fetched = pd.to_datetime(snapshots['fetched_at'], utc=True)
    rows = snapshots[fetched < pd.to_datetime(snapshots['start_time'], utc=True)].sort_values('fetched_at',
                                                                                                kind='stable')
    last = rows.drop_duplicates(PROP_KEY, keep='last').reset_index(drop=True)
    for col in ('stars', 'night_rank', 'eval_side', 'ev_net_100', 'market_over_pct', 'red_flag'):
        if col not in last:
            last[col] = np.nan
    has_net = last['eval_side'].isin(['Over', 'Under'])
    last['pick'] = last['eval_side'].where(has_net, last['pick'])
    last = last[last['pick'].isin(['Over', 'Under'])].reset_index(drop=True)
    has_net = last['eval_side'].isin(['Over', 'Under'])
    night = _et_date(last['start_time'])
    saved = pd.to_numeric(last['stars'], errors='coerce')
    # a night is recorded once a fetch of it saved the stars; older nights are rated again here
    recorded = night.isin(set(night[saved.notna()]))
    last['origin'] = np.where(recorded, RECORDED, RECOMPUTED)
    last['stars'] = saved.where(recorded)
    last['night_rank'] = pd.to_numeric(last['night_rank'], errors='coerce').where(recorded)

    older = last[~recorded]
    if len(older):
        odds = pd.Series(np.where(older['pick'] == 'Over', older['over_odds'], older['under_odds']), index=older.index)
        own_ev = 100 * (pd.to_numeric(older['model_pct'], errors='coerce') / 100 * alpha(SUPERBET_STANDARD) * odds - 1)
        rated = stars(pd.DataFrame({
            'event_id': older['event_id'], 'name_ESPN': older['name_ESPN'], 'bet_type': older['bet_type'],
            'start_time': older['start_time'], 'side': older['pick'], 'side odds': odds,
            'ev net 100': pd.to_numeric(older['ev_net_100'], errors='coerce').where(has_net[older.index], own_ev),
            'p win %': older['model_pct'], 'market over %': older['market_over_pct'],
            'red flag': older['red_flag']}))
        if len(rated):
            found = older.reset_index()[['index'] + PROP_KEY].merge(rated[PROP_KEY + ['stars', 'rank']], on=PROP_KEY)
            last.loc[found['index'], 'stars'] = found['stars'].astype(float).values
            last.loc[found['index'], 'night_rank'] = found['rank'].values
    last['stars'] = last['stars'].astype('Int64')
    market = pd.to_numeric(last['market_over_pct'], errors='coerce')
    last['side market %'] = market.where(last['pick'] == 'Over', 100 - market)
    # night by night, in the stars' order
    order = pd.DataFrame({'night': night, 'rank': last['night_rank']}).sort_values(
        ['night', 'rank'], na_position='last', kind='stable').index
    return last.loc[order].reset_index(drop=True)


def settle_stars(snapshots: pd.DataFrame, logs: pd.DataFrame, games: pd.DataFrame,
                 closing: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """settle_props of star_lines, with stars, night_rank, side market % and origin next to each result; with the
    CLV columns when `closing` (closing_props) is given."""
    lines = star_lines(snapshots)
    if lines.empty:
        return pd.DataFrame()
    settled = settle_props(snapshots, logs, games, bets=lines, closing=closing)  # keeps the bets' order
    for col in ['stars', 'night_rank', 'side market %', 'origin', 'event_id']:
        settled[col] = lines[col].values
    return settled


def _level_row(part: pd.DataFrame) -> dict:
    decided = part[part['result'].isin(['win', 'loss'])]
    wins, n = int((decided['result'] == 'win').sum()), len(decided)
    low, high = wilson_interval(wins, n)
    price = decided['side market %'].mean() if n else np.nan
    clv = decided['clv %'].dropna() if 'clv %' in decided else pd.Series(dtype=float)
    return {'nights': int(decided['game_date'].nunique()), 'bets': n,
            'hit %': 100 * wins / n if n else np.nan, 'ci low %': 100 * low, 'ci high %': 100 * high,
            'price said %': price, 'won − price pp': 100 * wins / n - price if n else np.nan,
            'ROI %': 100 * decided['profit'].mean() if n else np.nan,
            'ROI % std': 100 * decided['profit std'].mean() if n else np.nan,
            'CLV bets': len(clv), 'CLV %': clv.mean() if len(clv) else np.nan}


def star_scorecard(settled: pd.DataFrame) -> pd.DataFrame:
    """Per star level (5★ … 0★, then EVERY_LINE of settle_stars, the baseline): nights, decided bets, hit %, its
    95% range, the margin-free price's chance of the same sides ('price said %'), how much more often they won than
    that, ROI at the plain odds and after the stake tax ('ROI % std'), and the average CLV % where the close is
    known. Then '4★ − 1★': the difference of won − price pp with its 95% range from resampling whole nights (the
    scale works only if it's above 0). Pushes and voids are left out; lines without a rating only count in
    EVERY_LINE."""
    from decisions import MAX_STARS
    if settled.empty:
        return pd.DataFrame()
    rows = [{'stars': n, **_level_row(settled[settled['stars'] == n])} for n in range(MAX_STARS, -1, -1)]
    rows.append({'stars': EVERY_LINE, **_level_row(settled)})
    decided = settled[settled['result'].isin(['win', 'loss'])]
    top, bottom = decided[decided['stars'] == 4], decided[decided['stars'] == 1]
    if len(top) and len(bottom):
        from backtest.ablation import night_bootstrap
        excess = lambda d: 100 * ((d['result'] == 'win') - d['side market %'] / 100)
        both = pd.concat([top.assign(w=len(top) + len(bottom), x=excess(top) / len(top)),
                          bottom.assign(w=len(top) + len(bottom), x=-excess(bottom) / len(bottom))])
        low, high = night_bootstrap(both['game_date'].values, (both['x'] * both['w']).values)
        rows.append({'stars': '4★ − 1★', 'won − price pp': excess(top).mean() - excess(bottom).mean(),
                     'ci low %': low, 'ci high %': high})
    return pd.DataFrame(rows)


def paper_accumulators(settled: pd.DataFrame, legs: int = ACCUMULATOR_LEGS) -> pd.DataFrame:
    """A virtual accumulator (AKO) a night: the `legs` best 4★ lines (one per game already), 1 unit at the
    product of their odds. Superbet takes its 12% tax once, from the coupon's stake, so a win pays alpha × Π odds −
    1: it can only pay if the legs beat their prices before the tax by enough (about 4.4% each for 3 legs). A
    pushed or void leg counts as odds 1; a night with a leg pending or unresolved, or fewer legs, is left out. A
    record on paper only: nothing recommends it."""
    if settled.empty:
        return pd.DataFrame()
    top = settled[settled['stars'] >= 4].sort_values(['game_date', 'night_rank'], kind='stable')
    rows = []
    for night, part in top.groupby('game_date'):
        part = part.head(legs)
        if len(part) < legs or part['status'].isin(['pending', 'unresolved']).any():
            continue
        odds = np.where(part['result'].isin(['push', 'void']), 1.0, part['odds'].astype(float))
        won = not (part['result'] == 'loss').any()
        total = float(np.prod(odds))
        rows.append({'game_date': night,
                     'legs': " · ".join(f"{r['name']} {r['pick']} {r['line']:g} {r['bet_type']} ({r['result']})"
                                        for _, r in part.iterrows()),
                     'odds': total, 'result': 'win' if won else 'loss', 'profit': total - 1 if won else -1.0,
                     'profit std': alpha(SUPERBET_STANDARD) * total - 1 if won else -1.0})
    out = pd.DataFrame(rows)
    if len(out):
        out['cumulative std'] = out['profit std'].cumsum()
    return out
