"""H3 (docs/hipotezy_wyceny.md): Superbet's team totals against its own player points lines (dashboard/team_total.py).

    python -m backtest.team_total [--d YYYY-MM-DD]

At every read of a game before tip-off (the schedule's reads rebuilt from the quote files, older games from the
dashboard's snapshots) the team's gap: Superbet's team total − the sum of its player PTS lines' medians − what the
team's other players usually score (RotoWire's out players left out, as of that read).

  a. The signal (decides): every PTS line of a team whose |gap| ≥ team_total.MIN_GAP, on the gap's side (Over when
     above 0), no profitability threshold. Counted and judged exactly as backtest/mispricing_eval's signals: once
     per game, player, bet and side at its first read where it could be taken (the next read still had the same
     line and odds not worse), after-tax CLV and ROI with 99% ranges from resampling whole nights, the registry's
     verdict.
  b. The mechanism (descriptive): at each PTS line's last read, the gap's side won − its margin-free price by
     |gap|, and per team the correlation of the gap with the players' points minus their lines and with the team's
     points minus its total (the team total should be right and the lines off, not the other way round).
  c. As a model input (descriptive, what backtest/ablation.py would ask of a new rung): on the settled PTS lines
     at their last read, the market's chance with an Over/Under bias against the same plus the line's shift (its
     share of the gap / its spread), fitted on the earlier 70% of the nights and scored on the rest; log loss minus
     the market's with a 95% range from resampling nights.

Nights up to D are recognition (the rule was written on D after looking at them); nights after D decide (at least
10). Writes data/backtest/team_total.md. The status in mispricing_status.json is set by hand.
"""
import argparse
import logging
import os
from typing import Dict

import numpy as np
import pandas as pd

import backtest  # noqa: F401  (puts dashboard/ on the path)
from backtest.absence_shift import night_range
from backtest.mispricing_eval import TAX, economic, settle, signals
from backtest.run import OUT_DIR, markdown
from news import _night, _utc, lineup_versions, offers, player_ids
from safe_io import atomic_write_text
import team_total as tt

log = logging.getLogger(__name__)

REPORT_FILE = os.path.join(OUT_DIR, 'team_total.md')
D = '2026-11-20'
GAME_KEY = ['event_id', 'market', 'side', 'line']
MARKETS = ('TOTAL', 'SPREAD', 'HOME_TOTAL', 'AWAY_TOTAL')
BANDS = [0, 3, 6, 10, 15, 1000]


def game_offers(game_odds: pd.DataFrame, game_quotes: pd.DataFrame, fetches: pd.DataFrame) -> pd.DataFrame:
    """The game markets (MARKETS) at every read before tip-off: at, event_id, market, side, line, odds, as
    news.offers rebuilds the player lines (the schedule's reads from the quote changes, else the snapshots)."""
    frames, scheduled = [], set()
    if len(fetches) and len(game_quotes):
        reads = fetches.assign(at=_utc(fetches['fetched_at']), tip=_utc(fetches['start_time']))
        reads = reads[reads['at'] < reads['tip']].drop_duplicates(['event_id', 'at'])[['event_id', 'at']]
        q = game_quotes[game_quotes['market'].isin(MARKETS)]
        q = q.assign(at=_utc(q['fetched_at'])).drop(columns='fetched_at').sort_values('at')
        q['line'] = q['line'].astype(float)
        grid = reads.merge(q[GAME_KEY].drop_duplicates(), on='event_id').sort_values('at')
        frames.append(pd.merge_asof(grid, q, on='at', by=GAME_KEY, direction='backward'))
        scheduled = set(reads['event_id'])
    if len(game_odds):
        s = game_odds[game_odds['market'].isin(MARKETS) & ~game_odds['event_id'].isin(scheduled)]
        s = s.assign(at=_utc(s['fetched_at']), tip=_utc(s['start_time']))
        frames.append(s[s['at'] < s['tip']][['at'] + GAME_KEY + ['odds']])
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=['at'] + GAME_KEY + ['odds'])
    return out.dropna(subset=['odds'])


