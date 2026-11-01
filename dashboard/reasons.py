"""Reasons for and against an offer in plain words (no Streamlit, so it can be tested). They're written after the
decision (decisions.py) and explain it: how many there are never changes it.

Every reason is {'supports': True / False / None, 'direction': 'for' / 'against' / None, 'text', 'flag', 'kind',
'group', 'used_by_model', 'impact_pp', 'validation', 'value', 'reference', 'n', 'as_of', 'source'}. kind says what
sort of claim it is:
  economics  the price: the model's chance against what the odds need after the cost profile's tax
  driver     an input the model used, with how much it moved the final (calibrated) chance: impact_pp
  context    what the player's games show that the model doesn't use; validation says whether it predicted results
             beyond the model on unseen lines (backtest/reason_lift.py): 'untested', 'no_lift' or 'lift'
  warning    something to know before betting that doesn't block it
  blocker    a red flag (flag=True): it keeps the offer from OBSTAW and the shortlist
Only economics and drivers are for or against (a driver by the sign of its impact); context is for or against only
when it predicted results on unseen lines ('lift'), in the direction it did. A reason without its data (no value,
no reference, no time, no source, no observations where it rests on games) isn't made.
"""
import json
import os
import re
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

import i18n
from metrics import (ACTIVE_PROFILE, alpha, calibrate, logit, no_vig, prop_probability, stint_games,
                     wilson_interval)

MIN_GAMES = 8
ESPN, SUPERBET, ROTOWIRE, MODEL = 'ESPN', 'Superbet', 'RotoWire', 'model'
ECONOMICS, DRIVER, CONTEXT, WARNING, BLOCKER = 'economics', 'driver', 'context', 'warning', 'blocker'
UNTESTED, NO_LIFT, LIFT = 'untested', 'no_lift', 'lift'
# a driver that moves the final chance by less than this (pp) is shown without a direction
IMPACT_MIN = 0.1
# the stats whose points come from shots (volume vs conversion), and the attempts that make 3PM
SHOT_STATS = {'PTS', 'PA', 'PR', 'ARP'}
LIFT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'backtest',
                         'reason_lift.json')


def _known(value) -> bool:
    return value is not None and not (isinstance(value, float) and np.isnan(value)) and value is not pd.NaT


def _reason(supports, text: str, flag: bool = False, value=None, reference=None, n=None, as_of=None,
            source=None, kind: str = CONTEXT, group: Optional[str] = None, used_by_model: bool = False,
            impact_pp=None, validation: Optional[str] = None) -> Dict:
    # numpy comparisons give np.bool_, which `is True` doesn't match
    supports = None if supports is None else bool(supports)
    kind = BLOCKER if flag else kind
    return {'supports': supports, 'direction': None if supports is None else 'for' if supports else 'against',
            'text': text, 'flag': flag, 'kind': kind, 'group': group, 'used_by_model': used_by_model,
            'impact_pp': impact_pp, 'validation': validation, 'value': value, 'reference': reference, 'n': n,
            'as_of': as_of, 'source': source}


def complete(reason: Dict) -> bool:
    """A reason has everything it must show: value, reference, time, source and, unless it's about the quote
    itself (economics, the market's movement), the observations (1+) it rests on. Blockers and warnings aren't
    arguments and are always kept."""
    if reason['flag'] or reason.get('kind') == WARNING:
        return True
    if not all(_known(reason[k]) for k in ('value', 'reference', 'as_of', 'source')):
        return False
    if reason.get('kind') == ECONOMICS or reason.get('group') == 'market':
        return True
    n = reason['n']
    return _known(n) and n >= 1


def _last(dates) -> object:
    """The newest date in a column of game dates (the data a stats reason rests on is that recent)."""
    if dates is None or len(dates) == 0:
        return None
    return pd.to_datetime(pd.Series(dates)).max()


# --- what a context reason measures: the same numbers backtest/reason_lift.py tests on past lines. Each is
# signed for Over (higher = more Over); NaN where there's too little to say ---

def lift_status(path: str = LIFT_FILE) -> Dict[str, Dict]:
    """backtest/reason_lift.py's verdict per context feature: {feature: {'status', 'over_sign', ...}}; {} when it
    hasn't been run (every context reason is then 'untested')."""
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f).get('features', {})
    except (OSError, ValueError):
        return {}


def current_stint(games: pd.DataFrame) -> pd.DataFrame:
    """The player's games since he last joined his current team (all of them without a team column)."""
    if 'team' not in games or games.empty:
        return games
    other = np.flatnonzero(games['team'].values != games['team'].values[-1])
    return games.iloc[other[-1] + 1:] if len(other) else games


def feature_hits(values: pd.Series, line: float, market_over: float, last: int = 10, prior: float = 10) -> float:
    """The Over rate at the line in the last `last` games, pulled toward the market's chance as if it were worth
    `prior` games, on the log-odds scale relative to the market."""
    part = values.tail(last)
    if len(part) < 3 or not _known(market_over):
        return np.nan
    shrunk = (int((part > line).sum()) + prior * market_over) / (len(part) + prior)
    return logit(shrunk) - logit(market_over)


