"""Pure pandas calculations behind the dashboard (no Streamlit), so they can be tested and reused."""
import math
from typing import Dict, Optional

import numpy as np
import pandas as pd

STATS = ['PTS', 'REB', 'AST', '3PM', 'PA', 'PR', 'RA', 'ARP', 'MIN', 'STL', 'BLK', 'TO', 'FGM', 'FGA', '3PA', 'FTM', 'FTA',
         'PF']
# rule columns of assessed_bets.csv; each holds the rule's vote ('Over'/'Under') or NaN when it didn't vote
RULES = ['quantiles', 'median', 'last_games', 'averages', 'bets_hits', 'low_odds']
POSITION_GROUPS = {'G': 'G', 'PG': 'G', 'SG': 'G', 'F': 'F', 'SF': 'F', 'PF': 'F', 'C': 'C'}


def add_combined_stats(logs: pd.DataFrame) -> pd.DataFrame:
    """The combined bet types bookmakers offer: points+assists, points+rebounds, rebounds+assists,
    points+rebounds+assists."""
    return logs.assign(PA=logs['PTS'] + logs['AST'], PR=logs['PTS'] + logs['REB'], RA=logs['REB'] + logs['AST'],
                       ARP=logs['PTS'] + logs['REB'] + logs['AST'])


def hit_rates(values: pd.Series, line: float) -> Dict[str, float]:
    """Share of games over and under the line. Games exactly on a whole-number line are pushes and count for neither."""
    n = len(values)
    if n == 0:
        return {'over': np.nan, 'under': np.nan, 'games': 0}
    return {'over': (values > line).sum() / n, 'under': (values < line).sum() / n, 'games': n}


def line_percentile(values: pd.Series, line: float) -> float:
    """Where the line sits in the player's results, 0-100 (50 = at the median). Ties count half."""
    if len(values) == 0:
        return np.nan
    return 100 * ((values < line).mean() + 0.5 * (values == line).mean())


def percentile_band(values: pd.Series, lower: float = 0.30, upper: float = 0.70):
    """The band betfinder.check_bet tests the line against."""
    return values.quantile(lower), values.quantile(upper)


def trend(values: pd.Series, games: int = 5) -> float:
    """Average game-to-game change over the last `games` games (same idea as bet_analyst's trend_rule)."""
    last = values.tail(games)
    return last.diff().mean() if len(last) > 1 else np.nan


def player_summary(games: pd.DataFrame, stat: str, line: Optional[float] = None) -> Dict:
    """Key numbers for one player and stat. `games` must be sorted by date, oldest first."""
    values = games[stat]
    summary = {'games': len(values), 'avg': values.mean(), 'median': values.median(),
               'avg_last5': values.tail(5).mean(), 'avg_last10': values.tail(10).mean(),
               'trend5': trend(values), 'min_avg_last5': games['MIN'].tail(5).mean(),
               'min_avg': games['MIN'].mean()}
    summary['p30'], summary['p70'] = percentile_band(values) if len(values) else (np.nan, np.nan)
    if line is not None:
        season, last10, last5 = hit_rates(values, line), hit_rates(values.tail(10), line), hit_rates(values.tail(5), line)
        summary.update(over=season['over'], under=season['under'], over_last10=last10['over'],
                       under_last10=last10['under'], over_last5=last5['over'], under_last5=last5['under'],
                       percentile=line_percentile(values, line),
                       in_band=summary['p30'] <= line <= summary['p70'])
    return summary


def no_vig(over_odds: float, under_odds: float):
    """Chances of Over and Under implied by the odds with the bookmaker's margin removed, so they add up to 1.
    With one side missing, the other is plain 1 / odds."""
    over = 1 / over_odds if pd.notna(over_odds) else np.nan
    under = 1 / under_odds if pd.notna(under_odds) else np.nan
    if np.isnan(over) or np.isnan(under):
        return over, under
    return over / (over + under), under / (over + under)


def count_over(mean: float, var: float, line: float) -> float:
    """P(X > line) for a count X with this mean and variance: negative binomial when var > mean, else Poisson
    (results that vary less than their average still get a Poisson's spread). X > line means X ≥ floor(line) + 1."""
    mean = max(float(mean), 1e-6)
    k_max = math.floor(line)
    if k_max < 0:
        return 1.0
    if var > mean * 1.0001:
        r, q = mean ** 2 / (var - mean), 1 - mean / var
        pmf = math.exp(r * math.log(1 - q))
        step = lambda k: (k + r) / (k + 1) * q
    else:
        pmf = math.exp(-mean)
        step = lambda k: mean / (k + 1)
    cdf = pmf
    for k in range(k_max):
        pmf *= step(k)
        cdf += pmf
    return min(max(1 - cdf, 0.0), 1.0)


