"""How close candidate projections (proj avg) come to the results: the point estimate alone, no chances.

    python -m backtest.projection_eval              # reuses the saved Superbet components (backtest.ablation)
    python -m backtest.projection_eval --refresh    # price the Superbet lines again first

Two sources, every number from the games before the one projected:
- A, the logs: every real game (regular, play-in, playoffs) of the stored seasons where the player played and had
  at least MIN_HISTORY earlier real games. No lines, so it scores the core estimate only. The role (starter or
  bench) is the game's starter flag: an oracle standing in for RotoWire's lineup.
- B, Superbet: each saved line judged by its last fetch before tip-off (backtest.ablation.superbet_components:
  the current model's components as of that fetch), settled from the logs. The role is RotoWire's version saved
  before that fetch (listed as a starter, else bench). Lines with no log row for the player (didn't play) are left
  out.

Candidates (core = minutes × per-minute rate):
- season mean: the current model's avg (the season's earlier games, topped up to TOP_UP_GAMES with the latest ones
  before them, as models.top_up_logs does);
- core: minutes = EWMA (half-life HALF_MIN games) of the minutes in the season's earlier games of tonight's role
  (all the season's games if none; every earlier game before the player's MIN_SEASON_GAMES-th of the season),
  rate = the season's stat ÷ minutes with last season's rate as a prior worth PRIOR_GAMES games (game_features);
  PRA (ARP) is the sum of the PTS, REB and AST cores;
- on B also the current proj avg and the current model's adjustments on top of the core: lineup adj (adj avg − avg),
  the pace factor and the matchup factor.

Reported per stat: MAE, bias (mean result − projection), on B the share of lines where the projection was closer
to the result than the line, within 10% of the result (insights._near, ours taken as the half-point line it falls
in) and the correlation of (projection − line) with (result − line): whether our disagreements with the line carry
information. *vs* = the candidate's MAE minus the reference's, with the 95% range from resampling whole nights.
Writes data/backtest/projection_eval.md.
"""
import argparse
import logging
import os
from typing import Dict

import numpy as np
import pandas as pd

import backtest  # noqa: F401  (puts dashboard/ on the path)
from backtest.ablation import last_pretip_lines, night_bootstrap
from backtest.run import OUT_DIR, markdown
from safe_io import atomic_write_text

log = logging.getLogger(__name__)

REPORT = os.path.join(OUT_DIR, 'projection_eval.md')
STATS = ['PTS', 'REB', 'AST', '3PM', 'ARP']
PARTS = {'ARP': ['PTS', 'REB', 'AST']}
REAL_TYPES = ['regular', 'playin', 'post']
HALF_MIN, HALF_RATE = 5, 20
PRIOR_GAMES, PRIOR_MINUTES = 5, 25     # last season's rate counts as 5 games of 25 minutes
MIN_SEASON_GAMES = 3                   # season minutes are used from the player's 3rd game of the season on
TOP_UP_GAMES = 10
MIN_HISTORY = 10


# --- point-in-time features: each game row gets numbers from the player's earlier real games only ---

def _starter(values: pd.Series) -> pd.Series:
    return values.astype(str).str.lower().isin(['true', '1', '1.0', 'yes'])


def _season_mean(g: pd.DataFrame, stat: str, top_up: int) -> np.ndarray:
    """Per row: the mean of the stat in the season's earlier games; with fewer than top_up of them, the latest
    top_up earlier games (the season's and the ones before)."""
    values, seasons = g[stat].to_numpy(float), g['season_id'].to_numpy()
    out = np.full(len(values), np.nan)
    for i in range(1, len(values)):
        season = values[:i][seasons[:i] == seasons[i]]
        out[i] = season.mean() if len(season) >= top_up else values[max(0, i - top_up):i].mean()
    return out


