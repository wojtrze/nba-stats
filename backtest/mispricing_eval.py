"""Evaluating the mispricing hypotheses of docs/hipotezy_wyceny.md: H1, H2 and H6 on the nights after D.

    python -m backtest.mispricing_eval [--d YYYY-MM-DD]

Uses the app's own detectors (dashboard/mispricing.py) on every Superbet offer saved before tip-off. A game read
by the schedule (superbet_event_fetches) is rebuilt from superbet_prop_quotes, which hold only changes: at every
read, each line is its last quote so far. Older games come from the dashboard's superbet_props snapshots. The
detectors see only the player's games before that night and league numbers from the games before it.

  a. Does the signal pay (decides the verdict): a signal is a side whose chance clears its after-tax break-even,
     counted once per game, player, bet and side, at its first read where it could be taken (the next read still
     had the same line and odds not worse; a signal at a game's last read can't be checked and isn't counted).
     Measured by the after-tax CLV (tracking.add_clv, valid closes only) and the after-tax ROI settled with ESPN.
  b. Does the mechanism work (descriptive): at each line's last quote before tip-off, by how much the signal's
     side won more often than its margin-free price, beyond the tilt of the same stat and side on all of the
     hypothesis's lines, for a gap of at least MECHANISM_GAP_PP. H1b instead asks whether the combo's price moved
     toward its parts by the close in more than half of the cases (gap ≥ H1B_GAP_PP).

Verdicts follow the registry's rules on the nights after D (at least MIN_NIGHTS): admitted when the low end of the
99% range (nine hypotheses) of the CLV or ROI is above 0 with at least MIN_SIGNALS signals; rejected when a high
end is below 0, or the mean is ≤ 0 after REJECT_SIGNALS signals; no signals below one per NIGHTS_PER_SIGNAL nights;
otherwise wait. Ranges come from resampling whole nights. The nights up to D are shown for comparison with the
registry's exploration and never decide. The report never sets data/backtest/mispricing_status.json: that's done
by hand after reading it. Writes data/backtest/mispricing.md.
"""
import argparse
import logging
import os
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

import backtest  # noqa: F401  (puts dashboard/ on the path)
from backtest.ablation import night_bootstrap
from backtest.run import OUT_DIR, markdown
from metrics import COST_PROFILES, SUPERBET_STANDARD, no_vig
from mispricing import (COMBOS, combo_signals, league_rates, league_spreads, pooled_correlations,
                        shooting_signals, spread_signals)
from safe_io import atomic_write_text
from tracking import PROP_KEY

log = logging.getLogger(__name__)

REPORT_FILE = os.path.join(OUT_DIR, 'mispricing.md')
D = '2026-11-01'
HYPOTHESES = ('H1', 'H2', 'H6')
LEVEL = 0.99
MIN_NIGHTS = 10
MIN_SIGNALS = 60
REJECT_SIGNALS = 150
NIGHTS_PER_SIGNAL = 5
MECHANISM_GAP_PP = 4.0
H1B_GAP_PP = 3.0
TAX = COST_PROFILES[SUPERBET_STANDARD]
LINE = ['bet_type', 'line', 'over_odds', 'under_odds']
SIGNAL = ['event_id', 'player_id_ESPN', 'hypothesis', 'bet_type', 'side']


def _utc(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, utc=True)


def _night(tip: pd.Series) -> pd.Series:
    return tip.dt.tz_convert('US/Eastern').dt.tz_localize(None).dt.normalize()