def feature_minutes(stint: pd.DataFrame, recent: int = 5) -> float:
    """Minutes per game in the last `recent` games of the stint minus the earlier ones, in tens of minutes."""
    if len(stint) < MIN_GAMES or 'MIN' not in stint:
        return np.nan
    return (stint['MIN'].tail(recent).mean() - stint['MIN'].iloc[:-recent].mean()) / 10


def feature_venue(games: pd.DataFrame, stat: str, home) -> float:
    """Tonight's venue average minus the overall average, in the player's standard deviations (at least 1)."""
    if not _known(home) or len(games) < 6 or 'type' not in games:
        return np.nan
    part = games.loc[games['type'] == ('home' if home else 'away'), stat]
    if len(part) < 3:
        return np.nan
    return (part.mean() - games[stat].mean()) / max(games[stat].std(), 1.0)


def feature_rest(rest, opp_rest) -> float:
    """The team's rest days minus the opponent's, each capped at 3."""
    if not (_known(rest) and _known(opp_rest)):
        return np.nan
    return float(min(rest, 3) - min(opp_rest, 3))


def feature_vs_opp(history: pd.DataFrame, stat: str, line: float, sd) -> float:
    """The average against tonight's opponent minus the line, in the player's standard deviations (at least 1)."""
    if len(history) < 2:
        return np.nan
    return (history[stat].mean() - line) / max(sd if _known(sd) else 1.0, 1.0)


def _per_minute(games: pd.DataFrame, column: str) -> float:
    minutes = games['MIN'].sum()
    return games[column].sum() / minutes if minutes > 0 else np.nan


def feature_volume(stint: pd.DataFrame, stat: str, recent: int = 5) -> float:
    """The relative change of shot attempts per minute (FGA; 3PA for 3PM) in the last `recent` games of the stint
    against the earlier ones; NaN for stats that aren't made of shots."""
    column = '3PA' if stat == '3PM' else 'FGA' if stat in SHOT_STATS else None
    if column is None or len(stint) < MIN_GAMES or column not in stint or 'MIN' not in stint:
        return np.nan
    now, before = _per_minute(stint.tail(recent), column), _per_minute(stint.iloc[:-recent], column)
    return now / before - 1 if _known(before) and before > 0 and _known(now) else np.nan


# --- the model's drivers: how much each input moved the final chance ---

def driver_impacts(values: pd.Series, line: float, side: str, market: float, adj_avg: float, lineup_adj: float,
                   pace_factor: float, matchup_factor: float, coef: Optional[Dict]) -> Dict[str, float]:
    """For the evaluated side at the same quote: the final (calibrated) chance in pp, and how much each of the
    projection's inputs moved it (final − the chance with that input reset: absences = no lineup adj, environment =
    pace factor 1, opponent = matchup factor 1), plus beyond_price = final − the price alone through the same
    calibration (calibrate(market, market)). The effects aren't additive: don't sum them."""
    pace = pace_factor if _known(pace_factor) else 1.0
    match = matchup_factor if _known(matchup_factor) else 1.0
    adj = lineup_adj if _known(lineup_adj) else 0.0

    def final(mean: float) -> float:
        return 100 * calibrate(prop_probability(values, line, side, market, mean=mean)['p'], market, side, coef)

    p = final(adj_avg * pace * match)
    return {'final': p,
            'price': 100 * calibrate(market, market, side, coef),
            'beyond_price': p - 100 * calibrate(market, market, side, coef),
            'availability': p - final((adj_avg - adj) * pace * match),
            'environment': p - final(adj_avg * match),
            'opponent': p - final(adj_avg * pace)}


def _margin(result: str) -> float:
    """The final margin of a 'W120-110' / 'L106-114' result (positive)."""
    match = re.search(r'(\d+)-(\d+)', str(result or ''))
    return abs(int(match.group(1)) - int(match.group(2))) if match else np.nan


def _side_market(over: float, side: str) -> float:
    return over if side == 'Over' else 1 - over