def prop_probability(values: pd.Series, line: float, side: str, market: float, mean: Optional[float] = None,
                     prior_games: float = 10) -> Dict[str, float]:
    """Chance that `side` ('Over' / 'Under') wins, with a 95% range.

    - hit: the side's hit rate, pulled toward the margin-free market chance `market` as if the market were worth
      `prior_games` games, so 4 of 5 doesn't read as 80%
    - dist: the chance of a result beyond the line if the result is a count (count_over: negative binomial, or
      Poisson when the player's results vary less than their average) around `mean` (default: the player's
      average; pass adj avg / proj avg to include tonight's adjustments) with the player's own variance, scaled
      with the mean; pulled toward the market the same way (a 5-game spread is no more reliable than a hit rate).
      A count fits whole-number stats better than a normal curve, most of all for small ones like 3PM
      (backtest/ideas.py)
    p is the average of the two (only hit with fewer than 3 games). The range is p ± 1.96 standard errors of a
    hit rate worth n + prior_games games: the sampling noise of the player's record, wide with few games so a hot
    start doesn't look certain. It is not a prediction interval and leaves out the projection's and the
    model's own errors."""
    market = 0.5 if pd.isna(market) else market
    n = len(values)
    weight = n / (n + prior_games)
    hits = int((values > line).sum() if side == 'Over' else (values < line).sum())
    shrunk = (hits + prior_games * market) / (n + prior_games)
    dist = np.nan
    if n >= 3:
        average = values.mean()
        centre = average if mean is None or pd.isna(mean) else mean
        # the player's variance, scaled with the projection: a count's spread grows with its mean
        var = (values.var() if pd.notna(values.var()) else 0.0) * (centre / average if average > 0 else 1.0)
        # a whole-number line pushes on the line itself: Over needs line + 1, Under line - 1
        whole = float(line).is_integer()
        cut = line + 0.5 if whole and side == 'Over' else line - 0.5 if whole else line
        over = count_over(centre, var, cut)
        dist = weight * (over if side == 'Over' else 1 - over) + (1 - weight) * market
    p = shrunk if np.isnan(dist) else (shrunk + dist) / 2
    half = 1.96 * math.sqrt(p * (1 - p) / (n + prior_games + 1))
    return {'p': p, 'low': max(p - half, 0.0), 'high': min(p + half, 1.0), 'hit': shrunk, 'dist': dist}


# --- calibration: the model's chance mapped to how often such picks actually won (backtest/calibrate.py) ---

# a = weight of the market's chance, b = weight of the model's opinion beyond it, c = Over/Under bias, d = offset
IDENTITY_CALIBRATION = {'a': 1.0, 'b': 1.0, 'c': 0.0, 'd': 0.0}


def logit(p: float) -> float:
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


def calibrate(p: float, market: float, side: str, coef: Optional[Dict] = None) -> float:
    """The chance that `side` wins, corrected for how the model's chances have turned out:
    sigmoid(a·logit(market) + b·(logit(p) − logit(market)) + c·[Over] + d). market: the side's margin-free chance
    (0.5 when unknown). The identity coefficients return p itself (up to clipping at 0.01%)."""
    if pd.isna(p):
        return p
    coef = coef or IDENTITY_CALIBRATION
    m = 0.5 if pd.isna(market) else market
    z = coef['a'] * logit(m) + coef['b'] * (logit(p) - logit(m)) + coef['c'] * (side == 'Over') + coef['d']
    return 1 / (1 + math.exp(-z))


def prop_signal(edge_pp, green_edge: Optional[float] = None):
    """🟢 for an edge (calibrated, pp) of at least green_edge, the threshold that held up on unseen lines
    (backtest/calibrate.py; None = none did, so no 🟢); 🟡 for any other positive edge; '' otherwise.
    edge_pp: a number or a Series (returns the same)."""
    edge = pd.Series(edge_pp, dtype=float) if not isinstance(edge_pp, pd.Series) else edge_pp.astype(float)
    green = edge >= green_edge if green_edge is not None else pd.Series(False, index=edge.index)
    out = pd.Series(np.select([green, edge > 0], ['🟢', '🟡'], ''), index=edge.index)
    return out if isinstance(edge_pp, pd.Series) else out.iloc[0]


