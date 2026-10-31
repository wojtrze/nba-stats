import pandas as pd
import streamlit as st

from components import decision_text, decision_times, reasons_panel
from core.data import game_model, lineups as rotowire_lineups, player_decisions, priced_games, priced_props, superbet
from decisions import team_decision
from core.columns import GAMES_ABSENCES, GAMES_MARKETS, GAMES_SUMMARY
from core.labels import MARKET_LABELS, describe_outcome, market_label, winner
from core.state import language, scope
from core.ui import PAGES, go_to_data, kpis, no_offers, page_header, pl_time, stop, table
from espn_scraper import CURRENT_SEASON
from i18n import t, value
from loaders import season_label, snapshot_history
from models import GAME_DEFAULTS
from reasons import flag_game_outcomes, game_reasons
from tracking import opening_game_lines

lang = language()
page_header(t('games.title', lang), t('games.purpose', lang))

with st.popover(t('games.settings', lang)):
    s = st.columns(2)
    prior_games = s[0].number_input(t('games.prior', lang), 0, 82, GAME_DEFAULTS['prior_games'],
                                    help=t('games.prior_help', lang))
    regress = s[1].slider(t('games.regress', lang), 0.0, 1.0, GAME_DEFAULTS['regress'], 0.1,
                          help=t('games.regress_help', lang))
    home_court = s[0].number_input(t('games.home_court', lang), 0.0, 6.0, GAME_DEFAULTS['home_court'], 0.5,
                                   help=t('games.home_court_help', lang))
    shrink = s[1].number_input(t('games.shrink', lang), 0, 30, GAME_DEFAULTS['shrink'],
                               help=t('games.shrink_help', lang))
    out_max = s[0].selectbox(t('games.out_max', lang), [0, 25, 50], index=1,
                             format_func=lambda v: t('games.out_max_value', lang, pct=v),
                             help=t('games.out_max_help', lang))
    all_lines = s[1].toggle(t('games.every_line', lang), help=t('games.every_line_help', lang))

if superbet()['status']['state'] != 'available':
    no_offers(superbet()['status'])
    stop()
priced = priced_games(prior_games, regress, home_court, shrink, out_max, all_lines)
if not priced:
    go_to_data(t('games.none', lang))
    stop()

model = game_model(prior_games, regress)
ratings = model['ratings']
lineups = rotowire_lineups()
names = model['logs'].groupby('player_id_ESPN')['player_display_name'].last()
opening = opening_game_lines(snapshot_history('superbet_game_odds'))
st.caption(t('games.ratings', lang, current=season_label(CURRENT_SEASON), n_current=model['current'],
             prior=season_label(CURRENT_SEASON - 1), n_prior=model['prior']))

priced = sorted(priced, key=lambda g: pd.Timestamp(g['start_time']))   # earliest tip-off first
odds_at = superbet()['fetched_at']
decided = player_decisions(priced_props(*scope())) if not superbet()['props'].empty else {}
rows = []
for g in priced:
    played = min(ratings['games'].get(g['home'], 0), ratings['games'].get(g['away'], 0))
    g['edges'] = flag_game_outcomes(g['edges'], played, g['home'] in set(lineups['team']), lang)
    p = g['projection']
    players = decided.get(g['event_id'])
    rows.append({'event_id': g['event_id'], 'game': f"{g['away'].upper()} @ {g['home'].upper()}",
                 'start (PL)': pl_time(g['start_time']),
                 'decision': t(f"decision.{team_decision(g)['status']}", lang),
                 'players': t(f"decision.{players['status']}", lang) if players else '',
                 'proj score': f"{p['away_pts']:.0f} – {p['home_pts']:.0f}",
                 'proj winner': winner(p, g['home'], g['away'], lang),
                 'proj total': p['total'], 'RotoWire': '✔' if g['home'] in set(lineups['team']) else ''})
summary = pd.DataFrame(rows)
picked = table(summary, GAMES_SUMMARY, {'proj total': '%.1f'}, key='games_table', select=True,
               legend=['superbet', 'stats'], context='games')

focus = st.session_state.get('games_focus')
if picked is not None:
    st.session_state.pop('games_focus', None)
    event_id = summary.iloc[picked]['event_id']
elif focus in set(summary['event_id']):
    event_id = focus
else:
    event_id = summary['event_id'].iloc[0]
    st.caption(t('games.pick_game', lang))
game = next(g for g in priced if g['event_id'] == event_id)
home, away, p, edges = game['home'], game['away'], game['projection'], game['edges']