def detect(offered: pd.DataFrame, games: pd.DataFrame, logs: pd.DataFrame, versions: Dict,
           teams: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """'teams': TEAM_COLUMNS + night, at at every read; 'lines': every PTS line at every read with its team's gap
    and shift, in mispricing_eval's outputs format (clears = |gap| ≥ MIN_GAP, side = the gap's)."""
    offered = offered.assign(night=_night(offered['tip']))
    game_at = dict(tuple(games.groupby(['event_id', 'at'])))
    teams = teams.set_index('event_id')
    team_rows, line_rows = [], []
    for night, tonight in offered.groupby('night'):
        before = logs[logs['Date'] < night]
        team_of = before.sort_values('Date').drop_duplicates('player_id_ESPN', keep='last') \
            .set_index('player_id_ESPN')['team'].to_dict()
        saved = versions.get(night, [])
        for (event, at), lines in tonight.groupby(['event_id', 'at']):
            if (event, at) not in game_at or event not in teams.index or not (lines['bet_type'] == tt.STAT).any():
                continue
            version = next((v for s, v in reversed(saved) if s <= at), None)
            home, away = teams.at[event, 'home'], teams.at[event, 'away']
            gaps = tt.team_gaps(lines, game_at[(event, at)], before, team_of, tt.out_ids(version), home, away)
            if gaps.empty:
                continue
            team_rows.append(gaps.assign(night=night, at=at))
            pts = lines[(lines['bet_type'] == tt.STAT) & lines['player_id_ESPN'].notna()].copy()
            pts['team'] = pts['player_id_ESPN'].map(team_of)
            pts = pts.merge(gaps[['team', 'gap']], on='team')
            if pts.empty:
                continue
            pts['shift'] = tt.line_shifts(pts, gaps, team_of).values
            side = np.where(pts['gap'] > 0, 'Over', 'Under')
            p_over = tt.over_chance(pts['over_odds'], pts['under_odds'])
            line_rows.append(pts.assign(
                hypothesis='H3', side=side, odds=np.where(side == 'Over', pts['over_odds'], pts['under_odds']),
                p_book=np.where(side == 'Over', p_over, 1 - p_over), clears=pts['gap'].abs() >= tt.MIN_GAP,
                gap_pp=np.nan, **{'price %': 100 * np.where(side == 'Over', p_over, 1 - p_over)}))
    cat = lambda f: pd.concat(f, ignore_index=True) if f else pd.DataFrame()
    return {'teams': cat(team_rows), 'lines': cat(line_rows)}


def mechanism(lines: pd.DataFrame, team_rows: pd.DataFrame, logs: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """b: the gap's side at each PTS line's last read by |gap| band, and the per-team correlations."""
    last = lines.sort_values('at').drop_duplicates(['event_id', 'player_id_ESPN', 'bet_type'], keep='last')
    last = settle(last, logs)
    last = last[last['won'].notna()].assign(edge=lambda x: 100 * (x['won'] - x['p_book']))
    last['|gap|'] = pd.cut(last['gap'].abs(), BANDS, right=False)
    rows = []
    for band, x in last.groupby('|gap|', observed=True):
        low, high = night_range(x['night'].values, x['edge'].values)
        rows.append({'|gap| points': str(band), 'lines': len(x), 'nights': x['night'].nunique(),
                     'won %': 100 * x['won'].mean(), 'price %': 100 * x['p_book'].mean(),
                     'won − price pp': x['edge'].mean(), 'low': low, 'high': high,
                     'ROI after tax %': 100 * np.where(x['won'] == 1, TAX * x['odds'] - 1, -1.0).mean()})
    # per team at its last read: players' points − their medians, team's points − T
    t = team_rows.sort_values('at').drop_duplicates(['event_id', 'team'], keep='last')
    lp = last.assign(diff=last['actual'] - tt.pts_median(last['line'], last['over_odds'], last['under_odds']))
    players = lp.groupby(['event_id', 'team'])['diff'].sum().rename('players − lines')
    team_pts = logs.groupby(['team', 'Date'])['PTS'].sum().rename('team pts').reset_index() \
        .rename(columns={'Date': 'night'})
    t = t.merge(players, on=['event_id', 'team']).merge(team_pts, on=['team', 'night'])
    t['team − T'] = t['team pts'] - t['T']
    corr = {'teams': len(t), 'nights': t['night'].nunique(), 'mean gap': t['gap'].mean(), 'sd gap': t['gap'].std(),
            'corr(gap, players − lines)': t['gap'].corr(t['players − lines']),
            'corr(gap, team − T)': t['gap'].corr(t['team − T'])}
    return {'bands': pd.DataFrame(rows), 'teams': pd.DataFrame([corr])}


def as_input(lines: pd.DataFrame, logs: pd.DataFrame) -> pd.DataFrame:
    """c: the shift as a model input, scored on the later 30% of the nights."""
    from backtest.ablation import night_bootstrap
    from backtest.calibrate import _logit, _sigmoid, fit
    last = settle(lines.sort_values('at').drop_duplicates(['event_id', 'player_id_ESPN', 'bet_type'], keep='last'),
                  logs)
    x = last[last['actual'].notna() & (last['actual'] != last['line'])]
    nights = np.sort(x['night'].unique())
    if len(nights) < 5:
        return pd.DataFrame()
    m = _logit(np.clip(tt.over_chance(x['over_odds'], x['under_odds']), 1e-4, 1 - 1e-4))
    z = (x['shift'] / tt.pts_sd(x['line'])).values
    y = (x['actual'] > x['line']).astype(float).values
    train = (x['night'] < nights[int(len(nights) * 0.7)]).values
    loss = lambda q: -(y[~train] * np.log(q) + (1 - y[~train]) * np.log(1 - q))
    market = loss(np.clip(_sigmoid(m[~train]), 1e-4, 1 - 1e-4))
    rows = []
    for name, cols in (("market + Over/Under bias", [m]), ("+ the team-total shift", [m, z])):
        design = np.column_stack(cols + [np.ones(len(x))])
        beta = fit(design[train], y[train])
        diff = loss(np.clip(_sigmoid(design[~train] @ beta), 1e-4, 1 - 1e-4)) - market
        low, high = night_bootstrap(x['night'].values[~train], diff)
        rows.append({'model': name, 'scored lines': int((~train).sum()), 'vs market': diff.mean(), 'low': low,
                     'high': high, 'shift coefficient': beta[1] if len(cols) == 2 else np.nan})
    return pd.DataFrame(rows)


def evaluate(out: Dict[str, pd.DataFrame], offered: pd.DataFrame, logs: pd.DataFrame, d, closing=None) -> Dict:
    d = pd.Timestamp(d)
    settled = set(logs['Date'].unique())
    lines = out['lines'][out['lines']['night'].isin(settled)]
    teams = out['teams'][out['teams']['night'].isin(settled)]
    sig = signals(lines, offered, logs, closing) if len(lines) else lines
    result = {'input': as_input(lines[lines['night'] <= d], logs) if len(lines) else pd.DataFrame()}
    for period, keep in (('recognition', lambda n: n <= d), ('evaluation', lambda n: n > d)):
        nights = int(keep(pd.Series(lines['night'].unique())).sum()) if len(lines) else 0
        s = sig[keep(sig['night'])] if len(sig) else sig
        row = economic(s, nights)
        done = s[(s['taken'] == 'yes') & s['won'].notna()] if len(s) else s
        if len(done):
            row['won − price pp'] = 100 * (done['won'] - done['p_book']).mean()
        lp, tp = lines[keep(lines['night'])], teams[keep(teams['night'])]
        result[period] = {'a': row, **(mechanism(lp, tp, logs) if len(lp) else {})}
    return result


def report(result: Dict, d) -> str:
    text = ["# H3: Superbet's team totals against its player points lines", "",
            __doc__.split("\n\n", 2)[2].strip(), "",
            f"Fixed with D: OFFSET {tt.OFFSET:g} points, MIN_GAP {tt.MIN_GAP:g}, others over the team's last "
            f"{tt.OTHERS_GAMES} games. A side needs about 8–11 pp over the price after tax.", ""]
    for period, title in (('evaluation', f"Evaluation (nights after {d}): decides"),
                          ('recognition', f"Recognition (nights up to {d}): describes")):
        r = result.get(period)
        if not r or not r['a'].get('nights'):
            continue
        text += [f"## {title}", "", "### a. The signal (after tax)", "", markdown(pd.DataFrame([r['a']])), ""]
        if 'bands' in r:
            text += ["### b. The gap's side at the last read, by |gap|", "", markdown(r['bands']), "",
                     "Per team at its last read:", "", markdown(r['teams'], '{:.3f}'), ""]
    if len(result.get('input', [])):
        text += ["## c. As a model input (recognition nights, the later 30% scored)", "",
                 markdown(result['input'], '{:.4f}'), ""]
    return "\n".join(text)


def load(read) -> Dict:
    """Everything detect needs, from the season's files."""
    from espn_scraper import SEASONS
    from espn_scraper.storage import load_player_gamelogs
    from metrics import add_combined_stats
    from name_resolver import NameResolver
    logs = load_player_gamelogs(sorted(SEASONS))
    logs = add_combined_stats(logs[logs['season_type'] != 'pre'].assign(Date=lambda x: pd.to_datetime(x['Date'])))
    logs['player_id_ESPN'] = logs['player_id_ESPN'].astype('Int64')
    props, quotes, fetches = read('superbet_props'), read('superbet_prop_quotes'), read('superbet_event_fetches')
    game_odds, game_quotes = read('superbet_game_odds'), read('superbet_game_quotes')
    offered = offers(props, quotes, fetches)
    offered['player_id_ESPN'] = player_ids(offered, props, logs)
    teams = pd.concat([props[['event_id', 'home', 'away']], game_odds[['event_id', 'home', 'away']]]) \
        .drop_duplicates('event_id')
    return {'logs': logs, 'offered': offered, 'games': game_offers(game_odds, game_quotes, fetches),
            'versions': lineup_versions(NameResolver(logs).add_ids(read('rotowire_lineups'))), 'teams': teams,
            'quotes': quotes, 'fetches': fetches}


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument('--d', default=D, help="D, the last recognition night (default %(default)s)")
    args = parser.parse_args()
    from espn_scraper import CURRENT_SEASON
    from espn_scraper.storage import read_snapshot, snapshot_file
    from tracking import closing_props
    read = lambda name: read_snapshot(snapshot_file(CURRENT_SEASON, name)) \
        if os.path.exists(snapshot_file(CURRENT_SEASON, name)) else pd.DataFrame()
    x = load(read)
    out = detect(x['offered'], x['games'], x['logs'], x['versions'], x['teams'])
    log.info("%d team reads, %d PTS line reads", len(out['teams']), len(out['lines']))
    result = evaluate(out, x['offered'], x['logs'], args.d, closing_props(x['quotes'], x['fetches']))
    text = report(result, args.d)
    atomic_write_text(REPORT_FILE, text)
    print(text)


if __name__ == '__main__':
    main()