def splits(games: pd.DataFrame, stat: str, line: Optional[float] = None) -> pd.DataFrame:
    """Average (and hit rate over the line) by home/away, starter/bench, rest and minutes."""
    g = games.assign(
        location=games['type'].str.capitalize(),
        role=np.where(games['starter'], 'Starter', 'Bench'),
        rest=np.select([games['rest_days'] == 1, games['rest_days'] >= 2], ['Back-to-back', '1+ days rest'], 'First game'),
        minutes=pd.cut(games['MIN'], [-1, 19, 29, 35, 60], labels=['<20 min', '20-29 min', '30-35 min', '36+ min']),
    )
    rows = []
    for split in ['location', 'role', 'rest', 'minutes']:
        for value, part in g.groupby(split, observed=True):
            row = {'split': split, 'value': value, 'games': len(part), 'avg': part[stat].mean(), 'median': part[stat].median()}
            if line is not None:
                row['over %'] = 100 * hit_rates(part[stat], line)['over']
            rows.append(row)
    return pd.DataFrame(rows)


def teammates(logs: pd.DataFrame, player_id) -> pd.DataFrame:
    """Players who appeared in the same game for the same team, with the number of shared games."""
    own = logs.loc[logs['player_id_ESPN'] == player_id, ['game_id', 'team']]
    shared = logs.merge(own, on=['game_id', 'team'])
    shared = shared[shared['player_id_ESPN'] != player_id]
    return (shared.groupby(['player_id_ESPN', 'player_display_name']).size().rename('shared_games')
            .reset_index().sort_values('shared_games', ascending=False))


def stint_games(logs: pd.DataFrame, player_id, teammate_id) -> pd.DataFrame:
    """The player's games from the teammate's first to last game on the same team (per season), flagged
    `teammate_played`. Games before the teammate joined or after they left don't count as 'out'."""
    player = logs[logs['player_id_ESPN'] == player_id]
    mate = logs[(logs['player_id_ESPN'] == teammate_id) & (logs['MIN'] > 0)]
    together = mate.merge(player[['game_id', 'team']], on=['game_id', 'team'])
    if together.empty:
        return player.iloc[0:0].assign(teammate_played=pd.Series(dtype=bool))
    windows = mate.groupby(['season_id', 'team'])['Date'].agg(['min', 'max']).reset_index()
    windows = windows.merge(together[['season_id', 'team']].drop_duplicates())
    games = player.merge(windows, on=['season_id', 'team'])
    games = games[(games['Date'] >= games['min']) & (games['Date'] <= games['max'])].drop(columns=['min', 'max'])
    return games.assign(teammate_played=games['game_id'].isin(mate['game_id']))


def with_without(logs: pd.DataFrame, player_id, teammate_id, stat: str) -> pd.DataFrame:
    """The player's numbers in games the teammate played vs missed (within the teammate's stint)."""
    games = stint_games(logs, player_id, teammate_id)
    if games.empty:
        return pd.DataFrame()
    return (games.groupby('teammate_played')
            .agg(games=(stat, 'size'), avg=(stat, 'mean'), median=(stat, 'median'), minutes=('MIN', 'mean'),
                 shots=('FGA', 'mean'))
            .rename(index={True: 'Teammate played', False: 'Teammate out'}))


def team_rotation(logs: pd.DataFrame, team: str, min_games: int = 5, min_minutes: float = 10) -> pd.DataFrame:
    """Players who play regularly for the team and are still on it (their latest game was for this team).
    Index: player id. Sorted by minutes per game."""
    latest = logs.sort_values('Date').groupby('player_id_ESPN').tail(1).set_index('player_id_ESPN')['team']
    current = latest[latest == team].index
    games = logs[(logs['team'] == team) & logs['player_id_ESPN'].isin(current)]
    rotation = games.groupby('player_id_ESPN').agg(
        name=('player_display_name', 'last'), position=('position', 'last'), games=('game_id', 'size'),
        mpg=('MIN', 'mean'), starts=('starter', 'sum'), last_game=('Date', 'max'))
    rotation = rotation[(rotation['games'] >= min_games) & (rotation['mpg'] >= min_minutes)]
    return rotation.sort_values('mpg', ascending=False)