def offers(props: pd.DataFrame, quotes: pd.DataFrame, fetches: pd.DataFrame) -> pd.DataFrame:
    """Every line as offered at every read before tip-off: at (the read), event_id, tip, name_ESPN, bet_type,
    line, over_odds, under_odds, source ('schedule' or 'snapshot'). A line withdrawn (empty odds) or not yet
    listed at a read isn't in it."""
    frames = []
    scheduled = set()
    if len(fetches) and len(quotes):
        reads = fetches.assign(at=_utc(fetches['fetched_at']), tip=_utc(fetches['start_time']))
        reads = reads[reads['at'] < reads['tip']].drop_duplicates(['event_id', 'at'])[['event_id', 'at', 'tip']]
        q = quotes.assign(at=_utc(quotes['fetched_at'])).drop(columns='fetched_at').sort_values('at')
        keys = q[PROP_KEY].drop_duplicates()
        grid = reads.merge(keys, on='event_id').sort_values('at')
        rebuilt = pd.merge_asof(grid, q, on='at', by=PROP_KEY, direction='backward')
        frames.append(rebuilt.assign(source='schedule'))
        scheduled = set(reads['event_id'])
    if len(props):
        s = props.assign(at=_utc(props['fetched_at']), tip=_utc(props['start_time']))
        s = s[(s['at'] < s['tip']) & ~s['event_id'].isin(scheduled)]
        frames.append(s[['at', 'event_id', 'tip'] + PROP_KEY[1:] + LINE[1:]].assign(source='snapshot'))
    if not frames:
        return pd.DataFrame(columns=['at', 'event_id', 'tip', *PROP_KEY[1:], *LINE[1:], 'source'])
    out = pd.concat(frames, ignore_index=True)
    out = out.dropna(subset=['line', 'over_odds', 'under_odds'])
    return out.drop_duplicates(['at'] + PROP_KEY, keep='last').sort_values(['at'] + PROP_KEY, ignore_index=True)


def player_ids(offered: pd.DataFrame, props: pd.DataFrame, logs: pd.DataFrame) -> pd.Series:
    """Each offered line's player_id_ESPN: the snapshot's for the same game and name, else the gamelogs' when the
    name belongs to one player only."""
    known = props.dropna(subset=['player_id_ESPN']).drop_duplicates(['event_id', 'name_ESPN'], keep='last')
    pid = offered[['event_id', 'name_ESPN']].merge(
        known[['event_id', 'name_ESPN', 'player_id_ESPN']], on=['event_id', 'name_ESPN'], how='left')['player_id_ESPN']
    named = logs.drop_duplicates(['player_name_ESPN', 'player_id_ESPN'])
    unique = named.groupby('player_name_ESPN')['player_id_ESPN'].transform('size') == 1
    by_name = named[unique].set_index('player_name_ESPN')['player_id_ESPN']
    pid.index = offered.index
    return pid.fillna(offered['name_ESPN'].map(by_name)).astype('Int64')


def detect(offered: pd.DataFrame, logs: pd.DataFrame) -> pd.DataFrame:
    """Every detector's output (not only the signals: all compared lines) at each read where a player's lines
    changed (the same lines give the same output until the next change). One row per read and output: night, at,
    event_id, name_ESPN, player_id_ESPN, hypothesis, bet_type, line, side, odds, over_odds, under_odds, p_ours,
    p_book, gap_pp, clears."""
    offered = offered.assign(night=_night(offered['tip']))
    by_player = dict(tuple(logs.groupby('player_id_ESPN')))
    league: Dict = {}
    rows: List[Dict] = []
    for (night, event, pid), player in offered.dropna(subset=['player_id_ESPN']).groupby(
            ['night', 'event_id', 'player_id_ESPN']):
        if pid not in by_player:
            continue
        games = by_player[pid][by_player[pid]['Date'] < night].sort_values('Date')
        if night not in league:
            before = logs[logs['Date'] < night]
            league[night] = (pooled_correlations(before), league_rates(before), league_spreads(before))
        prior, rates, spreads = league[night]
        last = None
        for at, lines in player.groupby('at'):
            lines = lines.sort_values('bet_type')
            fingerprint = tuple(map(tuple, lines[LINE].values))
            if fingerprint == last:
                continue
            last = fingerprint
            for s in (combo_signals(lines, games, prior, at, status={}) +
                      shooting_signals(lines, games, rates, at, status={}) +
                      spread_signals(lines, games, spreads, at, status={})):
                quote = lines[lines['bet_type'] == s['bet_type']].iloc[-1]
                rows.append({'night': night, 'at': at, 'event_id': event, 'name_ESPN': quote['name_ESPN'],
                             'player_id_ESPN': pid, 'source': quote['source'],
                             'over_odds': quote['over_odds'], 'under_odds': quote['under_odds'],
                             **{k: s[k] for k in ('hypothesis', 'bet_type', 'line', 'side', 'odds', 'p_ours',
                                                  'p_book', 'gap_pp', 'clears')}})
    return pd.DataFrame(rows)