def game_features(logs: pd.DataFrame, half_min: float = HALF_MIN, half_rate: float = HALF_RATE,
                  top_up: int = TOP_UP_GAMES, prior_games: float = PRIOR_GAMES,
                  prior_minutes: float = PRIOR_MINUTES) -> pd.DataFrame:
    """logs (prepare_logs, any game types) → its real games where the player played, sorted, with:
    - history (earlier real games), n season (earlier real games of the season), starter;
    - 'min st' / 'min bn' / 'min all': EWMA (half_min) of minutes in the season's earlier starter / bench / all
      games, and 'xmin st' / 'xmin bn' / 'xmin all' the same over every earlier game (the start of a season);
    - per stat 'rate <stat>': the season's stat ÷ minutes so far, with the player's rate of the season before as a
      prior worth prior_games games of prior_minutes (scoring changes from season to season: 2026 started ~3
      points per team below 2025); without a season before, the EWMA (half_rate) rate of his earlier games;
    - 'mean <stat>': the season mean with top-up (the current model's avg)."""
    real = logs[logs['season_type'].isin(REAL_TYPES) & (logs['MIN'] > 0)]
    real = real.sort_values(['player_id_ESPN', 'Date', 'game_id'], kind='stable').reset_index(drop=True)
    real['starter'] = _starter(real['starter'])
    by = real.groupby('player_id_ESPN', sort=False)
    by_season = real.groupby(['player_id_ESPN', 'season_id'], sort=False)
    prior_ewm = lambda groups, col, hl: groups[col].transform(
        lambda x: x.ewm(halflife=hl, ignore_na=True).mean().shift(1))
    before = lambda col: by_season[col].transform(lambda x: x.cumsum().shift(1)).fillna(0)
    real['history'], real['n season'] = by.cumcount(), by_season.cumcount()
    real['_min st'] = real['MIN'].where(real['starter'])
    real['_min bn'] = real['MIN'].where(~real['starter'])
    for key, col in (('st', '_min st'), ('bn', '_min bn'), ('all', 'MIN')):
        real[f'min {key}'] = prior_ewm(by_season, col, half_min)
        real[f'xmin {key}'] = prior_ewm(by, col, half_min)
    singles = sorted({p for s in STATS for p in PARTS.get(s, [s])})
    last_season = real.groupby(['player_id_ESPN', 'season_id'])[['MIN'] + singles].sum().reset_index()
    last_season = last_season.assign(season_id=last_season['season_id'] + 1)
    last_season = real[['player_id_ESPN', 'season_id']].merge(last_season, how='left')
    minutes_so_far, weight = before('MIN'), prior_games * prior_minutes
    ewm_minutes = prior_ewm(by, 'MIN', half_rate)
    for s in singles:
        prior = (last_season[s] / last_season['MIN']).fillna(prior_ewm(by, s, half_rate) / ewm_minutes)
        rate = (before(s) + weight * prior) / (minutes_so_far + weight)
        real[f'rate {s}'] = rate.where(prior.notna(), before(s) / minutes_so_far.replace(0, np.nan))
    for s in STATS:
        real[f'mean {s}'] = np.concatenate([_season_mean(g, s, top_up) for _, g in by])
    return real.drop(columns=['_min st', '_min bn'])


def core(features: pd.DataFrame, starter: pd.Series, min_season: int = MIN_SEASON_GAMES) -> Dict[str, pd.Series]:
    """Per stat: minutes × rate. Minutes: the season's EWMA in tonight's role (starter: bool per row), else in all
    the season's games, once the player has min_season games in it; before that the same over every earlier
    game."""
    own = features['n season'] >= min_season
    season = features['min st'].where(starter, features['min bn']).fillna(features['min all'])
    across = features['xmin st'].where(starter, features['xmin bn']).fillna(features['xmin all'])
    minutes = season.where(own).fillna(across)
    out = {s: minutes * features[f'rate {s}'] for s in STATS if s not in PARTS}
    out |= {s: sum(out[p] for p in parts) for s, parts in PARTS.items()}
    return out


# --- the sources ---