def starting_lineup(logs: pd.DataFrame, team: str, how: str = 'last', last_n: int = 10) -> list:
    """Starters of the team's last game ('last'), or the 5 most frequent starters of its last `last_n` games."""
    games = logs[logs['team'] == team]
    if games.empty:
        return []
    if how == 'last':
        last_game = games.loc[games['Date'] == games['Date'].max(), 'game_id'].iloc[-1]
        return games[(games['game_id'] == last_game) & games['starter']]['player_id_ESPN'].tolist()
    recent = games.drop_duplicates('game_id').sort_values('Date')['game_id'].tail(last_n)
    starts = games[games['game_id'].isin(recent) & games['starter']]
    return starts['player_id_ESPN'].value_counts().head(5).index.tolist()


def with_without_matrix(logs: pd.DataFrame, row_ids, col_ids, stat: str) -> Dict[str, pd.DataFrame]:
    """For every (row player, column teammate) pair: the row player's average with and without the teammate.
    Returns DataFrames 'with', 'without', 'n_with', 'n_without' and 'delta' (= without - with)."""
    out = {k: pd.DataFrame(np.nan, index=list(row_ids), columns=list(col_ids))
           for k in ['with', 'without', 'n_with', 'n_without', 'delta']}
    for r in row_ids:
        for c in col_ids:
            if r == c:
                continue
            games = stint_games(logs, r, c)
            played, missed = games.loc[games['teammate_played'], stat], games.loc[~games['teammate_played'], stat]
            out['with'].loc[r, c], out['without'].loc[r, c] = played.mean(), missed.mean()
            out['n_with'].loc[r, c], out['n_without'].loc[r, c] = len(played), len(missed)
    out['delta'] = out['without'] - out['with']
    return out


def lineup_scenario(logs: pd.DataFrame, team: str, starters, out, available, stat: str,
                    shrink: float = 5, matrix: Optional[Dict[str, pd.DataFrame]] = None) -> pd.DataFrame:
    """Tonight's estimate for each starter and available bench player, given who is out.

    - usual: the player's average for this team
    - exact: average in team games where every starter played and every out player missed
    - estimate: usual + sum over out players of their with/without change, shrunk toward 0 by
      n_without / (n_without + shrink), so a couple of games without someone can't swing it much
    """
    starters, out, available = list(starters), list(out), list(available)
    players = starters + [p for p in available if p not in starters and p not in out]
    if matrix is None:
        matrix = with_without_matrix(logs, players, out, stat) if out else None
    team_logs = logs[logs['team'] == team]
    played_by_game = team_logs[team_logs['MIN'] > 0].groupby('game_id')['player_id_ESPN'].agg(set)
    # each out player only counts as 'missed' inside their stint on the team
    stints = team_logs[team_logs['player_id_ESPN'].isin(out) & (team_logs['MIN'] > 0)] \
        .groupby(['player_id_ESPN', 'season_id'])['Date'].agg(['min', 'max'])
    game_info = team_logs.drop_duplicates('game_id').set_index('game_id')[['Date', 'season_id']]

    def matches(game_id) -> bool:
        present = played_by_game.get(game_id, set())
        if not set(starters) <= present:
            return False
        date, season = game_info.loc[game_id, 'Date'], game_info.loc[game_id, 'season_id']
        for o in out:
            if o in present:
                return False
            if (o, season) not in stints.index or not stints.loc[(o, season), 'min'] <= date <= stints.loc[(o, season), 'max']:
                return False
        return True

    exact_games = {g for g in game_info.index if matches(g)}
    rows = []
    for p in players:
        games = team_logs[team_logs['player_id_ESPN'] == p]
        exact = games[games['game_id'].isin(exact_games)]
        change, evidence = 0.0, []
        for o in out:
            n = matrix['n_without'].loc[p, o]
            d = matrix['delta'].loc[p, o]
            if n and not np.isnan(d):
                change += d * n / (n + shrink)
                evidence.append(n)
        usual = games[stat].mean()
        support = min(evidence) if evidence else (len(games) if not out else 0)
        rows.append({'player_id_ESPN': p, 'name': games['player_display_name'].iloc[-1] if len(games) else str(p),
                     'role': 'Starter' if p in starters else 'Bench', 'games': len(games), 'usual': usual,
                     'exact match': exact[stat].mean() if len(exact) else np.nan, 'exact games': len(exact),
                     'estimate': usual + change, 'change': change, 'usual MIN': games['MIN'].mean(),
                     'exact MIN': exact['MIN'].mean() if len(exact) else np.nan,
                     'confidence': 'high' if support >= 10 else 'medium' if support >= 4 else 'low'})
    return pd.DataFrame(rows)


