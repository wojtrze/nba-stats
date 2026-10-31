"""Reasons for and against an offer in plain words (no Streamlit, so it can be tested). They're written after the
decision (decisions.py) and explain it: how many there are never changes it.

Every reason is {'supports': True / False / None, 'direction': 'for' / 'against' / None, 'text', 'flag', 'value',
'reference', 'n', 'as_of', 'source'}: for the evaluated side, against it, or context; the value and what it's
compared with, how many observations it rests on, how recent they are and where they come from. A reason without
its data (no value, no reference, no observations, no time or no source) isn't made. A flag is a warning that keeps
an offer from OBSTAW (too few games, may not play...).
"""
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

import i18n

MIN_GAMES = 8
ESPN, SUPERBET, ROTOWIRE, MODEL = 'ESPN', 'Superbet', 'RotoWire', 'model'


def _known(value) -> bool:
    return value is not None and not (isinstance(value, float) and np.isnan(value)) and value is not pd.NaT


def _reason(supports, text: str, flag: bool = False, value=None, reference=None, n=None, as_of=None,
            source=None) -> Dict:
    # numpy comparisons give np.bool_, which `is True` doesn't match
    supports = None if supports is None else bool(supports)
    return {'supports': supports, 'direction': None if supports is None else 'for' if supports else 'against',
            'text': text, 'flag': flag, 'value': value, 'reference': reference, 'n': n, 'as_of': as_of,
            'source': source}


def complete(reason: Dict) -> bool:
    """A reason has everything it must show: value, reference, observations (1+), time and source. Flags are
    warnings, not arguments, and are always kept."""
    if reason['flag']:
        return True
    n = reason['n']
    return (all(_known(reason[k]) for k in ('value', 'reference', 'as_of', 'source'))
            and _known(n) and n >= 1)


def _last(dates) -> object:
    """The newest date in a column of game dates (the data a stats reason rests on is that recent)."""
    if dates is None or len(dates) == 0:
        return None
    return pd.to_datetime(pd.Series(dates)).max()