with st.container(border=True):
    st.markdown(f"### {away.upper()} @ {home.upper()} · {pl_time(game['start_time'])}")
    team = team_decision(game, odds_at)
    st.markdown(f"**{t('decision.teams', lang)}:** {decision_text(team, lang)}")
    if decided.get(event_id):
        st.markdown(f"**{t('decision.players', lang)}:** {decision_text(decided[event_id], lang)}")
        st.caption(decision_times(decided[event_id], lang))
    kpis([{'label': t('games.kpi.winner', lang), 'value': winner(p, home, away, lang),
           'help': t('games.kpi.winner_help', lang, margin=p['margin'])},
          {'label': t('games.kpi.total', lang), 'value': f"{p['total']:.1f}"},
          {'label': t('games.kpi.points', lang, team=away.upper()), 'value': f"{p['away_pts']:.1f}"},
          {'label': t('games.kpi.points', lang, team=home.upper()), 'value': f"{p['home_pts']:.1f}",
           'help': t('games.kpi.points_help', lang)}])
    if event_id in opening.index:
        o = opening.loc[event_id]
        st.caption(t('games.opening', lang, home=home.upper(), spread=o['home_spread'], total=o['total']))

    markets_tab, teams_tab = st.tabs([t('games.tab.markets', lang), t('games.tab.teams', lang)])
    with markets_tab:
        rows_ = edges.assign(order=edges['market'].map(list(MARKET_LABELS).index),
                             market=edges['market'].map(lambda m: market_label(m, lang)),
                             team=edges['team'].fillna('').str.upper(),
                             side=edges['side'].map(lambda v: value(v, lang)))
        rows_ = rows_.sort_values(['order', 'line', 'side'])
        rows_['line'] = [('–' if pd.isna(v) else f"{v:+g}" if m == 'SPREAD' else f"{v:g}")
                         for v, m in zip(rows_['line'], edges.loc[rows_.index, 'market'])]
        st.caption(t('games.best_shown', lang))
        row = table(rows_, GAMES_MARKETS, {'market %': '%.0f', 'model %': '%.0f', 'fair odds': '%.2f',
                                           'odds': '%.2f', 'odds move': '%+.2f', 'break-even net %': '%.1f',
                                           'edge net pp': '%+.1f', 'ev net 100': '%+.1f'},
                    key=f"markets_{event_id}", select=True, context='games')
        # no outcome is picked for the user: the reasons open only for the row they choose
        if row is not None:
            outcome = edges.loc[rows_.index[row]]
            ctx = {'projection': p, 'ratings': ratings, 'home': home, 'away': away, 'home_court': home_court,
                   'absences': {tm: [(str(names.get(pid, pid)), imp) for pid, imp in game['absences'][tm]]
                                for tm in (home, away)},
                   'games_played': ratings['games'].to_dict(), 'rotowire': home in set(lineups['team']),
                   'odds_at': odds_at, 'stats_through': model['games']['date'].max()}
            reasons_panel(f"{describe_outcome(outcome, lang)} @ {outcome['odds']:.2f}", team,
                          game_reasons(outcome.to_dict(), ctx, lang), lang=lang)

    with teams_tab:
        cols = st.columns(2)
        for col, team, side in ((cols[0], away, t('games.away', lang)), (cols[1], home, t('games.home', lang))):
            with col:
                r = ratings.loc[team]
                st.markdown(t('games.team_line', lang, side=side, team=team.upper(), off=r['off_rtg'],
                              defense=r['def_rtg'], pace=r['pace']))
                listed = lineups[lineups['team'] == team]
                if listed.empty:
                    st.caption(t('games.not_listed', lang))
                else:
                    starters = listed[listed['role'] == 'starter']
                    status = listed['lineup_status'].iloc[0] or ''
                    status = t(f'overview.{status}', lang) if status in ('confirmed', 'expected') else status
                    st.caption(t('games.lineup', lang, status=status,
                                 players=", ".join(f"{x['pos']} {x['name']}" for _, x in starters.iterrows())))
                absences = pd.DataFrame([{'out': str(names.get(pid, pid)), 'games missed': imp['n_without'],
                                          'team pts change': imp['pts_for'], 'opp pts change': imp['pts_against']}
                                         for pid, imp in game['absences'][team]])
                if len(absences):
                    table(absences, GAMES_ABSENCES, {'team pts change': '%+.1f', 'opp pts change': '%+.1f',
                                                             'games missed': '%d'}, context='games')
                if st.button(t('games.open_lineup', lang, team=team.upper()), key=f"lab_{team}"):
                    st.session_state['lineup_team'] = team
                    st.switch_page(PAGES['lineup'])