def offer_context(row, games: pd.DataFrame, logs: pd.DataFrame, lineups: pd.DataFrame, names, odds_at, lineup_at,
                  coef: Optional[Dict] = None) -> Dict:
    """What prop_reasons needs about one priced line (a models.price_props row, with tracking.prop_movement's open
    line, open over / under and first seen when known): the bet dict both dashboards pass it. games: the player's
    games behind the numbers, oldest first; logs: every player's games of the same scope (team schedules,
    teammates); lineups: RotoWire's rows with player_id_ESPN; names: {player_id: display name}; coef: the
    calibration (default models.load_calibration())."""
    if coef is None:
        from models import load_calibration
        coef = load_calibration()
    pid, team, opp = row['player_id'], row.get('team') or '', row.get('opp') or ''
    tip = pd.to_datetime(row['start_time']).tz_convert('US/Eastern').tz_localize(None).normalize()

    def rest_of(dates) -> float:
        before = dates[dates < tip]
        return (tip - before.max()).days if len(before) else np.nan

    listed = lineups[lineups['player_id_ESPN'] == pid] if len(lineups) else lineups
    team_rows = lineups[lineups['team'] == team] if len(lineups) and team else lineups.iloc[0:0]
    from metrics import rotowire_team
    out_ids = rotowire_team(lineups, team)['out'] if team and len(lineups) else []
    # the fewest games the player played without one of tonight's out teammates (the change rests on them)
    missed = [int((~stint_games(logs, pid, o)['teammate_played']).sum()) for o in out_ids if o != pid]
    status = row.get('RotoWire') or ''
    side = row.get('side') or None
    market_over = row.get('market over %', np.nan) / 100
    stat, line = row['bet_type'], row['line']
    impacts = {}
    if side and _known(market_over) and len(games):
        impacts = driver_impacts(games[stat], line, side, _side_market(market_over, side), row['adj avg'],
                                 row['lineup adj'], row.get('pace factor'), row.get('matchup factor'), coef)
    profile = row.get('cost profile') or ACTIVE_PROFILE
    return {'name': row['name'], 'stat': stat, 'side': side, 'line': line, 'odds': row.get('side odds'),
            'model %': row.get('p win %'), 'break-even %': row.get('break-even net %'),
            'edge pp': row.get('edge net pp'), 'ev': row.get('ev net 100'), 'tax': 100 * (1 - alpha(profile)),
            'market over %': row.get('market over %'), 'impacts': impacts,
            'avg': row['avg'], 'proj avg': row['proj avg'], 'lineup adj': row['lineup adj'], 'status': status,
            'play_pct': listed['play_pct'].iloc[0] if len(listed) else np.nan,
            'lineup_status': team_rows['lineup_status'].iloc[0] if len(team_rows) else None,
            'out_names': [str(names.get(p, p)) for p in out_ids], 'out_n': min(missed) if missed else None,
            'team_games': row.get('team_games'), 'odds_at': odds_at, 'lineup_at': lineup_at,
            'stats_through': logs['Date'].max() if len(logs) else None,
            'open_line': row.get('open line', np.nan), 'open_over': row.get('open over', np.nan),
            'open_under': row.get('open under', np.nan), 'first_seen': row.get('first seen'),
            'over_odds': row.get('over_odds'), 'under_odds': row.get('under_odds'), 'start_time': row['start_time'],
            'snapshots': row.get('snapshots', np.nan), 'line_move': row.get('line move', np.nan),
            'home': row.get('is_home'), 'opp': opp, 'team': team,
            'rest_days': rest_of(games['Date']) if len(games) else np.nan,
            'opp_rest': rest_of(logs.loc[logs['team'] == opp, 'Date']) if opp and len(logs) else np.nan,
            'matchup': row.get('matchup_info'), 'implied': row.get('implied'), 'team_pts': row.get('team_pts'),
            'position': games['position_group'].iloc[-1] if len(games) and 'position_group' in games else None,
            'spread': row.get('spread'),
            'starter': status.startswith('starter') if status else
            bool(len(games) and games['starter'].tail(10).mean() > 0.5)}


