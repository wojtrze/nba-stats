"""Where Superbet may have priced a line wrong: detectors of the hypotheses in docs/hipotezy_wyceny.md (no
Streamlit, so they can be tested and backtested).

A detector doesn't forecast the result better than the price; it looks for a known mechanism of a mispricing.
  H1 combos against their parts: Superbet prices points+rebounds+assists (and PR, PA, RA) as a line of its own,
     next to the lines of the parts. Each part's margin-free price says what Superbet expects of it; with how the
     player's points, rebounds and assists vary and go together, those expectations give a chance for the combo.
  H2 makes against attempts: the lines of made and attempted shots (3PM/3PA, FGM/FGA, FTM/FTA) together assume a
     shooting rate. The attempts line with the player's own rate (pulled toward the league's) gives a chance for
     the makes line.
  H6 the spread of small counts: Superbet's price of a small line (≤ 2.5 blocks, steals, threes, turnovers, fouls)
     fits a count as spread as a Poisson. A player whose results spread more ends below the line
     more often at the same average.
  H5 a role change: RotoWire has him in tonight's starting five after at most one start in his last five games (or
     on the bench after four or five starts). His price fits the minutes he has been playing; the minutes of the
     new role (his own games in it, pulled toward his recent minutes plus the league's starter-bench difference)
     scale the price's average.

Every signal is {'hypothesis', 'mechanism', 'status', 'bet_type', 'line', 'parts' [(stat, line)], 'side',
'p_ours', 'p_book', 'gap_pp', 'needed_pp', 'clears', 'odds', 'n', 'as_of', 'expires_when'} plus what its message
needs, and 'exploration' (how the signals that cleared the tax did on the exploration nights, from the status file;
None when not recorded): chances of `side` in 0-1; p_ours what the mechanism gives, p_book the line's margin-free price; gap_pp how
far p_ours puts the side above p_book; needed_pp how far above it the side's odds need after the stake tax
(metrics.break_even); clears = p_ours reaches the break-even. status is the hypothesis's verdict
(hypothesis_status), so a page can tell an untested observation from a tested one. parts are the other lines the
signal rests on: a page shows it on the line itself and on these.
"""
import json
import math
import os
from itertools import combinations
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from metrics import ACTIVE_PROFILE, break_even, count_over, no_vig

UNTESTED, ADMITTED, REJECTED = 'untested', 'admitted', 'rejected'
STATUS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'backtest',
                           'mispricing_status.json')
# the combos Superbet offers and their parts (ARP = points+rebounds+assists)
COMBOS = {'PR': ('PTS', 'REB'), 'PA': ('PTS', 'AST'), 'RA': ('REB', 'AST'), 'ARP': ('PTS', 'REB', 'AST')}
# made shots and their attempts
SHOTS = {'3PM': '3PA', 'FGM': 'FGA', 'FTM': 'FTA'}
# the small counts of H6 and the highest line that counts as small. Not free throws: they come in pairs, so every
# player's spread twice a Poisson's is the stat's, not his (docs/hipotezy_wyceny.md, H6)
SMALL_STATS = ('BLK', 'STL', '3PM', 'TO', 'PF')
SMALL_LINE = 2.5
# fewer games than this and the player's spread and correlations say too little (as reasons.MIN_GAMES)
MIN_GAMES = 8
# the spread and the correlations come from the player's last RECENT games; a shooting rate from all of them
RECENT = 40
# a player's correlation is pulled toward the league's as if the league were worth this many games
PRIOR_GAMES = 10
# a player's shooting rate is pulled toward the league's as if the league were worth this many attempts
PRIOR_ATTEMPTS = 200
# a player's spread (variance / mean) is pulled toward the league's as if the league were worth this many games
PRIOR_SPREAD_GAMES = 20
# the smallest gap a page shows per hypothesis (docs/hipotezy_wyceny.md): below it the prices agree as often as
# not, and H2's typical gap is 3 pp
SHOW_GAP_PP = {'H1': 3.0, 'H2': 6.0, 'H6': 4.0, 'H5': 4.0}
# H5: tonight's role against the starts of his last ROLE_GAMES games; the minutes he'll play in the new role are his
# own in it, pulled toward his recent minutes ± the league's starter-bench difference as if that were worth
# ROLE_PRIOR_GAMES games
ROLE_GAMES = 5
ROLE_PRIOR_GAMES = 3


