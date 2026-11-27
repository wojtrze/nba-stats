"""Audit harness (read-only): rebuild what the props page would show for saved Superbet fetches.

For each chosen fetch: models.price_props as of that fetch (nightly.recompute_props: games before the night, the
RotoWire version saved before the fetch, the game odds of the same fetch), reasons.flag_props, tracking.prop_movement
from the snapshots up to the fetch, decisions.game_decisions judged at the fetch time, then for every priced line
reasons.offer_context + reasons.prop_reasons + mispricing.offer_signals, once as dashboard_v2 calls it (no role, so
no H5) and once with RotoWire's role (H5 reachable).

Nothing under data/ is written. Output: one pickle per fetch in --out (default: $AUDIT_OUT or ./audit_out).

    python audit/reasons/harness.py --fetch 2026-11-10T20:00:00Z --out <dir>
    python audit/reasons/harness.py --last-per-night 8 --out <dir>

Reproducibility: a fetch is reproducible only when its saved calibration_id equals the current one and no games were
added to the logs after the fetch for players of that night (the logs are filtered to games before the night, so
later games never leak in). Fetches saved with another calibration are re-priced with the current one and are
marked replay_only: their texts are what the current code says about that offer, not what was shown then.
"""
import argparse
import os
import pickle
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# AUDIT_CODE: another checkout's root to take dashboard/ from (a frozen 'before' copy); data always from ROOT
CODE = os.environ.get('AUDIT_CODE', ROOT)
sys.path[:0] = [os.path.join(CODE, 'dashboard'), CODE, ROOT]
os.chdir(ROOT)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from espn_scraper import SEASONS  # noqa: E402
from espn_scraper.storage import load_games, load_player_gamelogs, load_snapshot  # noqa: E402


def load():
    from models import prepare_logs
    from name_resolver import NameResolver
    props = load_snapshot('superbet_props')
    odds = load_snapshot('superbet_game_odds')
    rotowire = load_snapshot('rotowire_lineups', display_names=False)
    logs = prepare_logs(load_player_gamelogs(sorted(SEASONS)))
    games = load_games(sorted(SEASONS))
    resolver = NameResolver(logs)
    saved_ids = props['player_id_ESPN'].copy() if 'player_id_ESPN' in props else None
    props = resolver.add_ids(props.drop(columns=['player_id_ESPN'], errors='ignore'), team_cols=('home', 'away'))
    rotowire = resolver.add_ids(rotowire)
    return props, odds, rotowire, logs, games, saved_ids