def prop_reasons(bet: Dict, games: pd.DataFrame, history: pd.DataFrame, lang: str = 'en',
                 validation: Optional[Dict] = None) -> List[Dict]:
    """Reasons about one offer's evaluated side, worded in `lang` (i18n.TEXTS 'reason.*', 'warn.*' and 'flag.*').

    bet: offer_context's dict (name, stat, side, line, odds, model %, break-even %, edge pp after the cost
    profile's tax, ev, tax, market over %, impacts (driver_impacts), avg, proj avg, lineup adj, out_names, out_n,
    status, play_pct, lineup_status, home, rest_days, opp_rest, opp, team, matchup, position, implied, team_pts,
    team_games, spread, starter, line_move, open_line, open_over, open_under, first_seen, start_time, snapshots,
    odds_at, stats_through, lineup_at); missing keys mean the reason isn't made.
    games: the player's games behind the numbers, oldest first. history: his games against the opponent (only
    shown when that feature predicted results: see lift_status). validation: lift_status() (default: the file).
    """
    over = bet['side'] == 'Over'
    favours = lambda higher: higher if over else not higher   # does "the number is higher" help the side?
    stat, line, be, name = bet['stat'], bet['line'], bet['break-even %'], bet['name']
    side = i18n.value(bet['side'], lang)
    values = games[stat] if len(games) else pd.Series(dtype=float)
    n = len(values)
    played_through = _last(games['Date']) if n and 'Date' in games else bet.get('stats_through')
    odds_at = bet.get('odds_at')
    impacts = bet.get('impacts') or {}
    lifts = lift_status() if validation is None else validation
    stint = current_stint(games) if n else games
    reasons = []

    def context(feature: str, value_for_over, text: str, **kw):
        """A context reason: for or against only if the feature predicted results beyond the model."""
        verdict = lifts.get(feature, {})
        status = verdict.get('status', UNTESTED)
        supports = None
        if status == LIFT and _known(value_for_over) and value_for_over != 0:
            supports = favours(value_for_over * verdict.get('over_sign', 1) > 0)
        reasons.append(_reason(supports, text, kind=CONTEXT, validation=status, **kw))

    def driver(group: str, text: str, **kw):
        impact = impacts.get(group)
        supports = None if not _known(impact) or abs(impact) < IMPACT_MIN else impact > 0
        if _known(impact):
            text += i18n.t('reason.impact', lang, impact=impact) if abs(impact) >= IMPACT_MIN else                 i18n.t('reason.impact_none', lang, least=IMPACT_MIN)
        reasons.append(_reason(supports, text, kind=DRIVER, group=group, used_by_model=True, impact_pp=impact,
                               **kw))

    # --- economics ---
    if _known(bet.get('edge pp')):
        tax = bet.get('tax', 12.0)
        ev = bet.get('ev')
        ev = 100 * (bet['model %'] / be - 1) if not _known(ev) else ev
        key = 'reason.model' if tax else 'reason.model_no_tax'
        reasons.append(_reason(bet['edge pp'] > 0, i18n.t(key, lang, side=side, model=bet['model %'],
                                                          odds=bet['odds'], be=be, edge=bet['edge pp'], ev=ev,
                                                          tax=tax),
                               value=bet['model %'], reference=be, as_of=odds_at, source=f"{MODEL} · {SUPERBET}",
                               kind=ECONOMICS, group='price', used_by_model=True))
    if _known(impacts.get('beyond_price')) and _known(bet.get('market over %')):
        market = bet['market over %'] if over else 100 - bet['market over %']
        reasons.append(_reason(None, i18n.t('reason.beyond_price', lang, side=side, market=market,
                                            price=impacts['price'], beyond=impacts['beyond_price']),
                               value=impacts['final'], reference=impacts['price'], as_of=odds_at,
                               source=f"{MODEL} · {SUPERBET}", kind=ECONOMICS, group='price', used_by_model=True))

    # --- the model's drivers ---
    if n:
        proj = bet.get('proj avg', bet['avg'])
        reasons.append(_reason(None, i18n.t('reason.expected', lang, proj=proj, stat=stat, line=line, diff=proj - line,
                                            avg=bet['avg'], median=values.median()),
                               value=proj, reference=line, n=n, as_of=played_through, source=f"{MODEL} · {ESPN}",
                               kind=DRIVER, group='projection', used_by_model=True))

    adj = bet.get('lineup adj', 0) or 0
    if adj and bet.get('out_names'):
        driver('availability', i18n.t('reason.teammates', lang, names=', '.join(bet['out_names']), name=name,
                                      adj=adj, stat=stat, n=bet.get('out_n') or 0),
               value=bet['avg'] + adj, reference=bet['avg'], n=bet.get('out_n'), as_of=bet.get('lineup_at'),
               source=f"{ROTOWIRE} · {ESPN}")

    implied, usual = bet.get('implied'), bet.get('team_pts')
    if _known(implied) and _known(usual) and usual:
        driver('environment', i18n.t('reason.environment', lang, team=bet['team'].upper(), implied=implied,
                                     usual=usual),
               value=implied, reference=usual, n=bet.get('team_games'), as_of=odds_at, source=f"{SUPERBET} · {ESPN}")

    m = bet.get('matchup') or {}
    if m:
        position = bet.get('position') if bet.get('position') in ('G', 'F', 'C') else ''
        driver('opponent', i18n.t('reason.matchup', lang, opp=bet['opp'].upper(), value=m['value'], stat=stat,
                                  position=i18n.t(f'reason.position.{position}', lang), diff=abs(m['diff']),
                                  more=i18n.t('reason.more' if m['diff'] > 0 else 'reason.fewer', lang),
                                  rank=m['rank'], teams=m['teams'], word=i18n.value(m['word'], lang)),
               value=m['value'], reference=m['average'], n=m.get('games'),
               as_of=bet.get('stats_through') or played_through, source=ESPN)

    # --- context: what the games show that the model doesn't use (or uses only as part of its hit rate) ---
    if n >= 3:
        last = values.tail(10)
        hits = int((last > line).sum() if over else (last < line).sum())
        low, high = wilson_interval(hits, len(last))
        text = i18n.t('reason.history_last', lang, side=side, hits=hits, n=len(last), rate=100 * hits / len(last),
                      low=100 * low, high=100 * high)
        if n > 10:
            every = int((values > line).sum() if over else (values < line).sum())
            text += i18n.t('reason.history_all', lang, hits=every, n=n, rate=100 * every / n)
        text += i18n.t('reason.history_note', lang, be=be)
        if 'top_up' in games and games['top_up'].any():
            text += i18n.t('reason.sample_last_season', lang, n=int(games['top_up'].sum()))
        if 'season_type' in games and (games['season_type'] == 'pre').any():
            text += i18n.t('reason.sample_preseason', lang, n=int((games['season_type'] == 'pre').sum()))
        context('hits_l10', feature_hits(values, line, bet.get('market over %', np.nan) / 100
                                         if _known(bet.get('market over %')) else np.nan),
                text, group='history', value=100 * hits / len(last), reference=be, n=n, as_of=played_through,
                source=ESPN)

    if len(stint) >= MIN_GAMES and 'MIN' in stint:
        recent, earlier = stint['MIN'].tail(5), stint['MIN'].iloc[:-5]
        if abs(recent.mean() - earlier.mean()) >= 3:
            text = i18n.t('reason.minutes', lang, recent=recent.mean(), usual=earlier.mean(), n=len(earlier),
                          team=str(stint['team'].iloc[-1]).upper() if 'team' in stint else '',
                          low=recent.min(), high=recent.max())
            short = stint.tail(5)[stint['MIN'].tail(5) < 0.75 * earlier.mean()]
            if len(short):
                fouls = int((short['PF'] >= 5).sum()) if 'PF' in short else 0
                blowouts = int((short['Result'].map(_margin) >= 20).sum()) if 'Result' in short else 0
                text += i18n.t('reason.minutes_short', lang, short=len(short), fouls=fouls, blowouts=blowouts)
            context('minutes', feature_minutes(stint), text, group='minutes_role', value=recent.mean(),
                    reference=earlier.mean(), n=len(stint), as_of=played_through, source=ESPN)

    if 'starter' in games and n and bet.get('status'):
        tonight = 'starter' if bet['status'].startswith('starter') else 'bench' if bet['status'] == 'bench' else None
        last = games['starter'].tail(10).astype(bool)
        if tonight:
            reasons.append(_reason(None, i18n.t('reason.role', lang, started=int(last.sum()), n=len(last),
                                                role=i18n.value(tonight, lang)),
                                   value=int(last.sum()), reference=len(last), n=len(last),
                                   as_of=bet.get('lineup_at') or played_through, source=f"{ESPN} · {ROTOWIRE}",
                                   kind=CONTEXT, group='minutes_role', validation=UNTESTED))
            share = last.mean()
            if (tonight == 'starter' and share <= 0.3) or (tonight == 'bench' and share >= 0.7):
                reasons.append(_reason(None, i18n.t('warn.role', lang, started=int(last.sum()), n=len(last),
                                                    role=i18n.value(tonight, lang)),
                                       kind=WARNING, group='minutes_role'))

    if n and 'team' in games and len(stint) < min(MIN_GAMES, n):
        reasons.append(_reason(None, i18n.t('warn.stint', lang, k=len(stint), n=n,
                                            team=str(games['team'].iloc[-1]).upper()),
                               kind=WARNING, group='minutes_role'))

    if stat in SHOT_STATS | {'3PM'} and len(stint) >= MIN_GAMES and {'FGA', '3PA', 'FTA', 'FGM', '3PM', 'FTM',
                                                                     'MIN'} <= set(stint.columns):
        recent, earlier = stint.tail(5), stint.iloc[:-5]
        per36 = lambda part, col: 36 * _per_minute(part, col)
        made = lambda part, made_, tried: 100 * part[made_].sum() / part[tried].sum() if part[tried].sum() else 0.0
        attempts = int(recent['FGA'].sum() + recent['FTA'].sum())
        if _known(per36(recent, 'FGA')) and _known(per36(earlier, 'FGA')):
            context('volume', feature_volume(stint, stat),
                    i18n.t('reason.volume', lang, fga=per36(recent, 'FGA'), tpa=per36(recent, '3PA'),
                           fta=per36(recent, 'FTA'), fga0=per36(earlier, 'FGA'), tpa0=per36(earlier, '3PA'),
                           fta0=per36(earlier, 'FTA'), fg=made(recent, 'FGM', 'FGA'), tp=made(recent, '3PM', '3PA'),
                           ft=made(recent, 'FTM', 'FTA'), fg0=made(earlier, 'FGM', 'FGA'),
                           tp0=made(earlier, '3PM', '3PA'), ft0=made(earlier, 'FTM', 'FTA'), attempts=attempts),
                    group='opportunity', value=per36(recent, 'FGA'), reference=per36(earlier, 'FGA'),
                    n=len(stint), as_of=played_through, source=ESPN)

    if _known(bet.get('home')) and n >= 6:
        where = 'home' if bet['home'] else 'away'
        part = games.loc[games['type'] == where, stat]
        if len(part) >= 3:
            context('venue', feature_venue(games, stat, bet['home']),
                    i18n.t('reason.home' if bet['home'] else 'reason.away', lang, value=part.mean(), n=len(part),
                           avg=values.mean()),
                    group='environment', value=part.mean(), reference=values.mean(), n=len(part),
                    as_of=played_through, source=ESPN)

    rest, opp_rest = bet.get('rest_days'), bet.get('opp_rest')
    if _known(rest) and _known(opp_rest) and n:
        days = lambda d: '3+' if d >= 3 else f"{int(d)}"
        dates = pd.to_datetime(games['Date'])
        tip = dates.max() + pd.Timedelta(days=int(rest))
        within = lambda d: games.loc[dates >= tip - pd.Timedelta(days=d), 'MIN'].sum() if 'MIN' in games else 0
        context('rest', feature_rest(rest, opp_rest),
                i18n.t('reason.rest', lang, team=bet['team'].upper(), rest=days(rest), opp=bet['opp'].upper(),
                       opp_rest=days(opp_rest), name=name, m3=within(3), m7=within(7)),
                group='environment', value=min(rest, 3), reference=min(opp_rest, 3), n=n, as_of=played_through,
                source=ESPN)

    if len(history) >= 2 and lifts.get('vs_opp', {}).get('status') == LIFT:
        context('vs_opp', feature_vs_opp(history, stat, line, values.std()),
                i18n.t('reason.vs_opp', lang, opp=bet['opp'].upper(), avg=history[stat].mean(), stat=stat,
                       n=len(history)),
                group='opponent', value=history[stat].mean(), reference=line, n=len(history),
                as_of=_last(history['Date']) if 'Date' in history else None, source=ESPN)

    spread = bet.get('spread')
    if _known(spread) and abs(spread) >= 10 and bet.get('starter') and 'Result' in games and 'MIN' in games:
        margin = games['Result'].map(_margin)
        big, close = games.loc[margin >= 15, 'MIN'], games.loc[margin < 15, 'MIN']
        if len(big) >= 2 and len(close) >= 2:
            context('blowout', abs(spread),
                    i18n.t('reason.blowout_favoured' if spread < 0 else 'reason.blowout_underdogs', lang,
                           team=bet['team'].upper(), spread=abs(spread), big=big.mean(), n_big=len(big),
                           close=close.mean(), n_close=len(close)),
                    group='environment', value=big.mean(), reference=close.mean(), n=len(games), as_of=odds_at,
                    source=f"{SUPERBET} · {ESPN}")

    open_line = bet.get('open_line')
    if _known(open_line):
        hours = (pd.Timestamp(bet['start_time']) - pd.Timestamp(odds_at)).total_seconds() / 3600 \
            if _known(bet.get('start_time')) and _known(odds_at) else np.nan
        move = line - open_line
        open_odds = bet.get('open_over') if over else bet.get('open_under')
        if move:
            text = i18n.t('reason.line_moved', lang, move=move, open=open_line, line=line)
        elif _known(open_odds) and _known(bet.get('odds')) and abs(open_odds - bet['odds']) > 1e-9:
            was = _side_market(no_vig(bet.get('open_over'), bet.get('open_under'))[0], bet['side'])
            now = _side_market(no_vig(bet.get('over_odds'), bet.get('under_odds'))[0], bet['side'])
            text = i18n.t('reason.odds_moved', lang, line=line, open_odds=open_odds, odds=bet['odds'], side=side,
                          was=100 * was, now=100 * now)
        else:
            text = None
        if text:
            if _known(hours):
                text += i18n.t('reason.before_tip', lang, hours=hours)
            reasons.append(_reason(None, text, value=line, reference=open_line, n=bet.get('snapshots'),
                                   as_of=odds_at, source=SUPERBET, kind=CONTEXT, group='market'))

    if bet.get('lineup_status') == 'expected':
        reasons.append(_reason(None, i18n.t('warn.lineup_expected', lang, team=bet['team'].upper()), kind=WARNING,
                               group='availability'))

    # blockers: an offer with one can't get OBSTAW (the tables show them as 🔴)
    preseason_only = bool(n and 'season_type' in games and (games['season_type'] == 'pre').all())
    minutes = games['MIN'] if n else pd.Series(dtype=float)
    reasons += [_reason(False, text, flag=True) for text in
                prop_flags(n, preseason_only, bet.get('play_pct'), bet.get('status'), minutes, bet.get('line_move'),
                           bet['side'], lang)]
    return [r for r in reasons if complete(r)]


