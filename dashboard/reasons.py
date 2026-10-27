"""Reasons for and against a bet in plain words, so each pick explains itself (no Streamlit, so it can be tested).

Every reason is {'supports': True / False / None, 'text': str, 'flag': bool}: supports = for the picked side,
against it, or just context. A flag is a reason on its own to pass (too few games, may not play...).
"""
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

import i18n

MIN_GAMES = 8


def _reason(supports, text: str, flag: bool = False) -> Dict:
    # numpy comparisons give np.bool_, which `is True` doesn't match
    return {'supports': None if supports is None else bool(supports), 'text': text, 'flag': flag}


def _known(value) -> bool:
    return value is not None and not (isinstance(value, float) and np.isnan(value))


def prop_reasons(bet: Dict, games: pd.DataFrame, history: pd.DataFrame, lang: str = 'en') -> List[Dict]:
    """Reasons for one prop pick, worded in `lang` (i18n.TEXTS 'reason.*' and 'flag.*').

    bet: name, stat, side ('Over'/'Under'), line, odds, model %, break-even %, edge pp, edge low, avg, proj avg,
    lineup adj, out_names, status (RotoWire text), play_pct, home (bool), rest_days (tonight), opp, team,
    matchup (metrics.matchup dict), position, implied (team's implied total), team_pts (team's usual points),
    spread (the team's handicap, negative = favourite), starter, line_move (the line's change since the first
    snapshot, + = up).
    games: the player's games in the chosen seasons, oldest first. history: every stored game against the opponent.
    """
    over = bet['side'] == 'Over'
    favours = lambda higher: higher if over else not higher   # does "the number is higher" help the pick?
    stat, line, be, name = bet['stat'], bet['line'], bet['break-even %'], bet['name']
    side = i18n.value(bet['side'], lang)
    values = games[stat] if len(games) else pd.Series(dtype=float)
    n = len(values)
    reasons = []

    if _known(bet.get('edge pp')):
        reasons.append(_reason(bet['edge pp'] > 0, i18n.t('reason.model', lang, side=side, model=bet['model %'],
                                                     odds=bet['odds'], be=be, edge=bet['edge pp'],
                                                     low=bet['edge low'])))

    def hit_line(part: pd.Series, label: str):
        hits = int((part > line).sum() if over else (part < line).sum())
        rate = 100 * hits / len(part)
        reasons.append(_reason(rate > be, i18n.t('reason.hits', lang, side=side, hits=hits, label=label, rate=rate,
                                            be=be)))

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
                                 median=values.median())))

    if n >= 6:
        recent, usual = games['MIN'].tail(5).mean(), games['MIN'].mean()
        if abs(recent - usual) >= 3:
            reasons.append(_reason(favours(recent > usual),
                                   i18n.t('reason.minutes_up' if recent > usual else 'reason.minutes_down', lang,
                                     recent=recent, usual=usual)))

    adj = bet.get('lineup adj', 0) or 0
    if adj and bet.get('out_names'):
        reasons.append(_reason(favours(adj > 0), i18n.t('reason.teammates', lang, names=', '.join(bet['out_names']),
                                                   name=name, adj=adj, stat=stat)))

    if _known(bet.get('home')) and n >= 6:
        where = 'home' if bet['home'] else 'away'
        part = games.loc[games['type'] == where, stat]
        if len(part) >= 3 and n:
            avg = values.mean()
            gap = part.mean() - avg
            reasons.append(_reason(None if abs(gap) < 0.05 * max(avg, 1) else favours(gap > 0),
                                   i18n.t('reason.home' if bet['home'] else 'reason.away', lang, value=part.mean(),
                                     n=len(part), avg=avg)))

    if bet.get('rest_days') == 1:
        part = games.loc[games['rest_days'] == 1, stat] if 'rest_days' in games else pd.Series(dtype=float)
        detail = i18n.t('reason.b2b_detail', lang, value=part.mean(), n=len(part), avg=values.mean()) \
            if len(part) >= 2 else ""
        higher = part.mean() > values.mean() if len(part) >= 2 else False
        reasons.append(_reason(favours(higher), i18n.t('reason.b2b', lang) + detail))

    m = bet.get('matchup') or {}
    if m:
        position = bet.get('position') if bet.get('position') in ('G', 'F', 'C') else ''
        reasons.append(_reason(None if m['word'] == 'average' else favours(m['word'] == 'soft'),
                               i18n.t('reason.matchup', lang, opp=bet['opp'].upper(), value=m['value'], stat=stat,
                                 position=i18n.t(f'reason.position.{position}', lang), diff=abs(m['diff']),
                                 more=i18n.t('reason.more' if m['diff'] > 0 else 'reason.fewer', lang), rank=m['rank'],
                                 teams=m['teams'], word=i18n.value(m['word'], lang))))

    if len(history) >= 2:
        avg = history[stat].mean()
        reasons.append(_reason(favours(avg > line), i18n.t('reason.vs_opp', lang, opp=bet['opp'].upper(), avg=avg,
                                                      stat=stat, n=len(history))))

    implied, usual = bet.get('implied'), bet.get('team_pts')
    if _known(implied) and _known(usual) and usual:
        ratio = implied / usual
        if abs(ratio - 1) >= 0.03:
            reasons.append(_reason(favours(ratio > 1),
                                   i18n.t('reason.implied_higher' if ratio > 1 else 'reason.implied_lower', lang,
                                     team=bet['team'].upper(), implied=implied, usual=usual)))

    spread = bet.get('spread')
    if _known(spread) and abs(spread) >= 10 and bet.get('starter'):
        reasons.append(_reason(favours(False),
                               i18n.t('reason.blowout_favoured' if spread < 0 else 'reason.blowout_underdogs', lang,
                                 team=bet['team'].upper(), spread=abs(spread))))

    move = bet.get('line_move')
    if _known(move) and move:
        # the line moving toward the pick (up for an Under, down for an Over) means the market agrees
        key = f"reason.line_{'up' if move > 0 else 'down'}_{'with' if favours(move > 0) else 'against'}"
        reasons.append(_reason(favours(move > 0), i18n.t(key, lang, move=abs(move))))

    # reasons that alone mean "pass" (the tables show them as 🔴)
    preseason_only = bool(n and 'season_type' in games and (games['season_type'] == 'pre').all())
    minutes = games['MIN'] if n else pd.Series(dtype=float)
    reasons += [_reason(False, text, flag=True) for text in
                prop_flags(n, preseason_only, bet.get('play_pct'), bet.get('status'), minutes, move, bet['side'],
                           lang)]
    return reasons


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
    (pass). logs: the games the lines were priced from; lineups: RotoWire's (with ESPN ids)."""
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
                                     games['MIN'] if n else empty, row.get('line move'), row['best side']))
    flags = pd.Series(['; '.join(flag_texts(i)) for i in items], index=table.index)
    out = table.assign(**{'red flag': flags, 'flag items': pd.Series(items, index=table.index, dtype=object),
                          'signal': table['signal'].where(flags == '', '🔴')})
    if 'bet' in out:
        out['bet'] = out['bet'].where(flags == '', '')
    return out