def absence_adjustments(logs: pd.DataFrame, player_ids, out_ids, stats, shrink: float = 5) -> pd.DataFrame:
    """For each player: the summed with/without change of each stat over the out teammates, each shrunk by
    n_without / (n_without + shrink) as in lineup_scenario. Index: player id, columns: stats."""
    out = pd.DataFrame(0.0, index=list(player_ids), columns=list(stats))
    for p in player_ids:
        for o in out_ids:
            if p == o:
                continue
            games = stint_games(logs, p, o)
            played, missed = games[games['teammate_played']], games[~games['teammate_played']]
            n = len(missed)
            if n and len(played):
                out.loc[p] += (missed[list(stats)].mean() - played[list(stats)].mean()) * n / (n + shrink)
    return out


def wilson_interval(hits: int, n: int, z: float = 1.96):
    """95% confidence interval of a hit rate; wide for small samples."""
    if n == 0:
        return np.nan, np.nan
    p = hits / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


# --- settling: the one place that turns a result into win / loss / push and a profit ---

def side_result(margin: pd.Series, decided: Optional[pd.Series] = None) -> pd.Series:
    """'win' / 'loss' / 'push' from how far a bet cleared its line in its own direction (actual − line for an Over,
    line − actual for an Under, the handicapped margin for a spread...); NaN where the margin is unknown or
    `decided` is False. A push needs an exact tie, which only whole-number lines allow."""
    out = pd.Series(np.select([margin > 0, margin < 0], ['win', 'loss'], 'push'), index=margin.index, dtype=object)
    keep = margin.notna() if decided is None else margin.notna() & decided
    return out.where(keep)


def side_profit(result: pd.Series, odds) -> pd.Series:
    """Profit per unit staked: odds − 1 for a win, −1 for a loss, 0 for a push or void (the stake comes back);
    NaN where there's no result."""
    profit = pd.Series(np.select([result == 'win', result == 'loss'], [np.asarray(odds) - 1, -1.0], 0.0),
                       index=result.index)
    return profit.where(result.notna())


def score_check(games: pd.DataFrame, logs: pd.DataFrame) -> pd.DataFrame:
    """NBA games whose players' points don't add up to the team's score (a player's line is missing: ESPN listed
    them without id or name and the play-by-play didn't have them either). Columns: the game's (date, teams,
    scores...) plus 'home pts (players)' and 'away pts (players)'; indexed by game_id. Empty when the logs lack
    game_id / type."""
    if len(logs) == 0 or not {'game_id', 'type', 'PTS'} <= set(logs.columns) or 'game_id' not in games:
        return pd.DataFrame()
    points = logs.groupby(['game_id', 'type'])['PTS'].sum().unstack().add_suffix(' pts (players)')
    for side in ('home', 'away'):
        if f'{side} pts (players)' not in points:
            points[f'{side} pts (players)'] = np.nan
    # the player logs hold NBA teams only, so All-Star games and exhibitions against foreign clubs are skipped
    from espn_scraper import NBA_TEAM_ABBRS
    nba = games[games['home'].isin(NBA_TEAM_ABBRS) & games['away'].isin(NBA_TEAM_ABBRS)].set_index('game_id')
    columns = [c for c in ['date', 'season_id', 'season_type', 'home', 'away', 'home_score', 'away_score'] if c in nba]
    check = nba[columns].join(points)
    return check[(check['home pts (players)'] != check['home_score'])
                 | (check['away pts (players)'] != check['away_score'])]


def roi(is_hit: pd.Series, odds: pd.Series) -> float:
    """Return per unit staked, betting 1 unit on every bet: +0.05 means +5%."""
    if len(is_hit) == 0:
        return np.nan
    return float((np.where(is_hit, odds, 0.0) - 1).mean())


def _rate_row(part: pd.DataFrame) -> Dict:
    hits, n = int(part['is_hit'].sum()), len(part)
    low, high = wilson_interval(hits, n)
    # the model's own expectation next to the hit rate: an accurate signal wins about as often as it said
    expected = {'expected %': part['model_pct'].mean()} if 'model_pct' in part else {}
    return {'bets': n, **expected, 'hit %': 100 * hits / n if n else np.nan, 'ci low %': 100 * low,
            'ci high %': 100 * high, 'ROI %': 100 * roi(part['is_hit'], part['odds']), 'avg odds': part['odds'].mean()}