def prop_flag_items(n: int, preseason_only: bool, play_pct, status, minutes: pd.Series, line_move,
                    side) -> List[Tuple[str, Dict]]:
    """The reasons to pass a prop whatever its numbers say, as (i18n text key, values): too few games, preseason
    only, out, may not play, unstable minutes, the line moving against the pick. minutes: the player's minutes in
    the games behind the numbers."""
    items = []
    if n < MIN_GAMES:
        items.append(('flag.few_games', {'n': n}))
    if preseason_only:
        items.append(('flag.preseason', {}))
    if _known(play_pct) and play_pct == 0:
        items.append(('flag.out', {'status': status}))
    if _known(play_pct) and 0 < play_pct < 100:
        items.append(('flag.may_not_play', {'status': status}))
    if n >= 5 and len(minutes) and minutes.mean() > 0 and minutes.std() / minutes.mean() > 0.35:
        items.append(('flag.minutes', {'low': minutes.min(), 'high': minutes.max()}))
    if _known(line_move) and abs(line_move) >= 1.5 and (line_move > 0) != (side == 'Over'):
        items.append(('flag.line_against', {'move': abs(line_move)}))
    return items


def flag_texts(items: List[Tuple[str, Dict]], lang: str = 'en') -> List[str]:
    return [i18n.t(key, lang, **values) for key, values in items]