def hypothesis_status(path: str = STATUS_FILE) -> Dict[str, Dict]:
    """Each hypothesis's verdict as the evaluation wrote it: {'H1': {'status', ...}}; {} before any evaluation
    (every hypothesis is then 'untested'). Set by hand after reading the report, like the admitted threshold."""
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f).get('hypotheses', {})
    except (OSError, ValueError):
        return {}


def _verdict(status: Optional[Dict[str, Dict]], hypothesis: str) -> Dict:
    """The hypothesis's status and, when recorded, how its signals that cleared the tax did on the exploration
    nights: {'status', 'exploration'}."""
    entry = (hypothesis_status() if status is None else status).get(hypothesis, {})
    return {'status': entry.get('status', UNTESTED), 'exploration': entry.get('exploration')}


def pooled_correlations(logs: pd.DataFrame, stats=('PTS', 'REB', 'AST')) -> pd.DataFrame:
    """How the stats go together within a player's games, across the league: every game's distance from its
    player's average, correlated over all players. The prior a player's own few games are pulled toward."""
    present = [s for s in stats if s in logs]
    if not len(logs) or 'player_id_ESPN' not in logs:
        return pd.DataFrame(np.eye(len(present)), index=present, columns=present)
    values = logs[present].astype(float)
    deviations = values - values.groupby(logs['player_id_ESPN']).transform('mean')
    return deviations.corr().fillna(0.0)


def league_rates(logs: pd.DataFrame) -> Dict[str, float]:
    """The league's shooting rate per made-shot stat: made / attempted over every game."""
    return {made: logs[made].sum() / logs[att].sum() for made, att in SHOTS.items()
            if made in logs and att in logs and logs[att].sum() > 0}


def stat_values(games: pd.DataFrame, stat: str) -> Optional[pd.Series]:
    """A stat per game, a combo summed from its parts; None when the games don't have it."""
    parts = COMBOS.get(stat, (stat,))
    if not set(parts) <= set(games.columns):
        return None
    return games[list(parts)].astype(float).sum(axis=1)


def league_spreads(logs: pd.DataFrame, min_games: int = 10, stats=SMALL_STATS) -> Dict[str, float]:
    """The typical spread (variance / mean) of each stat (SMALL_STATS by default): the median over players with
    min_games games."""
    spreads = {}
    for stat in stats:
        values = stat_values(logs, stat) if 'player_id_ESPN' in logs else None
        if values is None:
            continue
        per = values.groupby(logs['player_id_ESPN']).agg(['mean', 'var', 'size'])
        per = per[(per['size'] >= min_games) & (per['mean'] > 0)]
        if len(per):
            spreads[stat] = float((per['var'] / per['mean']).median())
    return spreads


def _player_correlation(games: pd.DataFrame, a: str, b: str, prior: pd.DataFrame) -> float:
    n = len(games)
    own = games[a].astype(float).corr(games[b].astype(float))
    own = 0.0 if pd.isna(own) else own
    league = prior.loc[a, b] if a in prior.index and b in prior.columns else 0.0
    return (n * own + PRIOR_GAMES * league) / (n + PRIOR_GAMES)


def market_mean(line: float, p_over: float, average: float, var: float) -> float:
    """The average a count must have (metrics.count_over, the player's variance scaled with the mean as in
    metrics.prop_probability) to go over the line as often as the margin-free price says. average = var gives
    the Poisson's mean."""
    scale = var / average if average > 0 else 1.0
    low, high = 1e-3, max(3 * line, line + 10)
    for _ in range(60):
        mid = (low + high) / 2
        if count_over(mid, scale * mid, line) < p_over:
            low = mid
        else:
            high = mid
    return (low + high) / 2


def _quoted(lines: pd.DataFrame) -> pd.DataFrame:
    """The lines with both odds on a half-point line (a whole-number line can push), one per bet type."""
    quoted = lines.dropna(subset=['line', 'over_odds', 'under_odds']).drop_duplicates('bet_type', keep='last')
    return quoted[quoted['line'] % 1 != 0].set_index('bet_type')