def rule_stats(bets: pd.DataFrame) -> pd.DataFrame:
    """For each rule: bets where it voted with the bet's direction vs against it."""
    rows = []
    for rule in RULES:
        for relation, mask in (('agrees', bets[rule] == bets['over_under']),
                               ('disagrees', bets[rule].notna() & (bets[rule] != bets['over_under']))):
            if mask.any():
                rows.append({'rule': rule, 'vote': relation, **_rate_row(bets[mask])})
    return pd.DataFrame(rows)


def vote_pattern(bets: pd.DataFrame) -> pd.DataFrame:
    """Per bet: how many rules agree/disagree with its direction, and the pattern as text ('+' agree, '-' against)."""
    agree = pd.DataFrame({r: bets[r] == bets['over_under'] for r in RULES})
    against = pd.DataFrame({r: bets[r].notna() & (bets[r] != bets['over_under']) for r in RULES})
    pattern = pd.Series('', index=bets.index)
    for r in RULES:
        pattern = pattern + np.where(agree[r], f'+{r} ', np.where(against[r], f'-{r} ', ''))
    return bets.assign(agree=agree.sum(axis=1), against=against.sum(axis=1),
                       net=agree.sum(axis=1) - against.sum(axis=1),
                       pattern=pattern.str.strip().replace('', '(no votes)'))


def grouped_rates(bets: pd.DataFrame, by, min_bets: int = 1) -> pd.DataFrame:
    rows = [{**dict(zip([by] if isinstance(by, str) else by, key if isinstance(key, tuple) else (key,))), **_rate_row(part)}
            for key, part in bets.groupby(by, observed=True)]
    df = pd.DataFrame(rows)
    return df[df['bets'] >= min_bets] if not df.empty else df


def team_ratings(games: pd.DataFrame) -> pd.DataFrame:
    """Per team: record, points for/against, a pace proxy and points per 100 possessions."""
    sides = []
    for side, other in (('home', 'away'), ('away', 'home')):
        s = pd.DataFrame({
            'team': games[side], 'pts': games[f'{side}_score'], 'opp_pts': games[f'{other}_score'],
            'poss': games[f'{side}_FGA'] + 0.44 * games[f'{side}_FTA'] + games[f'{side}_TO'] - games[f'{side}_OREB'],
            'opp_poss': games[f'{other}_FGA'] + 0.44 * games[f'{other}_FTA'] + games[f'{other}_TO'] - games[f'{other}_OREB'],
            'location': side})
        sides.append(s)
    t = pd.concat(sides)
    t['win'] = t['pts'] > t['opp_pts']
    t['pace'] = (t['poss'] + t['opp_poss']) / 2
    out = t.groupby('team').agg(games=('win', 'size'), wins=('win', 'sum'), pts=('pts', 'mean'),
                                opp_pts=('opp_pts', 'mean'), pace=('pace', 'mean'),
                                poss=('poss', 'sum'), opp_poss=('opp_poss', 'sum'),
                                pts_total=('pts', 'sum'), opp_total=('opp_pts', 'sum'))
    out['losses'] = out['games'] - out['wins']
    out['off_rtg'] = 100 * out['pts_total'] / out['poss']
    out['def_rtg'] = 100 * out['opp_total'] / out['opp_poss']
    out['net_rtg'] = out['off_rtg'] - out['def_rtg']
    home = t[t['location'] == 'home'].groupby('team')['win'].agg(['sum', 'size'])
    out['home'] = home['sum'].astype(int).astype(str) + '-' + (home['size'] - home['sum']).astype(int).astype(str)
    return (out[['games', 'wins', 'losses', 'home', 'pts', 'opp_pts', 'pace', 'off_rtg', 'def_rtg', 'net_rtg']]
            .sort_values('net_rtg', ascending=False))


def allowed_by_position(logs: pd.DataFrame, stat: str) -> pd.DataFrame:
    """Per defending team: the stat its opponents' guards / forwards / centers produce per game, combined."""
    df = logs.assign(defense=logs['OPP'].str.lower(), group=logs['position'].map(POSITION_GROUPS))
    per_game = df.groupby(['defense', 'game_id', 'group'])[stat].sum().unstack('group', fill_value=0)
    table = per_game.groupby('defense').mean()
    table['games'] = per_game.groupby('defense').size()
    return table.reindex(columns=['G', 'F', 'C', 'games'])


def matchup_verdict(diff: float, average: float):
    """(matchup word, colour): soft / tough when the defense allows at least 5% more / less than the league
    average."""
    if diff >= 0.05 * average:
        return 'soft', 'green'
    if diff <= -0.05 * average:
        return 'tough', 'red'
    return 'average', 'gray'