def prop_flags(n: int, preseason_only: bool, play_pct, status, minutes: pd.Series, line_move, side,
               lang: str = 'en') -> List[str]:
    """prop_flag_items in words."""
    return flag_texts(prop_flag_items(n, preseason_only, play_pct, status, minutes, line_move, side), lang)


def flag_props(table: pd.DataFrame, logs: pd.DataFrame, lineups: pd.DataFrame) -> pd.DataFrame:
    """models.price_props output (with prop_movement's 'line move' when there is one) with 'red flag' (the
    prop_flags of each line in English, joined; '' when none; saved with the snapshots), 'flag items' (the same as
    prop_flag_items, for showing them in another language), 🔴 as the signal of every flagged line and no bet on it
    (pass). The line moving against a side is judged for the evaluated side (price_props' side). logs: the games the lines were priced from; lineups: RotoWire's (with ESPN ids)."""
    by_player = {pid: g for pid, g in logs.groupby('player_id_ESPN')}
    listed = lineups.dropna(subset=['player_id_ESPN']).drop_duplicates('player_id_ESPN') if len(lineups) else lineups
    play_pct = listed.set_index('player_id_ESPN')['play_pct'] if len(listed) else pd.Series(dtype=float)
    empty = pd.Series(dtype=float)
    items = []
    for _, row in table.iterrows():
        games = by_player.get(row['player_id'])
        n = 0 if games is None else len(games)
        items.append(prop_flag_items(n, bool(n and (games['season_type'] == 'pre').all()),
                                     play_pct.get(row['player_id']), row.get('RotoWire'),
                                     games['MIN'] if n else empty, row.get('line move'),
                                     row.get('side') or row['best side']))
    flags = pd.Series(['; '.join(flag_texts(i)) for i in items], index=table.index)
    out = table.assign(**{'red flag': flags, 'flag items': pd.Series(items, index=table.index, dtype=object),
                          'signal': table['signal'].where(flags == '', '🔴')})
    if 'bet' in out:
        out['bet'] = out['bet'].where(flags == '', '')
    return out


