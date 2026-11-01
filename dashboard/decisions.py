"""One decision per game for the team markets and one for its players (no Streamlit, tested in test_decisions.py).

A decision comes only from the price, the model, how fresh the odds and lineups are and whether the model family is
admitted. The reasons for and against (reasons.py) are written after it and explain it; how many there are never
changes it.

  OBSTAW         an offer that meets a threshold recorded on an independent period. No such threshold exists yet
                 (ADMITTED_THRESHOLD is None), so no offer can get it.
  NIE_OBSTAWIAJ  the evaluation is current and no offer meets the condition.
  CZEKAJ         the evaluation isn't current: no (fresh) odds, no lineup for a team of the game, the player whose
                 offer is best is questionable, or two offers tie for the one slot.
  NIEDOSTEPNE    the model family isn't admitted: every game market, and props without a calibration fitted for
                 the current model.

Next to the decision, shortlist() answers the relative question the decision can't: if one bets tonight anyway,
which lines are the best of the night? It ranks lines by expected return; it never makes a line OBSTAW, and its
lines still lose money on average after the stake tax (data/backtest/shortlist.md has the evidence).
"""
import re
from datetime import timedelta
from typing import Dict, Optional

import numpy as np
import pandas as pd

OBSTAW, NIE_OBSTAWIAJ, CZEKAJ, NIEDOSTEPNE = 'OBSTAW', 'NIE_OBSTAWIAJ', 'CZEKAJ', 'NIEDOSTEPNE'
STATUSES = (OBSTAW, NIE_OBSTAWIAJ, CZEKAJ, NIEDOSTEPNE)
# the edge net pp (metrics.ACTIVE_PROFILE) an offer needs for OBSTAW, recorded on a period no fit or threshold
# choice has seen. None: there isn't one, so OBSTAW can't be reached. The 🟢 threshold of backtest/calibrate.py
# doesn't qualify: it's chosen on the same held-out nights it's judged on
ADMITTED_THRESHOLD: Optional[float] = None
# odds older than this aren't a current price (the sidebar's freshness strip uses the same limit)
MAX_ODDS_AGE = timedelta(hours=3)
# two offers whose expected returns (per 100) differ by less than this tie
TIE_EV = 0.1
# the shortlist (backtest/shortlist.py): the night's lines ranked by expected return. On 77 unseen 2022/23 nights the
# best line of up to 5 games a night won 3.8 pp more often than the margin-free price said (about break-even before
# the tax, −11.9% after it, against −15.5% for every line), and the lines in the night's best quarter beat the
# price too, while the rest didn't. Relative, not an edge: it's no OBSTAW
TOP, LOOK = 'top', 'look'
SHORTLIST_TOP = 5            # TOP: the best line of each of up to this many games a night
SHORTLIST_LOOK = 0.25        # LOOK: any other line in the night's best quarter by expected return


def _decision(status: str, reason: str, offer=None, odds_at=None, lineup_at=None, **values) -> Dict:
    return {'status': status, 'reason': reason, 'values': values, 'offer': offer, 'odds_at': odds_at,
            'lineup_at': lineup_at}


def team_decision(game: Optional[Dict] = None, odds_at=None) -> Dict:
    """The decision for a game's team markets (winner, handicap, totals): NIEDOSTEPNE, always. The game model isn't
    admitted (it predicted worse than the margin-free price on the settled nights: data/backtest/calibration.md),
    and nothing admits it automatically, however many outcomes settle."""
    return _decision(NIEDOSTEPNE, 'decision.reason.game_model', odds_at=odds_at)


def _utc(when) -> pd.Timestamp:
    ts = pd.Timestamp(when)
    return ts.tz_localize('UTC') if ts.tzinfo is None else ts.tz_convert('UTC')


def lineup_time(lineups: Optional[pd.DataFrame], teams):
    """When RotoWire's lineup of these teams was fetched (the older of the two), if the lineups say."""
    if lineups is None or lineups.empty or 'fetched_at' not in lineups:
        return None
    times = lineups[lineups['team'].isin(list(teams))]['fetched_at'].dropna()
    return times.min() if len(times) else None


def play_chance(status: str) -> Optional[float]:
    """The chance to play in RotoWire's role text (models.rotowire_status: 'Ques 50%', 'Out 0%'); None for a
    starter, a bench player or a player RotoWire doesn't list."""
    match = re.search(r'(\d+)%$', status or '')
    return float(match.group(1)) if match else None