def matchup(allowed: pd.DataFrame, defense: str, group: str) -> Dict:
    """What `defense` allows to a position group vs the league average, from an allowed_by_position table:
    value, average, diff, ratio, rank (1 = allows the most), word and colour. Empty when unknown."""
    if defense not in allowed.index or group not in ('G', 'F', 'C') or pd.isna(allowed.loc[defense, group]):
        return {}
    value, average = allowed.loc[defense, group], allowed[group].mean()
    word, colour = matchup_verdict(value - average, average)
    rank = int(allowed[group].rank(ascending=False, method='min')[defense])
    return {'value': value, 'average': average, 'diff': value - average, 'ratio': value / average if average else 1.0,
            'rank': rank, 'teams': int(allowed[group].notna().sum()), 'word': word, 'colour': colour}


# a game's expected points and its opponent's defense move a player's numbers, but much less than one to one
# (minutes and role don't change), so each factor is damped and capped; the tracker shows whether it helps
CONTEXT_DAMPING, CONTEXT_CAP = 0.5, 0.08


def context_factor(ratio: float) -> float:
    """1 + half of (ratio - 1), capped at ±8%."""
    if pd.isna(ratio):
        return 1.0
    return 1 + float(np.clip(CONTEXT_DAMPING * (ratio - 1), -CONTEXT_CAP, CONTEXT_CAP))


def game_lines(main: pd.DataFrame) -> pd.DataFrame:
    """Per event: the home team's handicap and the total of Superbet's main lines (main_lines output), and both
    implied team totals. A home handicap of −6.5 = home favoured by 6.5."""
    rows = {}
    for event_id, g in main.groupby('event_id'):
        spread = g[(g['market'] == 'SPREAD') & (g['side'] == 'home')]['line']
        total = g[g['market'] == 'TOTAL']['line']
        rows[event_id] = {'home_spread': spread.iloc[0] if len(spread) else np.nan,
                          'total': total.iloc[0] if len(total) else np.nan}
    out = pd.DataFrame.from_dict(rows, orient='index', columns=['home_spread', 'total'])
    out['home_implied'] = out['total'] / 2 - out['home_spread'] / 2
    out['away_implied'] = out['total'] / 2 + out['home_spread'] / 2
    return out


# --- today's games: RotoWire lineups and a simple game model ---

# spread of actual results around game_projection (2025/26 regular season: margin 14.1, total 18.4)
MARGIN_SD, TOTAL_SD, TEAM_TOTAL_SD = 14.0, 18.0, 11.5


def rotowire_team(lineups: pd.DataFrame, team: str, out_max_pct: int = 25) -> Dict[str, list]:
    """A team's RotoWire lineup as ESPN ids (lineups need a player_id_ESPN column): starters, out (chance to play
    <= out_max_pct) and questionable (above that but under 100). Unmatched names are skipped."""
    t = lineups[(lineups['team'] == team) & lineups['player_id_ESPN'].notna()]
    may_not = t[t['role'] == 'may_not_play']
    return {'starters': t.loc[t['role'] == 'starter', 'player_id_ESPN'].tolist(),
            'out': may_not.loc[may_not['play_pct'] <= out_max_pct, 'player_id_ESPN'].tolist(),
            'questionable': may_not.loc[(may_not['play_pct'] > out_max_pct) & (may_not['play_pct'] < 100),
                                        'player_id_ESPN'].tolist()}


def blended_ratings(current: pd.DataFrame, prior: pd.DataFrame, prior_games: float = 10,
                    regress: float = 0.3) -> pd.DataFrame:
    """team_ratings of the current season's games pulled toward the prior season's: the current season weighs
    n / (n + prior_games), so the first weeks lean on last season. Last season's ratings are first moved
    `regress` of the way to the league average, since rosters change over the summer. A team missing on one
    side uses the other."""
    cols = ['off_rtg', 'def_rtg', 'pace']
    cur = team_ratings(current) if len(current) else pd.DataFrame(columns=cols + ['games'], dtype=float)
    old = team_ratings(prior)[cols] if len(prior) else pd.DataFrame(columns=cols, dtype=float)
    old = old * (1 - regress) + old.mean() * regress
    teams = cur.index.union(old.index)
    games = cur['games'].reindex(teams).fillna(0).astype(float)
    cur, old = cur[cols].reindex(teams).astype(float), old.reindex(teams).astype(float)
    w = games / (games + prior_games)
    blended = (cur.mul(w, axis=0) + old.mul(1 - w, axis=0)).fillna(cur).fillna(old)
    return blended.assign(games=games.astype(int))