def game_reasons(outcome: Dict, ctx: Dict, lang: str = 'en') -> List[Dict]:
    """Reasons about one game outcome (a row of metrics.market_edges), worded in `lang` (i18n 'game.*'). Research
    only: team markets are always NIEDOSTEPNE (decisions.team_decision).

    ctx: projection (game_projection), ratings (blended_ratings), home, away, absences ({team: [(name, impact)]}),
    home_court, games_played ({team: current-season games}), rotowire (bool: RotoWire lists the game), odds_at
    (when the odds were fetched), stats_through (the newest stored game).
    """
    p, r, home, away = ctx['projection'], ctx['ratings'], ctx['home'], ctx['away']
    market, side, line = outcome['market'], outcome['side'], outcome['line']
    played = min(ctx['games_played'].get(t, 0) for t in (home, away))
    odds_at, through = ctx.get('odds_at'), ctx.get('stats_through')
    be = outcome.get('break-even net %', outcome['implied %'])
    edge = outcome.get('edge net pp', outcome['edge pp'])
    reasons = [_reason(edge > 0, i18n.t('game.model', lang, model=outcome['model %'], be=be, odds=outcome['odds'],
                                        edge=edge),
                       value=outcome['model %'], reference=be, n=played, as_of=odds_at, source=f"{MODEL} · {SUPERBET}",
                       kind=ECONOMICS, group='price', used_by_model=True)]
    league = r[['off_rtg', 'def_rtg', 'pace']].mean()
    # the game model's inputs (it isn't admitted: these explain its estimate, not a bet)
    rated = dict(n=played, as_of=through, source=f"{MODEL} · {ESPN}", kind=DRIVER, group='projection',
                 used_by_model=True)
    absent = dict(kind=DRIVER, group='availability', used_by_model=True)
    if market in ('ML', 'SPREAD'):
        team, opp = (home, away) if side == 'home' else (away, home)
        margin = p['margin'] if side == 'home' else -p['margin']
        handicap = line if market == 'SPREAD' and pd.notna(line) else 0
        cover = margin + handicap
        what = i18n.t('game.wins_by' if margin >= 0 else 'game.loses_by', lang, margin=abs(margin))
        spread_part = i18n.t('game.covering' if cover > 0 else 'game.missing', lang, line=line, gap=abs(cover)) \
            if market == 'SPREAD' and pd.notna(line) else ""
        reasons.append(_reason(cover > 0, i18n.t('game.projection', lang, team=team.upper(), what=what) + spread_part,
                               value=margin, reference=-handicap, **rated))
        net = lambda tm: r.loc[tm, 'off_rtg'] - r.loc[tm, 'def_rtg']
        reasons.append(_reason(net(team) > net(opp), i18n.t('game.net', lang, team=team.upper(), net=net(team),
                                                            opp=opp.upper(), opp_net=net(opp)),
                               value=net(team), reference=net(opp), **rated))
        for tm in (team, opp):
            for name, imp in ctx['absences'].get(tm, []):
                swing = imp['pts_for'] - imp['pts_against']
                if imp['n_without'] and abs(swing) >= 0.5:
                    helps = (swing > 0) == (tm == team)
                    reasons.append(_reason(helps, i18n.t('game.absence_margin', lang, team=tm.upper(), name=name,
                                                         swing=swing, n=imp['n_without']),
                                           value=swing, reference=0, n=imp['n_without'], as_of=through,
                                           source=f"{ROTOWIRE} · {ESPN}", **absent))
    else:
        over = side == 'over'
        expected = {'TOTAL': p['total'], 'HOME_TOTAL': p['home_pts'], 'AWAY_TOTAL': p['away_pts']}[market]
        gap = expected - line
        reasons.append(_reason(gap > 0 if over else gap < 0,
                               i18n.t('game.projected_total', lang, expected=expected, line=line, gap=gap),
                               value=expected, reference=line, **rated))
        faster = p['pace'] - league['pace']
        reasons.append(_reason(None if abs(faster) < 1 else (faster > 0) == over,
                               i18n.t('game.pace_faster' if p['pace'] > league['pace'] else 'game.pace_slower', lang,
                                      pace=p['pace'], league=league['pace']),
                               value=p['pace'], reference=league['pace'], **rated))
        teams = {'TOTAL': (home, away), 'HOME_TOTAL': (home,), 'AWAY_TOTAL': (away,)}[market]
        for tm in teams:
            opp = away if tm == home else home
            attack = r.loc[tm, 'off_rtg'] - league['off_rtg'] + r.loc[opp, 'def_rtg'] - league['def_rtg']
            reasons.append(_reason(None if abs(attack) < 1 else (attack > 0) == over,
                                   i18n.t('game.attack', lang, team=tm.upper(), off=r.loc[tm, 'off_rtg'],
                                          opp=opp.upper(), defense=r.loc[opp, 'def_rtg'], league=league['off_rtg'],
                                          attack=attack),
                                   value=attack, reference=0, **rated))
        for tm in (home, away):
            for name, imp in ctx['absences'].get(tm, []):
                change = imp['pts_for'] + imp['pts_against'] if market == 'TOTAL' else \
                    imp['pts_for'] if tm in teams else imp['pts_against']
                if imp['n_without'] and abs(change) >= 0.5:
                    reasons.append(_reason((change > 0) == over,
                                           i18n.t('game.absence_points', lang, team=tm.upper(), name=name,
                                                  change=change, n=imp['n_without']),
                                           value=change, reference=0, n=imp['n_without'], as_of=through,
                                           source=f"{ROTOWIRE} · {ESPN}", **absent))

    reasons += [_reason(False, text, flag=True)
                for text in game_flags(edge, played, ctx['rotowire'], lang)]
    return [reason for reason in reasons if complete(reason)]