def _signal(hypothesis: str, mechanism: str, verdict: Dict, quoted: pd.DataFrame, stat: str, p_ours_over: float,
            parts, n: int, as_of, profile: str, **extra) -> Dict:
    """The signal for the side p_ours favours over the line's margin-free price."""
    p_book_over = no_vig(quoted.loc[stat, 'over_odds'], quoted.loc[stat, 'under_odds'])[0]
    over = p_ours_over >= p_book_over
    p_ours = p_ours_over if over else 1 - p_ours_over
    p_book = p_book_over if over else 1 - p_book_over
    odds = float(quoted.loc[stat, 'over_odds' if over else 'under_odds'])
    be = float(break_even(odds, profile))
    return {'hypothesis': hypothesis, 'mechanism': mechanism, **verdict, 'bet_type': stat,
            'line': float(quoted.loc[stat, 'line']), 'parts': parts, 'side': 'Over' if over else 'Under',
            'p_ours': p_ours, 'p_book': p_book, 'gap_pp': 100 * (p_ours - p_book), 'needed_pp': 100 * (be - p_book),
            'clears': p_ours >= be, 'odds': odds, 'n': n, 'as_of': as_of, 'expires_when': 'line_or_odds_change',
            **extra}


def combo_over_from_parts(parts: Dict[str, Dict], combo_line: float, games: pd.DataFrame,
                          prior: pd.DataFrame) -> Optional[float]:
    """P(combo > line) from the parts' prices: each part's mean from its margin-free price (market_mean), its
    variance the player's scaled with that mean, the covariances from the player's correlations pulled toward the
    league's; the sum is a count with that mean and variance (count_over). parts: {stat: {'line', 'p_over'}}."""
    means, variances = {}, {}
    for stat, part in parts.items():
        values = games[stat].astype(float)
        average, var = values.mean(), values.var()
        if pd.isna(var) or average <= 0:
            return None
        means[stat] = market_mean(part['line'], part['p_over'], average, var)
        variances[stat] = var * means[stat] / average
    total_var = sum(variances.values()) + 2 * sum(
        _player_correlation(games, a, b, prior) * math.sqrt(variances[a] * variances[b])
        for a, b in combinations(parts, 2))
    return count_over(sum(means.values()), max(total_var, 0.0), combo_line)


def combo_signals(lines: pd.DataFrame, games: pd.DataFrame, prior: pd.DataFrame, as_of=None,
                  status: Optional[Dict[str, Dict]] = None, profile: str = ACTIVE_PROFILE) -> List[Dict]:
    """H1 for one player's lines of one game from one fetch (bet_type, line, over_odds, under_odds): a signal per
    combo whose parts all have both odds, when the player has MIN_GAMES games. games: his games before the game,
    oldest first (the last RECENT count); prior: pooled_correlations()."""
    recent = games.tail(RECENT)
    if len(recent) < MIN_GAMES or not len(lines):
        return []
    verdict, quoted = _verdict(status, 'H1'), _quoted(lines)
    signals = []
    for combo, stats in COMBOS.items():
        if combo not in quoted.index or not all(s in quoted.index for s in stats):
            continue
        parts = {s: {'line': float(quoted.loc[s, 'line']),
                     'p_over': no_vig(quoted.loc[s, 'over_odds'], quoted.loc[s, 'under_odds'])[0]} for s in stats}
        p_over = combo_over_from_parts(parts, float(quoted.loc[combo, 'line']), recent, prior)
        if p_over is not None:
            signals.append(_signal('H1', 'B', verdict, quoted, combo, p_over, [(s, parts[s]['line']) for s in stats],
                                   len(recent), as_of, profile))
    return signals