def absence_impact(games: pd.DataFrame, logs: pd.DataFrame, team: str, player_id, shrink: float = 5) -> Dict:
    """How the team's points scored and allowed change in games the player missed (inside the player's stints
    on the team, per season), shrunk toward 0 by n / (n + shrink) where n = games missed."""
    played = logs[(logs['player_id_ESPN'] == player_id) & (logs['team'] == team) & (logs['MIN'] > 0)]
    if played.empty:
        return {'pts_for': 0.0, 'pts_against': 0.0, 'n_without': 0, 'n_with': 0}
    windows = played.groupby('season_id')['Date'].agg(['min', 'max'])
    sides = []
    for side, other in (('home', 'away'), ('away', 'home')):
        g = games[games[side] == team]
        sides.append(pd.DataFrame({'game_id': g['game_id'], 'season_id': g['season_id'], 'date': g['date'],
                                   'pts_for': g[f'{side}_score'], 'pts_against': g[f'{other}_score']}))
    t = pd.concat(sides).merge(windows, left_on='season_id', right_index=True)
    t = t[(t['date'] >= t['min']) & (t['date'] <= t['max'])]
    t['played'] = t['game_id'].isin(played['game_id'])
    with_, without = t[t['played']], t[~t['played']]
    n = len(without)
    if n == 0 or with_.empty:
        return {'pts_for': 0.0, 'pts_against': 0.0, 'n_without': n, 'n_with': len(with_)}
    weight = n / (n + shrink)
    return {'pts_for': weight * (without['pts_for'].mean() - with_['pts_for'].mean()),
            'pts_against': weight * (without['pts_against'].mean() - with_['pts_against'].mean()),
            'n_without': n, 'n_with': len(with_)}


def game_projection(ratings: pd.DataFrame, home: str, away: str, home_court: float = 1.5,
                    home_absences=(), away_absences=()) -> Dict:
    """Projected points for both teams: pace x (team's offense + opponent's defense - league average) / 100,
    plus half the home-court edge each way, plus the absence_impact dicts of each team's missing players."""
    league_rtg, league_pace = ratings['off_rtg'].mean(), ratings['pace'].mean()
    h, a = ratings.loc[home], ratings.loc[away]
    pace = h['pace'] + a['pace'] - league_pace
    home_pts = pace * (h['off_rtg'] + a['def_rtg'] - league_rtg) / 100 + home_court / 2
    away_pts = pace * (a['off_rtg'] + h['def_rtg'] - league_rtg) / 100 - home_court / 2
    for imp in home_absences:
        home_pts, away_pts = home_pts + imp['pts_for'], away_pts + imp['pts_against']
    for imp in away_absences:
        away_pts, home_pts = away_pts + imp['pts_for'], home_pts + imp['pts_against']
    return {'home_pts': home_pts, 'away_pts': away_pts, 'margin': home_pts - away_pts,
            'total': home_pts + away_pts, 'pace': pace}


def _normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def model_probability(projection: Dict, market: str, side: str, line: Optional[float]) -> float:
    """Chance the outcome wins under the projection. A SPREAD line is the side's handicap (+1.5 = may lose by 1)."""
    if market in ('ML', 'SPREAD'):
        margin = projection['margin'] if side == 'home' else -projection['margin']
        return _normal_cdf((margin + (line if market == 'SPREAD' else 0)) / MARGIN_SD)
    expected, sd = {'TOTAL': (projection['total'], TOTAL_SD), 'HOME_TOTAL': (projection['home_pts'], TEAM_TOTAL_SD),
                    'AWAY_TOTAL': (projection['away_pts'], TEAM_TOTAL_SD)}[market]
    over = _normal_cdf((expected - line) / sd)
    return over if side == 'over' else 1 - over


def market_edges(projection: Dict, odds: pd.DataFrame) -> pd.DataFrame:
    """Superbet outcomes (market, side, line, odds) with the model's chance, the chance implied by the odds,
    the edge in percentage points and the model's fair odds."""
    out = odds.copy()
    out['model %'] = [100 * model_probability(projection, m, s, l)
                      for m, s, l in zip(out['market'], out['side'], out['line'])]
    out['implied %'] = 100 / out['odds']
    out['edge pp'] = out['model %'] - out['implied %']
    out['fair odds'] = 100 / out['model %']
    return out