def game_reasons(outcome: Dict, ctx: Dict, lang: str = 'en') -> List[Dict]:
    """Reasons for one game outcome (a row of metrics.market_edges), worded in `lang` (i18n 'game.*').

    ctx: projection (game_projection), ratings (blended_ratings), home, away, absences ({team: [(name, impact)]}),
    home_court, games_played ({team: current-season games}), rotowire (bool: RotoWire lists the game).
    """
    p, r, home, away = ctx['projection'], ctx['ratings'], ctx['home'], ctx['away']
    market, side, line = outcome['market'], outcome['side'], outcome['line']
    reasons = [_reason(outcome['edge pp'] > 0,
                       i18n.t('game.model', lang, model=outcome['model %'], implied=outcome['implied %'],
                              odds=outcome['odds'], edge=outcome['edge pp']))]
    league = r[['off_rtg', 'def_rtg', 'pace']].mean()
    if market in ('ML', 'SPREAD'):
        team, opp = (home, away) if side == 'home' else (away, home)
        margin = p['margin'] if side == 'home' else -p['margin']
        cover = margin + (line if market == 'SPREAD' and pd.notna(line) else 0)
        what = i18n.t('game.wins_by' if margin >= 0 else 'game.loses_by', lang, margin=abs(margin))
        spread_part = i18n.t('game.covering' if cover > 0 else 'game.missing', lang, line=line, gap=abs(cover)) \
            if market == 'SPREAD' and pd.notna(line) else ""
        reasons.append(_reason(cover > 0, i18n.t('game.projection', lang, team=team.upper(), what=what) + spread_part))
        net = lambda tm: r.loc[tm, 'off_rtg'] - r.loc[tm, 'def_rtg']
        reasons.append(_reason(net(team) > net(opp), i18n.t('game.net', lang, team=team.upper(), net=net(team),
                                                            opp=opp.upper(), opp_net=net(opp))))
        reasons.append(_reason(team == home, i18n.t('game.home_court', lang, home=home.upper(),
                                                    points=ctx['home_court'])))
        for tm in (team, opp):
            for name, imp in ctx['absences'].get(tm, []):
                swing = imp['pts_for'] - imp['pts_against']
                if imp['n_without'] and abs(swing) >= 0.5:
                    helps = (swing > 0) == (tm == team)
                    reasons.append(_reason(helps, i18n.t('game.absence_margin', lang, team=tm.upper(), name=name,
                                                         swing=swing, n=imp['n_without'])))
    else:
        over = side == 'over'
        expected = {'TOTAL': p['total'], 'HOME_TOTAL': p['home_pts'], 'AWAY_TOTAL': p['away_pts']}[market]
        gap = expected - line
        reasons.append(_reason(gap > 0 if over else gap < 0,
                               i18n.t('game.projected_total', lang, expected=expected, line=line, gap=gap)))
        faster = p['pace'] - league['pace']
        reasons.append(_reason(None if abs(faster) < 1 else (faster > 0) == over,
                               i18n.t('game.pace_faster' if p['pace'] > league['pace'] else 'game.pace_slower', lang,
                                      pace=p['pace'], league=league['pace'])))
        teams = {'TOTAL': (home, away), 'HOME_TOTAL': (home,), 'AWAY_TOTAL': (away,)}[market]
        for tm in teams:
            opp = away if tm == home else home
            attack = r.loc[tm, 'off_rtg'] - league['off_rtg'] + r.loc[opp, 'def_rtg'] - league['def_rtg']
            reasons.append(_reason(None if abs(attack) < 1 else (attack > 0) == over,
                                   i18n.t('game.attack', lang, team=tm.upper(), off=r.loc[tm, 'off_rtg'],
                                          opp=opp.upper(), defense=r.loc[opp, 'def_rtg'], league=league['off_rtg'],
                                          attack=attack)))
        for tm in (home, away):
            for name, imp in ctx['absences'].get(tm, []):
                change = imp['pts_for'] + imp['pts_against'] if market == 'TOTAL' else \
                    imp['pts_for'] if tm in teams else imp['pts_against']
                if imp['n_without'] and abs(change) >= 0.5:
                    reasons.append(_reason((change > 0) == over,
                                           i18n.t('game.absence_points', lang, team=tm.upper(), name=name,
                                                  change=change, n=imp['n_without'])))

    played = min(ctx['games_played'].get(t, 0) for t in (home, away))
    reasons += [_reason(False, text, flag=True)
                for text in game_flags(outcome['edge pp'], played, ctx['rotowire'], lang)]
    return reasons


