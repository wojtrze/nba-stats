import numpy as np
import pandas as pd
import streamlit as st

from espn_scraper import CURRENT_SEASON
from glossary import column_config, source_legend, tinted
from loaders import games, player_logs, rotowire_lineups, season_label, superbet_offers, today_game_odds
from metrics import absence_impact, blended_ratings, game_projection, market_edges, rotowire_team
from superbet_fetcher import main_lines

TYPES = ['regular', 'playin', 'post']
MARKET_LABELS = {'ML': 'Moneyline', 'SPREAD': 'Handicap', 'TOTAL': 'Total', 'HOME_TOTAL': 'Home team total',
                 'AWAY_TOTAL': 'Away team total'}

st.title("Games")
st.caption("Superbet's game markets for the next 36 hours next to a simple projection: each team's offensive and "
           "defensive rating and pace (this season blended with last season), home court, and how the team "
           "usually does without the players RotoWire lists as out.")

top = st.columns([1, 4])
if top[0].button("Refresh offers"):
    superbet_offers.clear()
    rotowire_lineups.clear()
with top[1].expander("Settings"):
    s = st.columns(5)
    prior_games = s[0].number_input("Prior weight (games)", 0, 82, 10,
                                    help="This season counts n / (n + this) against last season's ratings")
    regress = s[0].slider("Regress last season to average", 0.0, 1.0, 0.3, 0.1,
                          help="Rosters change over the summer; 0 = use last season's ratings as they were")
    home_court = s[1].number_input("Home court (pts)", 0.0, 6.0, 1.5, 0.5,
                                   help="Points the home team gains just from playing at home, split half to the "
                                        "home score and half off the away score")
    shrink = s[2].number_input("Absence shrink", 0, 30, 5,
                               help="Each absence's effect is weighted by n / (n + shrink), n = games missed")
    out_max = s[3].selectbox("Count as out", [0, 25, 50], index=1, format_func=lambda v: f"≤ {v}% to play",
                             help="RotoWire players with at most this chance to play are treated as out")
    all_lines = s[4].toggle("Show every line", help="Otherwise only Superbet's main line of each market (the "
                                                    "line where both sides have the closest odds)")

odds = today_game_odds()
if odds.empty:
    st.info("Superbet has no NBA games in the next 36 hours.")
    st.stop()

all_games = games()
all_games = all_games[all_games['season_type'].isin(TYPES)]
current, prior = all_games[all_games['season_id'] == CURRENT_SEASON], all_games[all_games['season_id'] == CURRENT_SEASON - 1]
ratings = blended_ratings(current, prior, prior_games, regress)
logs = player_logs()
logs = logs[logs['season_id'].isin([CURRENT_SEASON - 1, CURRENT_SEASON]) & logs['season_type'].isin(TYPES)]
lineups = rotowire_lineups()
names = logs.groupby('player_id_ESPN')['player_display_name'].last()
st.caption(f"Ratings: {season_label(CURRENT_SEASON)} ({len(current)} games) blended with "
           f"{season_label(CURRENT_SEASON - 1)} ({len(prior)} games).")


@st.cache_data(show_spinner=False)
def cached_impact(team, player_id, shrink):
    return absence_impact(all_games, logs, team, player_id, shrink)


def describe(outcome) -> str:
    """'Handicap DET +1.5', 'Total over 220.5', 'Moneyline BOS'."""
    who = outcome['team'].upper() if outcome['market'] in ('ML', 'SPREAD') else outcome['side']
    line = '' if pd.isna(outcome['line']) else \
        f" {outcome['line']:+g}" if outcome['market'] == 'SPREAD' else f" {outcome['line']:g}"
    return f"{MARKET_LABELS[outcome['market']]} {who}{line}"


def winner(projection, home, away) -> str:
    """'BOS by 3.5': the projected winner and margin."""
    return f"{(home if projection['margin'] >= 0 else away).upper()} by {abs(projection['margin']):.1f}"


summary, details = [], []
for event_id, game_odds in odds.groupby('event_id', sort=False):
    home, away = game_odds['home'].iloc[0], game_odds['away'].iloc[0]
    if home not in ratings.index or away not in ratings.index:
        continue
    absences = {}
    for team in (home, away):
        rw = rotowire_team(lineups, team, out_max)
        absences[team] = [(p, cached_impact(team, p, shrink)) for p in rw['out']]
    projection = game_projection(ratings, home, away, home_court,
                                 [imp for _, imp in absences[home]], [imp for _, imp in absences[away]])
    shown_odds = game_odds if all_lines else pd.DataFrame(main_lines(game_odds.to_dict('records')))
    edges = market_edges(projection, shown_odds)
    best = edges.loc[edges['edge pp'].idxmax()]
    start = pd.to_datetime(game_odds['start_time'].iloc[0]).tz_convert('Europe/Warsaw')
    label = f"{away.upper()} @ {home.upper()}"
    # the decision first, then the projection behind it, then where the inputs stand
    summary.append({'game': label, 'start (PL)': start.strftime('%a %H:%M'),
                    'best bet': describe(best), 'best edge pp': best['edge pp'], 'best odds': best['odds'],
                    'proj score': f"{projection['away_pts']:.0f} – {projection['home_pts']:.0f}",
                    'proj winner': winner(projection, home, away), 'proj total': projection['total'],
                    'RotoWire': '✔' if home in set(lineups['team']) else ''})
    details.append((label, start, home, away, projection, edges, absences))