def player_decision(rows: pd.DataFrame, calibration_status: str, lineups: Optional[pd.DataFrame], fetched_at, now,
                    threshold: Optional[float] = ADMITTED_THRESHOLD) -> Dict:
    """The one decision for the players of one game. rows: models.price_props + reasons.flag_props rows of the
    game's lines (name, side, side odds, ev net 100, edge net pp, red flag, RotoWire, home, away); lineups:
    RotoWire's rows (team; fetched_at when known); fetched_at: when the odds were fetched; now: the time freshness
    is judged at. Returns {'status', 'reason' (i18n key), 'values', 'offer' (the row, only for OBSTAW), 'odds_at',
    'lineup_at'}. In order:
      1. no calibration fitted for the current model → NIEDOSTEPNE
      2. no line with a price on its evaluated side, or odds older than MAX_ODDS_AGE → CZEKAJ
      3. RotoWire doesn't list a team of the game, or the best line's player is questionable → CZEKAJ
      4. no line without a red flag whose ev net 100 > 0 and edge net pp ≥ threshold (none without a threshold)
         → NIE_OBSTAWIAJ
      5. the two best such lines tie on expected return → CZEKAJ
      6. → OBSTAW with the best one."""
    from models import FITTED
    teams = (rows['home'].iloc[0], rows['away'].iloc[0]) if len(rows) else ()
    when = {'odds_at': fetched_at, 'lineup_at': lineup_time(lineups, teams)}
    if calibration_status != FITTED:
        return _decision(NIEDOSTEPNE, 'decision.reason.no_calibration', **when)
    priced = rows[rows['side'].fillna('').ne('') & rows['side odds'].notna()] if len(rows) else rows
    # a player RotoWire lists as out (0%) won't play: his lines are refunded, not offers
    if len(priced):
        priced = priced[[play_chance(str(s or '')) != 0 for s in priced['RotoWire']]]
    if priced.empty:
        return _decision(CZEKAJ, 'decision.reason.no_odds', **when)
    if fetched_at is not None and now is not None:
        age = _utc(now) - _utc(fetched_at)
        if age > MAX_ODDS_AGE:
            return _decision(CZEKAJ, 'decision.reason.stale_odds', hours=age.total_seconds() / 3600, **when)
    listed = set(lineups['team']) if lineups is not None and len(lineups) else set()
    missing = [team for team in teams if team not in listed]
    if missing:
        return _decision(CZEKAJ, 'decision.reason.no_lineup', teams=', '.join(t.upper() for t in missing), **when)
    top = priced.sort_values('ev net 100', ascending=False).iloc[0]
    chance = play_chance(str(top.get('RotoWire') or ''))
    if chance is not None and 0 < chance < 100:
        return _decision(CZEKAJ, 'decision.reason.questionable', name=top['name'], role=top['RotoWire'], **when)
    if threshold is None:
        return _decision(NIE_OBSTAWIAJ, 'decision.reason.no_threshold', **when)
    clean = priced[priced['red flag'].fillna('') == ''] if 'red flag' in priced else priced
    candidates = clean[(clean['ev net 100'] > 0) & (clean['edge net pp'] >= threshold)] \
        .sort_values('ev net 100', ascending=False)
    if candidates.empty:
        return _decision(NIE_OBSTAWIAJ, 'decision.reason.no_offer', threshold=threshold, **when)
    if len(candidates) > 1 and candidates['ev net 100'].iloc[0] - candidates['ev net 100'].iloc[1] < TIE_EV:
        return _decision(CZEKAJ, 'decision.reason.tie', **when)
    return _decision(OBSTAW, 'decision.reason.meets', offer=candidates.iloc[0], **when)


def game_decisions(table: pd.DataFrame, calibration_status: str, lineups: Optional[pd.DataFrame], fetched_at,
                   now) -> Dict:
    """player_decision of every game in a price_props table: {event_id: decision}."""
    return {event_id: player_decision(rows, calibration_status, lineups, fetched_at, now)
            for event_id, rows in table.groupby('event_id', sort=False)}


def actionable(decisions: Dict) -> list:
    """The offers to show as a list: only those of OBSTAW decisions (none, while no threshold is recorded)."""
    return [d['offer'] for d in decisions.values() if d['status'] == OBSTAW and d['offer'] is not None]


def offers_table(decisions: Dict) -> pd.DataFrame:
    """The offers a page may list: one per game whose decision is OBSTAW. Empty otherwise: when nothing qualifies
    there's no ranking of the rest (no 'least loss' list)."""
    offers = actionable(decisions)
    return pd.DataFrame(offers).reset_index(drop=True) if offers else pd.DataFrame()