def shooting_signals(lines: pd.DataFrame, games: pd.DataFrame, rates: Dict[str, float], as_of=None,
                     status: Optional[Dict[str, Dict]] = None, profile: str = ACTIVE_PROFILE) -> List[Dict]:
    """H2 for one player's lines of one game from one fetch: a signal per makes line whose attempts line is quoted
    too. The attempts line's margin-free price gives the attempts' mean (market_mean); times the player's rate (his
    makes / attempts over all his games, pulled toward the league's `rates` by PRIOR_ATTEMPTS) it's the makes' mean,
    whose count (the player's spread, as market_mean) gives the makes line's chance. games: his games before the
    game, oldest first."""
    recent = games.tail(RECENT)
    if len(recent) < MIN_GAMES or not len(lines):
        return []
    verdict, quoted = _verdict(status, 'H2'), _quoted(lines)
    signals = []
    for made, att in SHOTS.items():
        if made not in quoted.index or att not in quoted.index or made not in rates:
            continue
        m_avg, m_var = recent[made].astype(float).mean(), recent[made].astype(float).var()
        a_avg, a_var = recent[att].astype(float).mean(), recent[att].astype(float).var()
        if not (m_avg > 0 and a_avg > 0) or pd.isna(m_var) or pd.isna(a_var):
            continue
        p_made = no_vig(quoted.loc[made, 'over_odds'], quoted.loc[made, 'under_odds'])[0]
        p_att = no_vig(quoted.loc[att, 'over_odds'], quoted.loc[att, 'under_odds'])[0]
        attempts = market_mean(float(quoted.loc[att, 'line']), p_att, a_avg, a_var)
        implied = market_mean(float(quoted.loc[made, 'line']), p_made, m_avg, m_var) / attempts
        total_made, total_att = float(games[made].sum()), float(games[att].sum())
        rate = (total_made + PRIOR_ATTEMPTS * rates[made]) / (total_att + PRIOR_ATTEMPTS)
        mean = attempts * rate
        p_over = count_over(mean, m_var / m_avg * mean, float(quoted.loc[made, 'line']))
        signals.append(_signal('H2', 'B', verdict, quoted, made, p_over, [(att, float(quoted.loc[att, 'line']))],
                               len(recent), as_of, profile, implied_rate=implied, player_rate=rate,
                               league_rate=rates[made], made=int(total_made), attempted=int(total_att),
                               games_all=len(games)))
    return signals


def spread_signals(lines: pd.DataFrame, games: pd.DataFrame, spreads: Dict[str, float], as_of=None,
                   status: Optional[Dict[str, Dict]] = None, profile: str = ACTIVE_PROFILE) -> List[Dict]:
    """H6 for one player's lines of one game from one fetch: a signal per small line (SMALL_STATS, ≤ SMALL_LINE)
    when the player's results spread more than a Poisson's. The price's mean as if the count were a Poisson
    (market_mean with var = mean), with the player's spread (variance / mean over his last RECENT games, pulled
    toward the league's `spreads` by PRIOR_SPREAD_GAMES) gives the line's chance. A spread of 1 or less changes
    nothing (count_over is then a Poisson), so there's no signal. games: his games before the game, oldest first."""
    recent = games.tail(RECENT)
    n = len(recent)
    if n < MIN_GAMES or not len(lines):
        return []
    verdict, quoted = _verdict(status, 'H6'), _quoted(lines)
    signals = []
    for stat in SMALL_STATS:
        if stat not in quoted.index or stat not in spreads or quoted.loc[stat, 'line'] > SMALL_LINE:
            continue
        values = recent[stat].astype(float)
        if not values.mean() > 0:
            continue
        own = values.var() / values.mean()
        spread = (n * own + PRIOR_SPREAD_GAMES * spreads[stat]) / (n + PRIOR_SPREAD_GAMES)
        if spread <= 1.0001:
            continue
        line = float(quoted.loc[stat, 'line'])
        p_book_over = no_vig(quoted.loc[stat, 'over_odds'], quoted.loc[stat, 'under_odds'])[0]
        mean = market_mean(line, p_book_over, 1.0, 1.0)
        signals.append(_signal('H6', 'C', verdict, quoted, stat, count_over(mean, spread * mean, line), [], n, as_of,
                               profile, spread=spread, own_spread=own, league_spread=spreads[stat],
                               below=float((values < line).mean())))
    return signals