def run_fetch(fetched_at, props, odds, rotowire, logs, games, out_dir, profile='superbet_standard'):
    from decisions import game_decisions, offer_decision
    from mispricing import offer_signals
    from metrics import ACTIVE_PROFILE, reprice_net
    from models import top_up_logs, load_calibration, calibration_id as current_calibration_id
    from nightly import et_night, lineups_before_tip, recompute_props
    from reasons import offer_context, prop_reasons
    from tracking import prop_movement

    rows_all = props[props['fetched_at'] == fetched_at]
    nights = et_night(rows_all['start_time'])
    coef = load_calibration()
    result = {'fetched_at': fetched_at, 'nights': {}}
    for night, rows in rows_all.groupby(nights):
        t0 = time.time()
        night = pd.Timestamp(night)
        lineups = lineups_before_tip(rotowire, night, pd.Timestamp(fetched_at) + pd.Timedelta(seconds=1))
        table = recompute_props(rows, logs, games, lineups, odds[odds['fetched_at'] == fetched_at],
                                et_night(pd.Series([fetched_at])).iloc[0], full=True)
        history = props[pd.to_datetime(props['fetched_at'], utc=True) <= pd.Timestamp(fetched_at)]
        table = prop_movement(history, table)
        seen = history.groupby(['event_id', 'name_ESPN', 'bet_type']).size().rename('snapshots').reset_index()
        table['snapshots'] = table.merge(seen, on=['event_id', 'name_ESPN', 'bet_type'], how='left')['snapshots'].values
        saved = rows[['calibration_id', 'model_pct', 'eval_side', 'ev_net_100', 'decision', 'red_flag', 'stars']]
        table = table.join(saved.add_prefix('saved_'))
        if profile != ACTIVE_PROFILE:
            table = reprice_net(table, profile)   # as core.data.priced_props does for the sidebar's profile
        lu = lineups.copy()
        decisions = game_decisions(table, 'fitted', lu, fetched_at, pd.Timestamp(fetched_at))

        before = logs[logs['Date'] < night]
        season = before['season_id'].max()
        from models import DEFAULT_SEASON_TYPES
        scope = top_up_logs(before[(before['season_id'] == season) & before['season_type'].isin(DEFAULT_SEASON_TYPES)],
                            before, season, rows['player_id_ESPN'].dropna().unique())
        names = scope.groupby('player_id_ESPN')['player_display_name'].last()
        lineup_at = lineups['fetched_at'].max() if len(lineups) else None
        lines = []
        for i, row in table.iterrows():
            if not row.get('side') or pd.isna(row.get('side odds')):
                continue
            pid = row['player_id']
            games_ = scope[scope['player_id_ESPN'] == pid].sort_values('Date')
            hist = before[(before['player_id_ESPN'] == pid) & before['season_type'].isin(DEFAULT_SEASON_TYPES)
                          & (before['OPP'].str.lower() == (row['opp'] or ''))]
            bet = offer_context(row, games_, scope, lineups, names, fetched_at, lineup_at, coef=coef)
            player_lines = table[(table['player_id'] == pid) & (table['event_id'] == row['event_id'])]
            sig_ui = offer_signals(player_lines, games_, scope, fetched_at, profile=profile)
            status = str(row.get('RotoWire') or '')
            role = 'starter' if status.startswith('starter') else 'bench' if status == 'bench' else None
            sig_role = offer_signals(player_lines, games_, scope, fetched_at, role=role, profile=profile)
            reasons_en = prop_reasons(bet, games_, hist, 'en', signals=sig_ui)
            reasons_pl = prop_reasons(bet, games_, hist, 'pl', signals=sig_ui)
            reasons_role = prop_reasons(bet, games_, hist, 'en', signals=sig_role)
            lines.append({'index': i, 'row': row.to_dict(), 'bet': bet, 'n_games': len(games_),
                          'signals_ui': sig_ui, 'signals_role': sig_role, 'reasons_en': reasons_en,
                          'reasons_pl': reasons_pl, 'reasons_role': reasons_role,
                          'decision': offer_decision(decisions[row['event_id']], row)})
        result['nights'][str(night.date())] = {'table': table, 'decisions': decisions, 'lines': lines,
                                               'lineups': lineups, 'seconds': time.time() - t0}
        print(f"{fetched_at} night {night.date()}: {len(table)} lines, {len(lines)} priced, "
              f"{time.time() - t0:.0f} s", flush=True)
    result['profile'] = profile
    result['calibration_now'] = current_calibration_id()
    result['saved_calibration'] = sorted(rows_all['calibration_id'].dropna().unique().tolist())
    result['replay_only'] = result['saved_calibration'] != [result['calibration_now']]
    path = os.path.join(out_dir, 'fetch_' + fetched_at.replace(':', '').replace('-', '') + '.pkl')
    with open(path, 'wb') as f:
        pickle.dump(result, f)
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fetch', action='append', default=[])
    parser.add_argument('--last-per-night', type=int, default=0,
                        help='also the last fetch before the first tip-off of each of the last N nights')
    parser.add_argument('--out', default=os.environ.get('AUDIT_OUT', 'audit_out'))
    parser.add_argument('--profile', action='append', default=[],
                        help='cost profile(s) to price with (default superbet_standard); one sub-folder each')
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)
    props, odds, rotowire, logs, games, _ = load()
    fetches = list(args.fetch)
    if args.last_per_night:
        from nightly import et_night
        p = props.assign(night=et_night(props['start_time']).values)
        p = p[pd.to_datetime(p['fetched_at'], utc=True) < pd.to_datetime(p['start_time'], utc=True)]
        first_tip = p.groupby('night')['start_time'].min()
        for night in sorted(p['night'].unique())[-args.last_per_night:]:
            part = p[(p['night'] == night)
                     & (pd.to_datetime(p['fetched_at'], utc=True) < pd.to_datetime(first_tip[night], utc=True))]
            if len(part):
                fetches.append(part['fetched_at'].max())
    profiles = args.profile or ['superbet_standard']
    for profile in profiles:
        out = args.out if len(profiles) == 1 else os.path.join(args.out, profile)
        os.makedirs(out, exist_ok=True)
        for f in dict.fromkeys(fetches):
            print('->', run_fetch(f, props, odds, rotowire, logs, games, out, profile), flush=True)


if __name__ == '__main__':
    main()