def _next_quote(rows: pd.DataFrame, offered: pd.DataFrame) -> pd.DataFrame:
    """For each row, the same line at its game's next read: next line / next over / next under (NaN when the game
    wasn't read again or the line was gone)."""
    reads = offered[['event_id', 'at']].drop_duplicates().sort_values(['event_id', 'at'])
    reads['next at'] = reads.groupby('event_id')['at'].shift(-1)
    out = rows.merge(reads, on=['event_id', 'at'], how='left')
    nxt = offered[['event_id', 'at'] + PROP_KEY[1:] + LINE[1:]].rename(
        columns={'at': 'next at', 'line': 'next line', 'over_odds': 'next over', 'under_odds': 'next under'})
    out = out.merge(nxt, on=['event_id', 'next at', 'name_ESPN', 'bet_type'], how='left')
    out.index = rows.index
    return out


def takeable(rows: pd.DataFrame, offered: pd.DataFrame) -> pd.Series:
    """'yes' when the game's next read still had the same line and the side's odds not worse, 'no' when it hadn't,
    'unchecked' when the game wasn't read again before tip-off."""
    n = _next_quote(rows, offered)
    odds = np.where(n['side'] == 'Over', n['next over'], n['next under'])
    ok = (n['next line'] == n['line']) & (odds >= n['odds'])
    return pd.Series(np.select([n['next at'].isna(), ok], ['unchecked', 'yes'], 'no'), index=rows.index)


def settle(rows: pd.DataFrame, logs: pd.DataFrame) -> pd.DataFrame:
    """rows with actual (the player's number that night, a combo summed from its parts) and won (1/0; NaN when he
    didn't play)."""
    tonight = logs.drop_duplicates(['player_id_ESPN', 'Date'], keep='last').copy()
    for combo, parts in COMBOS.items():
        tonight[combo] = tonight[list(parts)].sum(axis=1)
    stats = sorted(set(rows['bet_type']) & set(tonight.columns)) if len(rows) else []
    long = tonight.melt(id_vars=['player_id_ESPN', 'Date'], value_vars=stats, var_name='bet_type',
                        value_name='actual')
    long = long.rename(columns={'Date': 'night'}).astype({'player_id_ESPN': 'Int64'})
    out = rows.merge(long, on=['player_id_ESPN', 'night', 'bet_type'], how='left')
    out.index = rows.index
    over = out['actual'] > out['line']
    won = np.where(out['side'] == 'Over', over, out['actual'] < out['line']).astype(float)
    return out.assign(won=np.where(out['actual'].notna(), won, np.nan))