def game_flags(edge_pp: float, games_played: int, rotowire: bool, lang: str = 'en') -> List[str]:
    """The reasons to pass a game market whatever its numbers say. games_played: the fewer of the two teams'
    current-season games; rotowire: RotoWire lists the game."""
    keys = (['gameflag.early'] if games_played < 5 else []) + ([] if rotowire else ['gameflag.no_lineup']) \
        + (['gameflag.big_edge'] if edge_pp > 15 else [])
    return [i18n.t(key, lang) for key in keys]


def flag_game_outcomes(edges: pd.DataFrame, games_played: int, rotowire: bool, lang: str = 'en') -> pd.DataFrame:
    """metrics.market_edges rows of one game with 'red flag' (game_flags, joined) and 'signal': 🔴 when flagged,
    otherwise ''. The game model isn't calibrated (it was overconfident on the settled nights: see the game section
    of data/backtest/calibration.md), so its edges are estimates and never 🟢 / 🟡."""
    flags = pd.Series(['; '.join(game_flags(e, games_played, rotowire, lang)) for e in edges['edge pp']],
                      index=edges.index)
    signal = np.where(flags != '', '🔴', '')
    return edges.assign(signal=signal, **{'red flag': flags})


def verdict(reasons: List[Dict], edge_pp: float, edge_low: float = np.nan, lang: str = 'en'):
    """('Bet' / 'Lean' / 'Pass', colour, why in `lang`). The word stays English (show it with
    i18n.t('verdict.<word>')). Any flag means Pass. Bet needs a strong edge and more reasons for than against; Lean
    a positive edge and at least as many reasons for as against. Strong: the 🟢 threshold (models.load_green_edge;
    none = never). Only props (they have an edge low) with a calibration fitted for the current model get past
    Pass: a game outcome's chance comes from an uncalibrated model."""
    from models import FITTED, calibration_status, load_green_edge
    flags = [r for r in reasons if r['flag']]
    pros = sum(r['supports'] is True for r in reasons)
    cons = sum(r['supports'] is False and not r['flag'] for r in reasons)
    if flags:
        return 'Pass', 'red', flags[0]['text']
    if pd.isna(edge_low):
        return 'Pass', 'gray', i18n.t('verdict.game', lang)
    if calibration_status() != FITTED:
        return 'Pass', 'gray', i18n.t('verdict.no_calibration', lang)
    if pd.isna(edge_pp) or edge_pp <= 0:
        return 'Pass', 'gray', i18n.t('verdict.no_value', lang)
    green = load_green_edge()
    strong = green is not None and edge_pp >= green
    if strong and pros > cons:
        return 'Bet', 'green', i18n.t('verdict.strong', lang, pros=pros, cons=cons)
    if pros >= cons:
        return 'Lean', 'orange', i18n.t('verdict.lean' if strong else 'verdict.lean_unproven', lang, pros=pros,
                                        cons=cons)
    return 'Pass', 'gray', i18n.t('verdict.more_against', lang, pros=pros, cons=cons)
