"""Reasons for and against a bet in plain words, so each pick explains itself (no Streamlit, so it can be tested).

Every reason is {'supports': True / False / None, 'text': str, 'flag': bool}: supports = for the picked side,
against it, or just context. A flag is a reason on its own to pass (too few games, may not play...).
"""
from typing import Dict, List

import numpy as np
import pandas as pd

MIN_GAMES = 8
POSITION_WORDS = {'G': 'guards', 'F': 'forwards', 'C': 'centers'}


def _reason(supports, text: str, flag: bool = False) -> Dict:
    # numpy comparisons give np.bool_, which `is True` doesn't match
    return {'supports': None if supports is None else bool(supports), 'text': text, 'flag': flag}


def _known(value) -> bool:
    return value is not None and not (isinstance(value, float) and np.isnan(value))


def prop_reasons(bet: Dict, games: pd.DataFrame, history: pd.DataFrame) -> List[Dict]:
    """Reasons for one prop pick.

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
    values = games[stat] if len(games) else pd.Series(dtype=float)
    n = len(values)
    reasons = []

    if _known(bet.get('edge pp')):
        reasons.append(_reason(
            bet['edge pp'] > 0,
            f"Model: {bet['side']} wins {bet['model %']:.0f}% of the time; odds {bet['odds']:.2f} need {be:.0f}% "
            f"(edge {bet['edge pp']:+.1f} pp, {bet['edge low']:+.1f} at the low end of the range)"))

    def hit_line(part: pd.Series, label: str):
        hits = int((part > line).sum() if over else (part < line).sum())
        rate = 100 * hits / len(part)
        reasons.append(_reason(rate > be, f"{bet['side']} in {hits} of {label} ({rate:.0f}%; needs {be:.0f}%)"))

    if n >= 3:
        hit_line(values.tail(10), f"the last {min(n, 10)} games")
    if n > 10:
        hit_line(values, f"all {n} games")

    if n:
        proj, avg = bet.get('proj avg', bet['avg']), bet['avg']
        diff = proj - line
        close = abs(diff) < max(0.5, 0.03 * line)
        reasons.append(_reason(None if close else favours(diff > 0),
                               f"Expected {proj:.1f} {stat} tonight vs the line {line:g} ({diff:+.1f}); "
                               f"average {avg:.1f}, median {values.median():.1f}"))

    if n >= 6:
        recent, usual = games['MIN'].tail(5).mean(), games['MIN'].mean()
        if abs(recent - usual) >= 3:
            reasons.append(_reason(favours(recent > usual),
                                   f"Minutes {'up' if recent > usual else 'down'} lately: {recent:.1f} per game in "
                                   f"the last 5 vs {usual:.1f}"))

    adj = bet.get('lineup adj', 0) or 0
    if adj and bet.get('out_names'):
        reasons.append(_reason(favours(adj > 0),
                               f"{', '.join(bet['out_names'])} out: {name} usually gets {adj:+.1f} {stat} "
                               f"without them"))

    if _known(bet.get('home')) and n >= 6:
        where = 'home' if bet['home'] else 'away'
        part = games.loc[games['type'] == where, stat]
        if len(part) >= 3 and n:
            avg = values.mean()
            gap = part.mean() - avg
            reasons.append(_reason(None if abs(gap) < 0.05 * max(avg, 1) else favours(gap > 0),
                                   f"{'At home' if bet['home'] else 'Away'}: {part.mean():.1f} in {len(part)} "
                                   f"{where} games ({avg:.1f} overall)"))

    if bet.get('rest_days') == 1:
        part = games.loc[games['rest_days'] == 1, stat] if 'rest_days' in games else pd.Series(dtype=float)
        detail = f": {part.mean():.1f} in {len(part)} such games ({values.mean():.1f} overall)" if len(part) >= 2 else ""
        higher = part.mean() > values.mean() if len(part) >= 2 else False
        reasons.append(_reason(favours(higher), f"Second night of a back-to-back{detail}"))

    m = bet.get('matchup') or {}
    if m:
        more = 'more' if m['diff'] > 0 else 'fewer'
        reasons.append(_reason(None if m['word'] == 'average' else favours(m['word'] == 'soft'),
                               f"{bet['opp'].upper()} allow {m['value']:.1f} {stat} per game to "
                               f"{POSITION_WORDS.get(bet.get('position'), 'this position')}, {abs(m['diff']):.1f} "
                               f"{more} than average (rank {m['rank']} of {m['teams']}, 1 = allows the most): "
                               f"{m['word']} matchup"))

    if len(history) >= 2:
        avg = history[stat].mean()
        reasons.append(_reason(favours(avg > line),
                               f"Against {bet['opp'].upper()}: {avg:.1f} {stat} in {len(history)} games (all stored "
                               f"seasons)"))

    implied, usual = bet.get('implied'), bet.get('team_pts')
    if _known(implied) and _known(usual) and usual:
        ratio = implied / usual
        if abs(ratio - 1) >= 0.03:
            reasons.append(_reason(favours(ratio > 1),
                                   f"Superbet expects {bet['team'].upper()} to score {implied:.0f} (usually "
                                   f"{usual:.0f}): a {'higher' if ratio > 1 else 'lower'}-scoring game than usual"))

    spread = bet.get('spread')
    if _known(spread) and abs(spread) >= 10 and bet.get('starter'):
        role = 'favoured' if spread < 0 else 'underdogs'
        reasons.append(_reason(favours(False),
                               f"{bet['team'].upper()} {role} by {abs(spread):g}: in a blowout starters sit out the "
                               f"fourth quarter"))

    move = bet.get('line_move')
    if _known(move) and move:
        # the line moving toward the pick (up for an Under, down for an Over) means the market agrees
        reasons.append(_reason(favours(move > 0),
                               f"The line moved {'up' if move > 0 else 'down'} {abs(move):g} since the first snapshot"
                               f" ({'the market moved your way' if favours(move > 0) else 'the market moved against you'})"))

    # reasons that alone mean "pass"
    if n < MIN_GAMES:
        reasons.append(_reason(False, f"Only {n} games in the sample: too few to trust the numbers", flag=True))
    if n and 'season_type' in games and (games['season_type'] == 'pre').all():
        reasons.append(_reason(False, "Every game is preseason: minutes and roles change in the regular season",
                               flag=True))
    pct = bet.get('play_pct')
    if _known(pct) and 0 < pct < 100:
        reasons.append(_reason(False, f"RotoWire: {bet.get('status')}: may sit or play limited minutes", flag=True))
    if n >= 5 and games['MIN'].mean() > 0 and games['MIN'].std() / games['MIN'].mean() > 0.35:
        reasons.append(_reason(False, f"Minutes swing a lot ({games['MIN'].min():.0f}–{games['MIN'].max():.0f}): "
                                      f"the role isn't settled", flag=True))
    if _known(move) and abs(move) >= 1.5 and not favours(move > 0):
        reasons.append(_reason(False, f"The line moved {abs(move):g} against the pick: the market may know something "
                                      f"(injury, minutes)", flag=True))
    return reasons


def game_reasons(outcome: Dict, ctx: Dict) -> List[Dict]:
    """Reasons for one game outcome (a row of metrics.market_edges).

    ctx: projection (game_projection), ratings (blended_ratings), home, away, absences ({team: [(name, impact)]}),
    home_court, games_played ({team: current-season games}), rotowire (bool: RotoWire lists the game).
    """
    p, r, home, away = ctx['projection'], ctx['ratings'], ctx['home'], ctx['away']
    market, side, line = outcome['market'], outcome['side'], outcome['line']
    reasons = [_reason(outcome['edge pp'] > 0,
                       f"Model: {outcome['model %']:.0f}% vs {outcome['implied %']:.0f}% implied by odds "
                       f"{outcome['odds']:.2f} (edge {outcome['edge pp']:+.1f} pp)")]
    league = r[['off_rtg', 'def_rtg', 'pace']].mean()
    if market in ('ML', 'SPREAD'):
        team, opp = (home, away) if side == 'home' else (away, home)
        margin = p['margin'] if side == 'home' else -p['margin']
        cover = margin + (line if market == 'SPREAD' and pd.notna(line) else 0)
        what = f"wins by {margin:.1f}" if margin >= 0 else f"loses by {-margin:.1f}"
        reasons.append(_reason(cover > 0, f"Projection: {team.upper()} {what}"
                               + (f", {'covering' if cover > 0 else 'missing'} {line:+g} by {abs(cover):.1f}"
                                  if market == 'SPREAD' and pd.notna(line) else "")))
        net = lambda t: r.loc[t, 'off_rtg'] - r.loc[t, 'def_rtg']
        reasons.append(_reason(net(team) > net(opp),
                               f"Net rating {team.upper()} {net(team):+.1f} vs {opp.upper()} {net(opp):+.1f} points "
                               f"per 100 possessions"))
        reasons.append(_reason(team == home, f"Home court: {home.upper()} +{ctx['home_court']:g} points"))
        for t in (team, opp):
            for name, imp in ctx['absences'].get(t, []):
                swing = imp['pts_for'] - imp['pts_against']
                if imp['n_without'] and abs(swing) >= 0.5:
                    helps = (swing > 0) == (t == team)
                    reasons.append(_reason(helps, f"{t.upper()} without {name}: {swing:+.1f} point margin per game "
                                                  f"({imp['n_without']} games missed)"))
    else:
        over = side == 'over'
        expected = {'TOTAL': p['total'], 'HOME_TOTAL': p['home_pts'], 'AWAY_TOTAL': p['away_pts']}[market]
        gap = expected - line
        reasons.append(_reason(gap > 0 if over else gap < 0,
                               f"Projected {expected:.1f} points vs the line {line:g} ({gap:+.1f})"))
        faster = p['pace'] - league['pace']
        reasons.append(_reason(None if abs(faster) < 1 else (faster > 0) == over,
                               f"Pace {p['pace']:.1f} possessions vs league {league['pace']:.1f}: a "
                               f"{'faster' if p['pace'] > league['pace'] else 'slower'} game than average"))
        teams = {'TOTAL': (home, away), 'HOME_TOTAL': (home,), 'AWAY_TOTAL': (away,)}[market]
        for t in teams:
            opp = away if t == home else home
            attack = r.loc[t, 'off_rtg'] - league['off_rtg'] + r.loc[opp, 'def_rtg'] - league['def_rtg']
            reasons.append(_reason(None if abs(attack) < 1 else (attack > 0) == over,
                                   f"{t.upper()} offense {r.loc[t, 'off_rtg']:.1f} vs {opp.upper()} defense "
                                   f"{r.loc[opp, 'def_rtg']:.1f} (league {league['off_rtg']:.1f}): "
                                   f"{attack:+.1f} per 100 possessions"))
        for t in (home, away):
            for name, imp in ctx['absences'].get(t, []):
                change = imp['pts_for'] + imp['pts_against'] if market == 'TOTAL' else \
                    imp['pts_for'] if t in teams else imp['pts_against']
                if imp['n_without'] and abs(change) >= 0.5:
                    reasons.append(_reason((change > 0) == over,
                                           f"{t.upper()} without {name}: {change:+.1f} points ({imp['n_without']} "
                                           f"games missed)"))

    if min(ctx['games_played'].get(t, 0) for t in (home, away)) < 5:
        reasons.append(_reason(False, "Early season: the ratings are still mostly last season's, which don't know "
                                      "about summer trades", flag=True))
    if not ctx['rotowire']:
        reasons.append(_reason(False, "RotoWire doesn't list this game yet: absences aren't in the projection",
                               flag=True))
    if outcome['edge pp'] > 15:
        reasons.append(_reason(False, "Edge over 15 pp: more likely the model is missing something (a trade, rest) "
                                      "than the market being that wrong", flag=True))
    return reasons


def verdict(reasons: List[Dict], edge_pp: float, edge_low: float = np.nan):
    """('Bet' / 'Lean' / 'Pass', colour, why). Any flag means Pass. Bet needs the low end of the edge above 0
    (or, without a range, an edge of 5+ pp) and more reasons for than against; Lean a positive edge and at least
    as many reasons for as against."""
    flags = [r for r in reasons if r['flag']]
    pros = sum(r['supports'] is True for r in reasons)
    cons = sum(r['supports'] is False and not r['flag'] for r in reasons)
    if flags:
        return 'Pass', 'red', flags[0]['text']
    if pd.isna(edge_pp) or edge_pp <= 0:
        return 'Pass', 'gray', "The price doesn't pay enough for the chance"
    holds = edge_low > 0 if pd.notna(edge_low) else edge_pp >= 5
    if holds and pros > cons:
        return 'Bet', 'green', f"The edge holds even at the low end, and {pros} reasons for vs {cons} against"
    if pros >= cons:
        return 'Lean', 'orange', (f"Positive edge, {pros} reasons for vs {cons} against, but the range still reaches "
                                  f"below break-even" if not holds else f"{pros} reasons for vs {cons} against")
    return 'Pass', 'gray', f"Positive edge, but more reasons against ({cons}) than for ({pros})"