def role_uplift(logs: pd.DataFrame, min_each: int = 3) -> float:
    """How many more minutes a player plays when he starts than off the bench: the median, over players with at
    least min_each games of each in their last RECENT games, of the difference of their averages."""
    if not {'starter', 'MIN', 'player_id_ESPN'} <= set(logs.columns):
        return 0.0
    recent = logs.sort_values('Date').groupby('player_id_ESPN').tail(RECENT) if 'Date' in logs else logs
    per = recent.assign(start=recent['starter'].astype(bool)).groupby(['player_id_ESPN', 'start'])['MIN'].agg(
        ['mean', 'size']).unstack('start')
    if True not in per['size'] or False not in per['size']:
        return 0.0
    both = per[(per['size'][True] >= min_each) & (per['size'][False] >= min_each)]
    return float((both['mean'][True] - both['mean'][False]).median()) if len(both) else 0.0


def role_signals(lines: pd.DataFrame, games: pd.DataFrame, role: Optional[str], uplift: float,
                 spreads: Dict[str, float], as_of=None, status: Optional[Dict[str, Dict]] = None,
                 profile: str = ACTIVE_PROFILE) -> List[Dict]:
    """H5 for one player's lines of one game from one fetch: when tonight's role (RotoWire: 'starter' or 'bench';
    anything else gives nothing) differs from his last ROLE_GAMES games (promoted: at most one start in them;
    demoted: on the bench after all but one were starts), a signal per line. Each price's average (market_mean
    with his spread: variance / mean over his last RECENT games, pulled toward the league's `spreads`) is scaled
    by the new role's minutes over his recent ones. games: his games before the game, oldest first."""
    if role not in ('starter', 'bench') or len(games) < MIN_GAMES or not {'starter', 'MIN'} <= set(games.columns):
        return []
    last = games.tail(ROLE_GAMES)
    starts = int(last['starter'].astype(bool).sum())
    promoted = role == 'starter' and starts <= 1
    if not promoted and not (role == 'bench' and starts >= ROLE_GAMES - 1):
        return []
    recent = games.tail(RECENT)
    usual = float(last['MIN'].mean())
    if not usual > 0:
        return []
    in_role = recent[recent['starter'].astype(bool) == promoted]['MIN']
    guess = max(usual + (uplift if promoted else -uplift), 1.0)
    minutes = (in_role.sum() + ROLE_PRIOR_GAMES * guess) / (len(in_role) + ROLE_PRIOR_GAMES)
    verdict, quoted, n = _verdict(status, 'H5'), _quoted(lines), len(recent)
    signals = []
    for stat in quoted.index:
        values = stat_values(recent, stat)
        if values is None or not values.mean() > 0:
            continue
        own = values.var() / values.mean()
        spread = max((n * own + PRIOR_SPREAD_GAMES * spreads.get(stat, own)) / (n + PRIOR_SPREAD_GAMES), 1.0)
        line = float(quoted.loc[stat, 'line'])
        p_book_over = no_vig(quoted.loc[stat, 'over_odds'], quoted.loc[stat, 'under_odds'])[0]
        mean = market_mean(line, p_book_over, 1.0, spread) * minutes / usual
        signals.append(_signal('H5', 'C', verdict, quoted, stat, count_over(mean, spread * mean, line), [], n,
                               as_of, profile, role=role, starts=starts, last_games=len(last),
                               usual_minutes=usual, minutes=minutes, role_games=len(in_role)))
    return signals


def offer_signals(lines: pd.DataFrame, games: pd.DataFrame, logs: pd.DataFrame, as_of=None,
                  status: Optional[Dict[str, Dict]] = None, profile: str = ACTIVE_PROFILE,
                  role: Optional[str] = None) -> List[Dict]:
    """Every detector's signals for one player's lines of one game: H1, H2, H5 and H6. logs: every player's games
    of the same scope (the league's correlations, shooting rates, spreads and starter-bench minutes). role:
    tonight's per RotoWire ('starter' or 'bench'), for H5."""
    status = hypothesis_status() if status is None else status
    return (combo_signals(lines, games, pooled_correlations(logs), as_of, status, profile)
            + shooting_signals(lines, games, league_rates(logs), as_of, status, profile)
            + spread_signals(lines, games, league_spreads(logs), as_of, status, profile)
            + role_signals(lines, games, role, role_uplift(logs),
                           league_spreads(logs, stats=tuple(lines['bet_type'].dropna().unique())), as_of, status,
                           profile))
