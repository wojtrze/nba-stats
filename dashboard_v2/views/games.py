import pandas as pd
import streamlit as st

from components import reasons_panel
from core.data import game_model, lineups as rotowire_lineups, priced_games, superbet
from core.labels import MARKET_LABELS, describe_outcome, winner
from core.ui import PAGES, go_to_data, kpis, no_offers, page_header, pl_time, stop, table
from espn_scraper import CURRENT_SEASON
from glossary import GAME_SIGNAL_TIP
from loaders import season_label, snapshot_history
from models import GAME_DEFAULTS
from reasons import flag_game_outcomes, game_reasons
from tracking import opening_game_lines

page_header("Games", "Superbet's moneyline, handicap and totals next to a team model: offensive and defensive "
                     "ratings, pace, home court and who RotoWire lists as out.")

with st.popover("Model settings"):
    s = st.columns(2)
    prior_games = s[0].number_input("Prior weight (games)", 0, 82, GAME_DEFAULTS['prior_games'],
                                    help="This season counts n / (n + this) against last season's ratings")
    regress = s[1].slider("Regress last season to average", 0.0, 1.0, GAME_DEFAULTS['regress'], 0.1,
                          help="Rosters change over the summer; 0 = use last season's ratings as they were")
    home_court = s[0].number_input("Home court (pts)", 0.0, 6.0, GAME_DEFAULTS['home_court'], 0.5,
                                   help="Points the home team gains from playing at home")
    shrink = s[1].number_input("Absence shrink", 0, 30, GAME_DEFAULTS['shrink'],
                               help="Each absence's effect is weighted by n / (n + shrink), n = games missed")
    out_max = s[0].selectbox("Count as out", [0, 25, 50], index=1, format_func=lambda v: f"≤ {v}% to play",
                             help="RotoWire players with at most this chance to play are treated as out")
    all_lines = s[1].toggle("Every line", help="Otherwise only Superbet's main line of each market")

if superbet()['status']['state'] != 'available':
    no_offers(superbet()['status'])
    stop()
priced = priced_games(prior_games, regress, home_court, shrink, out_max, all_lines)
if not priced:
    go_to_data("**Superbet has no NBA games in the next 36 hours**, or none could be priced. Fetch the offers "
               "again in the Data center.")
    stop()

model = game_model(prior_games, regress)
ratings = model['ratings']
lineups = rotowire_lineups()
names = model['logs'].groupby('player_id_ESPN')['player_display_name'].last()
opening = opening_game_lines(snapshot_history('superbet_game_odds'))
st.caption(f"Ratings: {season_label(CURRENT_SEASON)} ({model['current']} games) blended with "
           f"{season_label(CURRENT_SEASON - 1)} ({model['prior']} games). Superbet's margin is about 2–3 pp per "
           f"side, so small edges are noise.")

priced = sorted(priced, key=lambda g: pd.Timestamp(g['start_time']))   # earliest tip-off first
rows = []
for g in priced:
    played = min(ratings['games'].get(g['home'], 0), ratings['games'].get(g['away'], 0))
    g['edges'] = flag_game_outcomes(g['edges'], played, g['home'] in set(lineups['team']))
    best = g['edges'].loc[g['edges']['edge pp'].idxmax()]
    p = g['projection']
    rows.append({'event_id': g['event_id'], 'game': f"{g['away'].upper()} @ {g['home'].upper()}",
                 'start (PL)': pl_time(g['start_time']),
                 'proj score': f"{p['away_pts']:.0f} – {p['home_pts']:.0f}", 'proj winner': winner(p, g['home'], g['away']),
                 'proj total': p['total'], 'best bet': describe_outcome(best), 'signal': best['signal'],
                 'best edge pp': best['edge pp'],
                 'best odds': best['odds'], 'RotoWire': '✔' if g['home'] in set(lineups['team']) else ''})
summary = pd.DataFrame(rows)
picked = table(summary, ['game', 'start (PL)', 'proj winner', 'proj score', 'proj total', 'best bet', 'signal',
                         'best edge pp', 'best odds', 'RotoWire'],
               {'proj total': '%.1f', 'best edge pp': '%+.1f', 'best odds': '%.2f'},
               tips={'RotoWire': "✔ = RotoWire lists this game's lineups, so absences are in the projection",
                     'signal': "The best bet's signal: " + GAME_SIGNAL_TIP,
                     'best odds': "Superbet's odds for the best bet"},
               sources={'best odds': 'superbet'}, key='games_table', select=True, legend=['superbet', 'stats'])