def signals(outputs: pd.DataFrame, offered: pd.DataFrame, logs: pd.DataFrame,
            closing: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Test a's signals: outputs that clear the break-even, each (game, player, hypothesis, bet, side) once at its
    first read where it could be taken, settled (won, profit std per unit after tax) and with the after-tax CLV
    (clv % std) when closing is given. Signals that never could be taken are kept with taken = 'no' / 'unchecked'
    and no result."""
    clears = outputs[outputs['clears'].astype(bool)].sort_values('at')
    if clears.empty:
        return clears.assign(taken=pd.Series(dtype=str))
    clears = clears.assign(taken=takeable(clears, offered))
    clears['rank'] = clears['taken'].map({'yes': 0, 'unchecked': 1, 'no': 2})
    first = clears.sort_values(['rank', 'at'], kind='stable').drop_duplicates(SIGNAL).drop(columns='rank')
    first = settle(first, logs)
    played = (first['taken'] == 'yes') & first['won'].notna()
    first['profit std'] = np.where(first['won'] == 1, TAX * first['odds'] - 1, -1.0)
    first['profit std'] = first['profit std'].where(played)
    if closing is not None and len(closing):
        from tracking import add_clv
        first = add_clv(first.assign(pick=first['side']), closing)
        first['clv % std'] = first['clv % std'].where(first['taken'] == 'yes')
    return first.sort_values('at', ignore_index=True)


def economic(sig: pd.DataFrame, nights: int) -> Dict:
    """Test a's numbers and verdict for one hypothesis's signals over `nights` nights."""
    taken = sig[sig['taken'] == 'yes'] if len(sig) else sig
    settled = taken[taken['profit std'].notna()] if len(taken) else taken
    row = {'nights': nights, 'signals': len(taken), 'not takeable': int((sig['taken'] == 'no').sum()) if len(sig) else 0,
           'unchecked': int((sig['taken'] == 'unchecked').sum()) if len(sig) else 0, 'settled': len(settled),
           'won %': 100 * settled['won'].mean() if len(settled) else np.nan}
    roi = 100 * settled['profit std'] if len(settled) else pd.Series(dtype=float)
    low, high = night_bootstrap(settled['night'].values, roi.values, level=LEVEL) if len(settled) else (np.nan,) * 2
    row |= {'ROI after tax %': roi.mean() if len(roi) else np.nan, 'ROI low': low, 'ROI high': high}
    clv = taken[taken['clv % std'].notna()] if len(taken) and 'clv % std' in taken else taken.iloc[0:0]
    c_low, c_high = (night_bootstrap(clv['night'].values, clv['clv % std'].values, level=LEVEL) if len(clv)
                     else (np.nan, np.nan))
    row |= {'with a close': len(clv), 'CLV after tax %': clv['clv % std'].mean() if len(clv) else np.nan,
            'CLV low': c_low, 'CLV high': c_high}
    return row | verdict(row)


def verdict(r: Dict) -> Dict:
    """The registry's verdict on test a's numbers: {'verdict', 'why'}. The main measure is the CLV when most
    signals have a valid close, else the ROI."""
    if r['nights'] < MIN_NIGHTS:
        return {'verdict': 'wait', 'why': f"{r['nights']} of the {MIN_NIGHTS} nights a verdict needs"}
    if r['signals'] * NIGHTS_PER_SIGNAL < r['nights']:
        return {'verdict': 'no signals', 'why': f"{r['signals']} signals on {r['nights']} nights: fewer than one "
                                                f"per {NIGHTS_PER_SIGNAL} nights"}
    main = 'CLV' if r['with a close'] >= r['signals'] / 2 else 'ROI'
    mean = r['CLV after tax %'] if main == 'CLV' else r['ROI after tax %']
    lows = {m: r[f'{m} low'] for m in ('CLV', 'ROI') if pd.notna(r[f'{m} low'])}
    highs = {m: r[f'{m} high'] for m in ('CLV', 'ROI') if pd.notna(r[f'{m} high'])}
    up = [m for m, v in lows.items() if v > 0]
    down = [m for m, v in highs.items() if v < 0]
    if up and down:
        return {'verdict': 'wait', 'why': f"the ranges disagree: {', '.join(up)} above 0, {', '.join(down)} below"}
    if up and r['signals'] >= MIN_SIGNALS:
        return {'verdict': 'admitted', 'why': f"the low end of the {LEVEL:.0%} range of the {up[0]} is above 0"}
    if down:
        return {'verdict': 'rejected', 'why': f"the high end of the {LEVEL:.0%} range of the {down[0]} is below 0"}
    if r['signals'] >= REJECT_SIGNALS and pd.notna(mean) and mean <= 0:
        return {'verdict': 'rejected', 'why': f"the mean {main} is ≤ 0 after {r['signals']} signals"}
    if up:
        return {'verdict': 'wait', 'why': f"the {up[0]}'s range is above 0, but {r['signals']} of the "
                                          f"{MIN_SIGNALS} signals it needs"}
    return {'verdict': 'wait', 'why': "neither range is clear of 0 yet"}


def last_quotes(outputs: pd.DataFrame) -> pd.DataFrame:
    """Each line's detector output at its last read before tip-off."""
    if outputs.empty:
        return outputs
    return outputs.sort_values('at').drop_duplicates(['event_id', 'player_id_ESPN', 'hypothesis', 'bet_type'],
                                                     keep='last')


def mechanism(last: pd.DataFrame, gap_pp: float = MECHANISM_GAP_PP) -> Dict:
    """Test b on one hypothesis's settled last quotes: how much the signal's side (gap ≥ gap_pp) won more often
    than its price, plain and beyond the tilt of the same stat and side on all of its lines; with the tilt itself
    (Under's wins minus its price, pp, by stat)."""
    x = last[last['won'].notna()].copy()
    x['edge'] = x['won'] - x['p_book']
    x['under edge'] = np.where(x['side'] == 'Under', x['edge'], -x['edge'])
    tilt = x.groupby('bet_type')['under edge'].mean()
    x['beyond'] = x['edge'] - np.where(x['side'] == 'Under', 1, -1) * x['bet_type'].map(tilt)
    y = x[x['gap_pp'] >= gap_pp]
    low, high = night_bootstrap(y['night'].values, 100 * y['edge'].values, level=LEVEL) if len(y) else (np.nan,) * 2
    b_low, b_high = (night_bootstrap(y['night'].values, 100 * y['beyond'].values, level=LEVEL) if len(y)
                     else (np.nan, np.nan))
    return {'lines': len(x), f'gap ≥ {gap_pp:g} pp': len(y), 'nights': int(y['night'].nunique()),
            'won %': 100 * y['won'].mean() if len(y) else np.nan,
            'price %': 100 * y['p_book'].mean() if len(y) else np.nan,
            'won − price pp': 100 * y['edge'].mean() if len(y) else np.nan, 'low': low, 'high': high,
            'beyond the tilt pp': 100 * y['beyond'].mean() if len(y) else np.nan, 'beyond low': b_low,
            'beyond high': b_high, 'tilt': (100 * tilt).round(1).to_dict()}


def combo_drift(outputs: pd.DataFrame, last: pd.DataFrame, gap_pp: float = H1B_GAP_PP) -> Dict:
    """H1b: for each combo line whose gap first reached gap_pp, whether by its last read the combo's price moved
    toward its parts (same line: the side's margin-free chance rose; another line: the line moved the side's way).
    Lines whose price didn't move aren't counted. Also H1's method check: the mean signed gap (+ = parts say Over)
    on all last quotes, which should lie in [−1, 1] pp."""
    h1 = outputs[(outputs['hypothesis'] == 'H1') & (outputs['gap_pp'] >= gap_pp)].sort_values('at')
    first = h1.drop_duplicates(['event_id', 'player_id_ESPN', 'bet_type'])
    end = last[last['hypothesis'] == 'H1'][['event_id', 'player_id_ESPN', 'bet_type', 'line', 'over_odds',
                                             'under_odds', 'at']]
    m = first.merge(end, on=['event_id', 'player_id_ESPN', 'bet_type'], suffixes=('', ' end'))
    m = m[m['at end'] > m['at']]
    sign = np.where(m['side'] == 'Over', 1, -1)
    p_end = np.array([no_vig(o, u)[0] for o, u in zip(m['over_odds end'], m['under_odds end'])])
    p_end = np.where(m['side'] == 'Over', p_end, 1 - p_end)
    move = np.where(m['line end'] == m['line'], p_end - m['p_book'], sign * (m['line end'] - m['line']))
    moved = np.abs(move) > 1e-9
    toward = (move[moved] > 0).astype(float)
    nights = m['night'].values[moved]
    low, high = night_bootstrap(nights, 100 * toward, level=LEVEL) if len(toward) else (np.nan, np.nan)
    h1_last = last[last['hypothesis'] == 'H1']
    signed = np.where(h1_last['side'] == 'Over', h1_last['gap_pp'], -h1_last['gap_pp'])
    return {f'gap ≥ {gap_pp:g} pp': len(m), 'moved': int(moved.sum()),
            'toward the parts %': 100 * toward.mean() if len(toward) else np.nan, 'low': low, 'high': high,
            'mean signed gap pp (all lines)': float(signed.mean()) if len(signed) else np.nan}


def evaluate(outputs: pd.DataFrame, offered: pd.DataFrame, logs: pd.DataFrame, d=D,
             closing: Optional[pd.DataFrame] = None) -> Dict[str, Dict]:
    """Per period ('exploration': nights ≤ d, 'evaluation': nights > d) and hypothesis: {'a', 'b'} (and 'h1b' for
    H1)."""
    d = pd.Timestamp(d)
    if outputs.empty:
        return {}
    settled_nights = set(logs['Date'].unique())
    outputs = outputs[outputs['night'].isin(settled_nights)]
    sig = signals(outputs, offered, logs, closing)
    last = settle(last_quotes(outputs), logs)
    result = {}
    for period, keep in (('exploration', lambda n: n <= d), ('evaluation', lambda n: n > d)):
        out_p = outputs[keep(outputs['night'])]
        nights = int(out_p['night'].nunique())
        for h in HYPOTHESES:
            s = sig[(sig['hypothesis'] == h) & keep(sig['night'])] if len(sig) else sig
            lq = last[(last['hypothesis'] == h) & keep(last['night'])]
            entry = {'a': economic(s, nights), 'b': mechanism(lq)}
            if h == 'H1':
                entry['h1b'] = combo_drift(out_p, last[keep(last['night'])])
            result.setdefault(period, {})[h] = entry
    return result


def report(result: Dict[str, Dict], d=D) -> str:
    text = ["# Mispricing hypotheses: evaluation", "", __doc__.split("\n\n", 2)[2].strip(), ""]
    for period, title in (('evaluation', f"Evaluation (nights after {d}): decides"),
                          ('exploration', f"Exploration (nights up to {d}): for comparison only")):
        per = result.get(period, {})
        if not per:
            continue
        text += [f"## {title}", ""]
        a = pd.DataFrame([{'hypothesis': h, **e['a']} for h, e in per.items()])
        text += ["### a. Does the signal pay (after tax)", "", markdown(a), ""]
        b = pd.DataFrame([{'hypothesis': h, **{k: v for k, v in e['b'].items() if k != 'tilt'}}
                          for h, e in per.items() if h != 'H1'])
        text += ["### b. Does the mechanism work (last quote, settled)", "", markdown(b), ""]
        text += [f"Under's wins minus its price on all lines, pp: " +
                 "; ".join(f"{h} {e['b']['tilt']}" for h, e in per.items() if h != 'H1'), ""]
        if 'H1' in per:
            text += ["### H1b: did the combo's price move toward its parts by the close", "",
                     markdown(pd.DataFrame([per['H1']['h1b']])), ""]
    return "\n".join(text)


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument('--d', default=D, help="D, the last night before the evaluation (default %(default)s)")
    args = parser.parse_args()
    from espn_scraper import CURRENT_SEASON, SEASONS
    from espn_scraper.storage import load_player_gamelogs, read_snapshot, snapshot_file
    from tracking import closing_props
    read = lambda name: read_snapshot(snapshot_file(CURRENT_SEASON, name)) \
        if os.path.exists(snapshot_file(CURRENT_SEASON, name)) else pd.DataFrame()
    logs = load_player_gamelogs(sorted(SEASONS))
    logs = logs[logs['season_type'] != 'pre'].assign(Date=lambda x: pd.to_datetime(x['Date']))
    logs['player_id_ESPN'] = logs['player_id_ESPN'].astype('Int64')
    props, quotes, fetches = read('superbet_props'), read('superbet_prop_quotes'), read('superbet_event_fetches')
    offered = offers(props, quotes, fetches)
    offered['player_id_ESPN'] = player_ids(offered, props, logs)
    log.info("%d lines offered at %d reads", len(offered), offered[['event_id', 'at']].drop_duplicates().shape[0])
    outputs = detect(offered, logs)
    result = evaluate(outputs, offered, logs, args.d, closing_props(quotes, fetches))
    text = report(result, args.d)
    atomic_write_text(REPORT_FILE, text)
    print(text)


if __name__ == '__main__':
    main()