st.subheader("Overview")
overview = pd.DataFrame(summary)
overview_formats = {'proj total': '%.1f', 'best edge pp': '%+.1f', 'best odds': '%.2f'}
st.caption(source_legend())
st.dataframe(tinted(overview, overview_formats, sources={'best odds': 'superbet'}), hide_index=True, width='stretch',
             column_config=column_config(overview.columns, overview_formats,
                                         tips={'RotoWire': "✔ = RotoWire already lists this game's lineups and "
                                                           "injuries, so absences are in the projection",
                                               'best odds': "Superbet's odds for the best bet"},
                                         sources={'best odds': 'superbet'}))
st.caption("Hover a column header for what it means; expand a game below for every market. Superbet's margin is "
           "about 2–3 pp per side, so small edges are noise.")

for label, start, home, away, projection, edges, absences in details:
    with st.expander(f"{label} · {start.strftime('%a %H:%M')} · projected {away.upper()} {projection['away_pts']:.0f} – "
                     f"{projection['home_pts']:.0f} {home.upper()}"):
        cols = st.columns(2)
        for col, team, side in ((cols[0], away, 'Away'), (cols[1], home, 'Home')):
            col.markdown(f"**{side}: {team.upper()}** — 📊 ORtg {ratings.loc[team, 'off_rtg']:.1f}, "
                         f"DRtg {ratings.loc[team, 'def_rtg']:.1f}, pace {ratings.loc[team, 'pace']:.1f}",
                         help="📊 Calculated from the scraped games: points scored / allowed per 100 possessions "
                              "and possessions per game, this season blended with last season")
            listed = lineups[lineups['team'] == team]
            if listed.empty:
                col.caption("📋 Not on RotoWire's page (yet).")
            else:
                starters = listed[listed['role'] == 'starter']
                col.caption(f"📋 RotoWire {listed['lineup_status'].iloc[0] or ''} lineup: "
                            + ", ".join(f"{r['pos']} {r['name']}" for _, r in starters.iterrows()))
                may_not = listed[listed['role'] == 'may_not_play']
                if len(may_not):
                    col.caption("📋 May not play: " + ", ".join(f"{r['name']} ({r['injury']}, {r['play_pct']:.0f}%)"
                                                             for _, r in may_not.iterrows()))
            rows = [{'out': str(names.get(p, p)), 'games missed': imp['n_without'], 'team pts change': imp['pts_for'],
                     'opp pts change': imp['pts_against']} for p, imp in absences[team]]
            if rows:
                absence_table = pd.DataFrame(rows)
                absence_formats = {'team pts change': '%+.1f', 'opp pts change': '%+.1f', 'games missed': '%d'}
                col.dataframe(tinted(absence_table, absence_formats), hide_index=True, width='stretch',
                              column_config=column_config(absence_table.columns, absence_formats))
        m = st.columns(4)
        m[0].metric("Projected winner", winner(projection, home, away),
                    help=f"Projected {home.upper()} points minus {away.upper()} points: "
                         f"{projection['margin']:+.1f} (home margin)")
        m[1].metric("Projected total", f"{projection['total']:.1f}", help="Both teams' projected points combined")
        m[2].metric(f"{home.upper()} points", f"{projection['home_pts']:.1f}",
                    help="Pace × (own ORtg + opponent's DRtg − league average) / 100, + half the home-court edge, "
                         "+ the effect of missing players")
        m[3].metric(f"{away.upper()} points", f"{projection['away_pts']:.1f}",
                    help="Pace × (own ORtg + opponent's DRtg − league average) / 100, − half the home-court edge, "
                         "+ the effect of missing players")
        # markets in MARKET_LABELS order (moneyline first), then by line
        table = edges.assign(order=edges['market'].map(list(MARKET_LABELS).index),
                             market=edges['market'].map(MARKET_LABELS), team=edges['team'].fillna('').str.upper(),
                             signal=np.select([edges['edge pp'] >= 5, edges['edge pp'] <= -5], ['🟢', '🔴'], ''))
        table = table.sort_values(['order', 'line', 'side'])
        # a moneyline has no line: show it as text so the empty cell reads '–' rather than 'None'
        table['line'] = [('–' if pd.isna(v) else f"{v:+g}" if m == 'Handicap' else f"{v:g}")
                         for v, m in zip(table['line'], table['market'])]
        # outcome -> verdict -> Superbet's price -> the model's price
        market_cols = ['market', 'team', 'side', 'line', 'signal', 'edge pp', 'odds', 'implied %', 'model %',
                       'fair odds']
        market_formats = {'implied %': '%.0f', 'model %': '%.0f', 'fair odds': '%.2f', 'odds': '%.2f',
                          'edge pp': '%+.1f'}
        st.dataframe(tinted(table[market_cols], market_formats), hide_index=True, width='stretch',
                     column_config=column_config(
                         market_cols, formats=market_formats,
                         tips={'line': "Handicap: the team's handicap (+1.5 = still wins the bet if it loses by 1). "
                                       "Totals: the points line. Empty for the moneyline.",
                               'signal': "🟢 model edge of +5 pp or more, 🔴 −5 pp or less",
                               'edge pp': "model % − implied %, in percentage points"}))
        b = st.columns(2)
        for i, team in enumerate((away, home)):
            if b[i].button(f"Open {team.upper()} in Lineup lab", key=f"lab_{label}_{team}"):
                st.session_state['lineup_team'] = team
                st.switch_page("views/lineup.py")