def prop_reasons(bet: Dict, games: pd.DataFrame, history: pd.DataFrame, lang: str = 'en') -> List[Dict]:
    """Reasons about one offer's evaluated side, worded in `lang` (i18n.TEXTS 'reason.*' and 'flag.*').

    bet: name, stat, side (the evaluated side, 'Over' / 'Under'), line, odds, model % (its chance to win),
    break-even % and edge pp (after the cost profile's stake tax), avg, proj avg, lineup adj, out_names, out_n (the
    fewest games the player played without one of them), status (RotoWire text), play_pct, home (bool), rest_days
    (tonight), opp, team, matchup (metrics.matchup dict), position, implied (team's implied total), team_pts (team's
    usual points) and team_games (the games behind it), spread (the team's handicap, negative = favourite),
    starter, line_move and open_line (the line's change since the first snapshot, + = up, and that first line),
    snapshots (how many fetches saw the line), odds_at (when the odds were fetched), stats_through (the newest game
    in the stats), lineup_at (when RotoWire was fetched).
    games: the player's games in the chosen seasons, oldest first. history: every stored game against the opponent.
    """
    over = bet['side'] == 'Over'
    favours = lambda higher: higher if over else not higher   # does "the number is higher" help the side?
    stat, line, be, name = bet['stat'], bet['line'], bet['break-even %'], bet['name']
    side = i18n.value(bet['side'], lang)
    values = games[stat] if len(games) else pd.Series(dtype=float)
    n = len(values)
    played_through = _last(games['Date']) if n and 'Date' in games else bet.get('stats_through')
    odds_at = bet.get('odds_at')
    reasons = []

    if _known(bet.get('edge pp')):
        reasons.append(_reason(bet['edge pp'] > 0, i18n.t('reason.model', lang, side=side, model=bet['model %'],
                                                          odds=bet['odds'], be=be, edge=bet['edge pp']),
                               value=bet['model %'], reference=be, n=n, as_of=odds_at, source=f"{MODEL} · {SUPERBET}"))

    def hit_line(part: pd.Series, label: str):
        hits = int((part > line).sum() if over else (part < line).sum())
        rate = 100 * hits / len(part)
        reasons.append(_reason(rate > be, i18n.t('reason.hits', lang, side=side, hits=hits, label=label, rate=rate,
                                                 be=be), value=rate, reference=be, n=len(part),
                               as_of=played_through, source=ESPN))

    if n >= 3:
        hit_line(values.tail(10), i18n.t('reason.last_games', lang, n=min(n, 10)))
    if n > 10:
        hit_line(values, i18n.t('reason.all_games', lang, n=n))

    if n:
        proj, avg = bet.get('proj avg', bet['avg']), bet['avg']
        diff = proj - line
        close = abs(diff) < max(0.5, 0.03 * line)
        reasons.append(_reason(None if close else favours(diff > 0),
                               i18n.t('reason.expected', lang, proj=proj, stat=stat, line=line, diff=diff, avg=avg,
                                      median=values.median()),
                               value=proj, reference=line, n=n, as_of=played_through, source=f"{MODEL} · {ESPN}"))

    if n >= 6:
        recent, usual = games['MIN'].tail(5).mean(), games['MIN'].mean()
        if abs(recent - usual) >= 3:
            reasons.append(_reason(favours(recent > usual),
                                   i18n.t('reason.minutes_up' if recent > usual else 'reason.minutes_down', lang,
                                          recent=recent, usual=usual),
                                   value=recent, reference=usual, n=n, as_of=played_through, source=ESPN))

    adj = bet.get('lineup adj', 0) or 0
    if adj and bet.get('out_names'):
        reasons.append(_reason(favours(adj > 0), i18n.t('reason.teammates', lang, names=', '.join(bet['out_names']),
                                                        name=name, adj=adj, stat=stat),
                               value=bet['avg'] + adj, reference=bet['avg'], n=bet.get('out_n'),
                               as_of=bet.get('lineup_at'), source=f"{ROTOWIRE} · {ESPN}"))

    if _known(bet.get('home')) and n >= 6:
        where = 'home' if bet['home'] else 'away'
        part = games.loc[games['type'] == where, stat]
        if len(part) >= 3:
            avg = values.mean()
            gap = part.mean() - avg
            reasons.append(_reason(None if abs(gap) < 0.05 * max(avg, 1) else favours(gap > 0),
                                   i18n.t('reason.home' if bet['home'] else 'reason.away', lang, value=part.mean(),
                                          n=len(part), avg=avg),
                                   value=part.mean(), reference=avg, n=len(part), as_of=played_through, source=ESPN))

    if bet.get('rest_days') == 1 and 'rest_days' in games:
        part = games.loc[games['rest_days'] == 1, stat]
        # a back-to-back reason needs back-to-back games to rest on; without them there's nothing to say
        if len(part) >= 2:
            reasons.append(_reason(favours(part.mean() > values.mean()),
                                   i18n.t('reason.b2b', lang) + i18n.t('reason.b2b_detail', lang, value=part.mean(),
                                                                       n=len(part), avg=values.mean()),
                                   value=part.mean(), reference=values.mean(), n=len(part), as_of=played_through,
                                   source=ESPN))

    m = bet.get('matchup') or {}
    if m:
        position = bet.get('position') if bet.get('position') in ('G', 'F', 'C') else ''
        reasons.append(_reason(None if m['word'] == 'average' else favours(m['word'] == 'soft'),
                               i18n.t('reason.matchup', lang, opp=bet['opp'].upper(), value=m['value'], stat=stat,
                                      position=i18n.t(f'reason.position.{position}', lang), diff=abs(m['diff']),
                                      more=i18n.t('reason.more' if m['diff'] > 0 else 'reason.fewer', lang),
                                      rank=m['rank'], teams=m['teams'], word=i18n.value(m['word'], lang)),
                               value=m['value'], reference=m['average'], n=m.get('games'),
                               as_of=bet.get('stats_through') or played_through, source=ESPN))

    if len(history) >= 2:
        avg = history[stat].mean()
        reasons.append(_reason(favours(avg > line), i18n.t('reason.vs_opp', lang, opp=bet['opp'].upper(), avg=avg,
                                                           stat=stat, n=len(history)),
                               value=avg, reference=line, n=len(history),
                               as_of=_last(history['Date']) if 'Date' in history else None, source=ESPN))

    implied, usual = bet.get('implied'), bet.get('team_pts')
    if _known(implied) and _known(usual) and usual:
        ratio = implied / usual
        if abs(ratio - 1) >= 0.03:
            reasons.append(_reason(favours(ratio > 1),
                                   i18n.t('reason.implied_higher' if ratio > 1 else 'reason.implied_lower', lang,
                                          team=bet['team'].upper(), implied=implied, usual=usual),
                                   value=implied, reference=usual, n=bet.get('team_games'), as_of=odds_at,
                                   source=f"{SUPERBET} · {ESPN}"))

    spread = bet.get('spread')
    if _known(spread) and abs(spread) >= 10 and bet.get('starter'):
        reasons.append(_reason(favours(False),
                               i18n.t('reason.blowout_favoured' if spread < 0 else 'reason.blowout_underdogs', lang,
                                      team=bet['team'].upper(), spread=abs(spread)),
                               value=spread, reference=10, n=1, as_of=odds_at, source=SUPERBET))

    move = bet.get('line_move')
    if _known(move) and move:
        # where the market went is context: it isn't by itself a reason for (or against) the offer as it is now
        reasons.append(_reason(None, i18n.t('reason.line_moved', lang, move=move, open=bet.get('open_line', np.nan),
                                            line=line),
                               value=line, reference=bet.get('open_line'), n=bet.get('snapshots'), as_of=odds_at,
                               source=SUPERBET))

    # warnings: an offer with one can't get OBSTAW (the tables show them as 🔴)
    preseason_only = bool(n and 'season_type' in games and (games['season_type'] == 'pre').all())
    minutes = games['MIN'] if n else pd.Series(dtype=float)
    reasons += [_reason(False, text, flag=True) for text in
                prop_flags(n, preseason_only, bet.get('play_pct'), bet.get('status'), minutes, move, bet['side'],
                           lang)]
    return [r for r in reasons if complete(r)]


def prop_flag_items(n: int, preseason_only: bool, play_pct, status, minutes: pd.Series, line_move,
                    side) -> List[Tuple[str, Dict]]:
    """The reasons to pass a prop whatever its numbers say, as (i18n text key, values): too few games, preseason
    only, may not play, unstable minutes, the line moving against the pick. minutes: the player's minutes in the
    games behind the numbers."""
    items = []
    if n < MIN_GAMES:
        items.append(('flag.few_games', {'n': n}))
    if preseason_only:
        items.append(('flag.preseason', {}))
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
                       value=outcome['model %'], reference=be, n=played, as_of=odds_at, source=f"{MODEL} · {SUPERBET}")]
    league = r[['off_rtg', 'def_rtg', 'pace']].mean()
    rated = dict(n=played, as_of=through, source=f"{MODEL} · {ESPN}")
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
                                           source=f"{ROTOWIRE} · {ESPN}"))
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
                                           source=f"{ROTOWIRE} · {ESPN}"))

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