def logs_source(features: pd.DataFrame, min_history: int = MIN_HISTORY) -> pd.DataFrame:
    """Source A in long form: night, stat, actual and one column per candidate."""
    rows = features[features['history'] >= min_history]
    roleless = pd.Series(False, index=rows.index)
    frames = []
    for s in STATS:
        frames.append(pd.DataFrame({
            'night': rows['Date'], 'stat': s, 'actual': rows[s],
            'season mean': rows[f'mean {s}'],
            'minutes (all games) × rate': core(rows.assign(**{c: np.nan for c in ('min st', 'min bn', 'xmin st', 'xmin bn')}), roleless)[s],
            'core: minutes in role × rate': core(rows, rows['starter'])[s]}))
    return pd.concat(frames, ignore_index=True)


def rotowire_roles(lines: pd.DataFrame, rotowire: pd.DataFrame) -> pd.Series:
    """Per line: listed as a starter in RotoWire's last version of that night saved before the line's fetch."""
    from nightly import lineups_before_tip
    starter = pd.Series(False, index=lines.index)
    for (fetched_at, night), rows in lines.groupby(['fetched_at', 'night']):
        version = lineups_before_tip(rotowire, night, pd.Timestamp(fetched_at) + pd.Timedelta(seconds=1))
        ids = set(version.loc[version['role'] == 'starter', 'player_id_ESPN'].dropna())
        starter.loc[rows.index] = rows['player_id'].isin(ids)
    return starter


def superbet_source(last: pd.DataFrame, components: pd.DataFrame, features: pd.DataFrame,
                    starter: pd.Series) -> pd.DataFrame:
    """Source B in long form. last: last_pretip_lines with player_id and night; components: superbet_components,
    row for row; features: game_features; starter: per line (rotowire_roles)."""
    if len(last) != len(components) or not (last['bet_type'].values == components['bet_type'].values).all():
        raise ValueError("the saved components don't line up with the saved lines: "
                         "run python -m backtest.projection_eval --refresh")
    t = pd.concat([last[['player_id', 'night', 'line']].reset_index(drop=True),
                   components[['bet_type', 'avg', 'adj avg', 'pace factor', 'matchup factor', 'proj avg']]
                   .reset_index(drop=True)], axis=1).assign(starter=starter.values)
    t = t[t['bet_type'].isin(STATS) & t['player_id'].notna() & t['proj avg'].notna()]
    t = t.assign(player_id=pd.to_numeric(t['player_id']), night=pd.to_datetime(t['night']))
    games = features.assign(player_id=pd.to_numeric(features['player_id_ESPN']), night=features['Date']) \
        .drop_duplicates(['player_id', 'night'])
    joined = t.merge(games, on=['player_id', 'night'], how='inner', suffixes=('', ' log'))
    frames = []
    for s in STATS:
        r = joined[joined['bet_type'] == s]
        if r.empty:
            continue
        c = core(r, r['starter'])[s]
        oracle = core(r, r['starter log'])[s]
        lineup = r['adj avg'] - r['avg']
        frames.append(pd.DataFrame({
            'night': r['night'], 'stat': s, 'actual': r[s], 'line': r['line'],
            'current proj avg': r['proj avg'],
            'current without matchup': r['adj avg'] * r['pace factor'],
            'core': c,
            'core + lineup adj': c + lineup,
            'core × pace': c * r['pace factor'],
            'core + lineup adj, × pace': (c + lineup) * r['pace factor'],
            'core (actual starter flag: oracle)': oracle}))
    return pd.concat(frames, ignore_index=True)


# --- scoring ---