def game_flags(edge_pp: float, games_played: int, rotowire: bool, lang: str = 'en') -> List[str]:
    """Warnings on a game market whatever its numbers say. games_played: the fewer of the two teams'
    current-season games; rotowire: RotoWire lists the game."""
    keys = (['gameflag.early'] if games_played < 5 else []) + ([] if rotowire else ['gameflag.no_lineup']) \
        + (['gameflag.big_edge'] if edge_pp > 15 else [])
    return [i18n.t(key, lang) for key in keys]


def flag_game_outcomes(edges: pd.DataFrame, games_played: int, rotowire: bool, lang: str = 'en') -> pd.DataFrame:
    """metrics.market_edges rows of one game with 'red flag' (game_flags, joined) and 'signal': 🔴 when flagged,
    otherwise ''. The game model isn't admitted (it predicted worse than the price on the settled nights: see the
    game section of data/backtest/calibration.md), so its edges are estimates and never 🟢 / 🟡."""
    edge = edges['edge net pp'] if 'edge net pp' in edges else edges['edge pp']
    flags = pd.Series(['; '.join(game_flags(e, games_played, rotowire, lang)) for e in edge], index=edges.index)
    signal = np.where(flags != '', '🔴', '')
    return edges.assign(signal=signal, **{'red flag': flags})