focus = st.session_state.get('games_focus')
if picked is not None:
    st.session_state.pop('games_focus', None)
    event_id = summary.iloc[picked]['event_id']
elif focus in set(summary['event_id']):
    event_id = focus
else:
    event_id = summary['event_id'].iloc[0]
    st.caption("Pick a game for its markets; showing the first one.")
game = next(g for g in priced if g['event_id'] == event_id)
home, away, p, edges = game['home'], game['away'], game['projection'], game['edges']

with st.container(border=True):
    st.markdown(f"### {away.upper()} @ {home.upper()} · {pl_time(game['start_time'])}")
    kpis([{'label': "Projected winner", 'value': winner(p, home, away),
           'help': f"Home margin {p['margin']:+.1f}"},
          {'label': "Projected total", 'value': f"{p['total']:.1f}"},
          {'label': f"{away.upper()} points", 'value': f"{p['away_pts']:.1f}"},
          {'label': f"{home.upper()} points", 'value': f"{p['home_pts']:.1f}",
           'help': "Pace × (own ORtg + opponent's DRtg − league average) / 100, ± half the home-court edge, + the "
                   "effect of missing players"}])
    if event_id in opening.index:
        o = opening.loc[event_id]
        st.caption(f"Opening lines (first snapshot): {home.upper()} handicap {o['home_spread']:+g}, "
                   f"total {o['total']:g}")

    markets_tab, teams_tab = st.tabs(["Markets", "Teams & absences"])
    with markets_tab:
        t = edges.assign(order=edges['market'].map(list(MARKET_LABELS).index), market=edges['market'].map(MARKET_LABELS),
                         team=edges['team'].fillna('').str.upper())
        t = t.sort_values(['order', 'line', 'side'])
        t['line'] = [('–' if pd.isna(v) else f"{v:+g}" if m == 'Handicap' else f"{v:g}")
                     for v, m in zip(t['line'], t['market'])]
        cols = ['market', 'team', 'side', 'line', 'signal', 'edge pp', 'odds', 'odds move', 'implied %', 'model %',
                'fair odds', 'red flag']
        row = table(t, cols, {'implied %': '%.0f', 'model %': '%.0f', 'fair odds': '%.2f', 'odds': '%.2f',
                              'odds move': '%+.2f', 'edge pp': '%+.1f'},
                    tips={'signal': GAME_SIGNAL_TIP,
                          'edge pp': "model % − implied %, in percentage points"},
                    key=f"markets_{event_id}", select=True)
        outcome = edges.loc[t.index[row]] if row is not None else edges.loc[edges['edge pp'].idxmax()]
        ctx = {'projection': p, 'ratings': ratings, 'home': home, 'away': away, 'home_court': home_court,
               'absences': {tm: [(str(names.get(pid, pid)), imp) for pid, imp in game['absences'][tm]]
                            for tm in (home, away)},
               'games_played': ratings['games'].to_dict(), 'rotowire': home in set(lineups['team'])}
        reasons_panel(f"{describe_outcome(outcome)} @ {outcome['odds']:.2f}", game_reasons(outcome.to_dict(), ctx),
                      outcome['edge pp'])
        st.caption("The best-priced outcome is shown; pick a market row for another.")

    with teams_tab:
        cols = st.columns(2)
        for col, team, side in ((cols[0], away, 'Away'), (cols[1], home, 'Home')):
            with col:
                r = ratings.loc[team]
                st.markdown(f"**{side}: {team.upper()}** · ORtg {r['off_rtg']:.1f}, DRtg {r['def_rtg']:.1f}, "
                            f"pace {r['pace']:.1f}")
                listed = lineups[lineups['team'] == team]
                if listed.empty:
                    st.caption("📋 Not on RotoWire's page (yet).")
                else:
                    starters = listed[listed['role'] == 'starter']
                    st.caption(f"📋 {listed['lineup_status'].iloc[0] or ''} lineup: "
                               + ", ".join(f"{x['pos']} {x['name']}" for _, x in starters.iterrows()))
                absences = pd.DataFrame([{'out': str(names.get(pid, pid)), 'games missed': imp['n_without'],
                                          'team pts change': imp['pts_for'], 'opp pts change': imp['pts_against']}
                                         for pid, imp in game['absences'][team]])
                if len(absences):
                    table(absences, list(absences.columns), {'team pts change': '%+.1f', 'opp pts change': '%+.1f',
                                                             'games missed': '%d'})
                if st.button(f"Open {team.upper()} in Lineup lab", key=f"lab_{team}"):
                    st.session_state['lineup_team'] = team
                    st.switch_page(PAGES['lineup'])