def score(t: pd.DataFrame, candidates, reference: str, with_line: bool) -> pd.DataFrame:
    """Per stat (and every stat together) and candidate: lines, MAE, bias, vs reference (MAE difference) with its
    night-resampled 95% range; with_line adds closer than line %, within 10% % and the disagreement correlation."""
    from insights import _near
    rows = []
    for stat in STATS + ['all']:
        part = t if stat == 'all' else t[t['stat'] == stat]
        part = part.dropna(subset=list(candidates) + ['actual'])
        if part.empty:
            continue
        ref_err = (part['actual'] - part[reference]).abs()
        for name in candidates:
            err = (part['actual'] - part[name]).abs()
            low, high = night_bootstrap(part['night'].values, (err - ref_err).values) if name != reference \
                else (np.nan, np.nan)
            row = {'stat': stat, 'candidate': name, 'lines': len(part), 'MAE': err.mean(),
                   'bias': (part['actual'] - part[name]).mean(), 'vs': (err - ref_err).mean(), 'low': low,
                   'high': high}
            if with_line:
                line_err = (part['actual'] - part['line']).abs()
                guess = np.floor(part[name]) + 0.5
                row |= {'closer %': 100 * (err < line_err).mean(),
                        'within 10% %': 100 * _near(guess, part['actual']).mean(),
                        'corr': np.corrcoef(part[name] - part['line'], part['actual'] - part['line'])[0, 1]
                        if stat != 'all' else np.nan}
            rows.append(row)
        if with_line:
            line_err = (part['actual'] - part['line']).abs()
            rows.append({'stat': stat, 'candidate': "Superbet's line", 'lines': len(part), 'MAE': line_err.mean(),
                         'bias': (part['actual'] - part['line']).mean(),
                         'within 10% %': 100 * _near(part['line'], part['actual']).mean()})
    return pd.DataFrame(rows)


def load(refresh: bool = False):
    from espn_scraper import CURRENT_SEASON, SEASONS
    from espn_scraper.storage import load_player_gamelogs, read_snapshot, snapshot_file
    from models import prepare_logs
    from name_resolver import NameResolver
    from nightly import et_night
    from backtest.ablation import superbet_components

    logs = prepare_logs(load_player_gamelogs(sorted(SEASONS)))
    features = game_features(logs)
    components = superbet_components(refresh=refresh)
    snaps = read_snapshot(snapshot_file(CURRENT_SEASON, 'superbet_props'))
    resolver = NameResolver(logs)
    last = last_pretip_lines(snaps)
    last = resolver.add_ids(last.drop(columns=['player_id_ESPN'], errors='ignore'), team_cols=('home', 'away')) \
        .rename(columns={'player_id_ESPN': 'player_id'})
    last['night'] = et_night(last['start_time'])
    rotowire = resolver.add_ids(pd.read_csv(snapshot_file(CURRENT_SEASON, 'rotowire_lineups')))
    starter = rotowire_roles(last, rotowire)
    return logs_source(features), superbet_source(last, components, features, starter)


def report(a: pd.DataFrame, b: pd.DataFrame) -> str:
    a_cands = ['season mean', 'minutes (all games) × rate', 'core: minutes in role × rate']
    b_cands = ['current proj avg', 'current without matchup', 'core', 'core + lineup adj', 'core × pace',
               'core + lineup adj, × pace', 'core (actual starter flag: oracle)']
    sa, sb = score(a, a_cands, 'season mean', False), score(b, b_cands, 'current proj avg', True)
    return "\n".join([
        "# Projection accuracy: candidate proj avg against the results (exploratory)", "",
        f"Minutes: EWMA half-life {HALF_MIN} games in tonight's role, this season's games from the player's "
        f"{MIN_SEASON_GAMES}rd of it; rate: this season's, with last season's worth {PRIOR_GAMES} games. "
        "*vs* = the candidate's MAE minus the reference's (below 0 = closer to the results), with the 95% range "
        "from resampling whole nights. Several candidates are tried on the same games, so treat a small gain as "
        "noise.", "",
        f"## A. Stored seasons' logs ({a['night'].min():%Y-%m-%d} – {a['night'].max():%Y-%m-%d}, "
        f"{a['night'].nunique()} nights); reference: season mean", "",
        markdown(sa, '{:.3f}'), "",
        f"## B. Superbet lines ({b['night'].min():%Y-%m-%d} – {b['night'].max():%Y-%m-%d}, {b['night'].nunique()} "
        "nights); reference: the current proj avg", "",
        "*closer %* = closer to the result than the line; *within 10%*: as the Overview's Spot on counts it; "
        "*corr* = correlation of (projection − line) with (result − line).", "",
        markdown(sb, '{:.3f}'), ""])


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--refresh', action='store_true', help='price the Superbet lines again first')
    parser.add_argument('--out', default=REPORT)
    args = parser.parse_args()
    a, b = load(args.refresh)
    text = report(a, b)
    atomic_write_text(args.out, text)
    print(text)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    main()