def shortlist(table: pd.DataFrame, decisions: Optional[Dict] = None) -> pd.DataFrame:
    """The best lines of each night by expected return: a ranking, not a bet signal. table: price_props +
    flag_props rows (event_id, name_ESPN, bet_type, side, side odds, p win %, market over %, ev net 100, red flag,
    RotoWire; start_time sets the night, else it's all one night); decisions: game_decisions of the same lines.

    A line is ranked within its night by ev net 100 (ties: event, player, stat). It's left out when its game's
    model isn't admitted (NIEDOSTEPNE), it has a red flag, or RotoWire doesn't list its player as sure to play;
    each player keeps his best line. tier TOP is the best line of each of the SHORTLIST_TOP best games, LOOK any
    other line in the night's best SHORTLIST_LOOK of every priced line. A game whose decision is CZEKAJ (old odds,
    no lineup) keeps its lines, with the decision's reason in 'wait', so the list isn't empty while lines are
    priced. Adds tier, rank (1 = best of the night), night pct (100 × rank among the night's priced lines),
    side market % (the margin-free price of the evaluated side) and above price pp (p win % − side market %)."""
    columns = ['tier', 'rank', 'night pct', 'side market %', 'above price pp', 'wait']
    if table.empty:
        return pd.DataFrame(columns=list(table.columns) + columns)
    decisions = decisions or {}
    priced = table[table['side'].fillna('').ne('') & table['side odds'].notna() & table['ev net 100'].notna()]
    if 'start_time' in priced:
        from nightly import et_night
        priced = priced.assign(night=et_night(priced['start_time']).values)
    else:
        priced = priced.assign(night=0)
    priced = priced.sort_values(['night', 'ev net 100', 'event_id', 'name_ESPN', 'bet_type'],
                                ascending=[True, False, True, True, True], kind='stable')
    priced['night pct'] = 100 * (priced.groupby('night').cumcount() + 1) / priced.groupby('night')['night'] \
        .transform('size')
    status = priced['event_id'].map(lambda e: decisions.get(e, {}).get('status'))
    chance = [play_chance(str(r or '')) for r in priced['RotoWire']] if 'RotoWire' in priced else [None] * len(priced)
    sure = pd.Series([c is None or c >= 100 for c in chance], index=priced.index)
    clean = priced['red flag'].fillna('').eq('') if 'red flag' in priced else True
    eligible = priced[(status != NIEDOSTEPNE) & sure & clean].drop_duplicates(['night', 'name_ESPN'])
    top = eligible.drop_duplicates(['night', 'event_id']).groupby('night', sort=False).head(SHORTLIST_TOP)
    look = eligible[~eligible.index.isin(top.index) & (eligible['night pct'] <= 100 * SHORTLIST_LOOK)]
    out = pd.concat([top.assign(tier=TOP), look.assign(tier=LOOK)])
    out = out.assign(is_top=out['tier'] == TOP)         .sort_values(['night', 'is_top', 'ev net 100'], ascending=[True, False, False], kind='stable')         .drop(columns='is_top')
    out['rank'] = out.groupby('night').cumcount() + 1
    over = out['side'] == 'Over'
    market_over = out['market over %'] if 'market over %' in out else pd.Series(np.nan, index=out.index)
    out['side market %'] = market_over.where(over, 100 - market_over)
    out['above price pp'] = out['p win %'] - out['side market %']
    out['wait'] = [decisions.get(e, {}).get('reason', '') if decisions.get(e, {}).get('status') == CZEKAJ else ''
                   for e in out['event_id']]
    return out.drop(columns='night').reset_index(drop=True)


def offer_decision(decision: Dict, row) -> Dict:
    """The game's player decision as it applies to one of its lines: the decision itself, except that under
    OBSTAW every line but the chosen offer is NIE_OBSTAWIAJ (one game, one offer)."""
    if decision['status'] != OBSTAW or (decision['offer'] is not None and offer_key(decision['offer']) == offer_key(row)):
        return decision
    return _decision(NIE_OBSTAWIAJ, 'decision.reason.other_offer', odds_at=decision['odds_at'],
                     lineup_at=decision['lineup_at'])


def offer_key(row) -> tuple:
    """(event_id, name_ESPN, bet_type): one offer across refreshes (its line and odds may change)."""
    return (row['event_id'], row['name_ESPN'], row['bet_type'])


def offer_changed(before: Optional[Dict], now: Dict) -> Dict:
    """What changed in an open offer since its decision was shown: {'changed', 'line': (was, is) or None,
    'odds': (was, is) or None}. before / now: {'line', 'odds'}; before None = nothing shown yet."""
    out = {'changed': False, 'line': None, 'odds': None}
    if not before:
        return out
    for key in ('line', 'odds'):
        was, is_ = before.get(key), now.get(key)
        if pd.isna(was) and pd.isna(is_):
            continue
        if pd.isna(was) or pd.isna(is_) or abs(float(was) - float(is_)) > 1e-9:
            out[key] = (was, is_)
            out['changed'] = True
    return out
