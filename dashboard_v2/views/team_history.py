import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import charts
from core.analysis import team_game_log
from core.data import props
from core.state import persist, remember
from core.ui import PAGES, kpis, page_header, stop, table
from espn_scraper import NBA_TEAM_ABBRS, NBA_TEAM_NAMES
from loaders import filtered_logs, games as all_games
from metrics import allowed_by_position, team_ratings, team_rotation

seasons, season_types = page_header("Team history", "One team's results, how its ratings moved, what its defense "
                                                    "allows to each position and who plays.", with_scope=True)
g = all_games()
g = g[g['season_id'].isin(seasons) & g['season_type'].isin(season_types)
      & g['home'].isin(NBA_TEAM_ABBRS) & g['away'].isin(NBA_TEAM_ABBRS)]
logs = filtered_logs(seasons, season_types)
if g.empty:
    st.info("No games in the scope.")
    stop()

today = props()
playing = sorted(set(today['home']) | set(today['away'])) if len(today) else []
teams = playing + sorted(t for t in NBA_TEAM_ABBRS if t not in playing)
persist('th_team', teams[0])
team = st.selectbox("Team", teams, key='th_team', on_change=remember, args=('th_team',),
                    format_func=lambda t: f"{t.upper()} – {NBA_TEAM_NAMES.get(t, '')}",
                    help="Teams playing in the next 36 hours are listed first")

ratings = team_ratings(g)
if team not in ratings.index:
    st.info(f"{team.upper()} has no games in the scope.")
    stop()
r = ratings.loc[team]
rank = lambda col, best_high=True: int(ratings[col].rank(ascending=not best_high, method='min')[team])
kpis([{'label': "Record", 'value': f"{int(r['wins'])}-{int(r['losses'])}", 'delta': f"home {r['home']}",
       'delta_color': 'off'},
      {'label': "Offensive rating", 'value': f"{r['off_rtg']:.1f}", 'delta': f"#{rank('off_rtg')} of {len(ratings)}",
       'delta_color': 'off', 'help': "Points scored per 100 possessions"},
      {'label': "Defensive rating", 'value': f"{r['def_rtg']:.1f}",
       'delta': f"#{rank('def_rtg', best_high=False)} of {len(ratings)}", 'delta_color': 'off',
       'help': "Points allowed per 100 possessions (lower is better)"},
      {'label': "Net rating", 'value': f"{r['net_rtg']:+.1f}", 'delta': f"#{rank('net_rtg')}", 'delta_color': 'off'},
      {'label': "Pace", 'value': f"{r['pace']:.1f}", 'delta': f"#{rank('pace')} fastest", 'delta_color': 'off',
       'help': "Possessions per game"}])

log = team_game_log(g, team)
# the year too: the same opponent on the same date in two seasons would share one bar
log['label'] = log['date'].dt.strftime('%y-%m-%d') + np.where(log['location'] == 'home', ' vs ', ' @ ') + \
    log['opp'].str.upper()

results_tab, trend_tab, defense_tab, players_tab = st.tabs(
    ["Results", "Ratings trend", "Defense vs position", "Players"])

with results_tab:
    fig = go.Figure(go.Bar(x=log['label'], y=log['margin'], marker_color=np.where(log['win'], charts.OVER, charts.UNDER),
                           customdata=np.stack([log['pts'], log['opp_pts'], log['season_type']], axis=1),
                           hovertemplate="%{x}: %{customdata[0]}–%{customdata[1]} (%{customdata[2]})<extra></extra>"))
    charts.show(charts.layout(fig, 340, "Margin per game (green = win)", xaxis=dict(type='category', tickangle=-50),
                              yaxis=dict(title='points')), key='th_margin')
    split = log.groupby('location').agg(games=('win', 'size'), wins=('win', 'sum'), pts=('pts', 'mean'),
                                        opp_pts=('opp_pts', 'mean'), margin=('margin', 'mean')).reset_index()
    table(split, list(split.columns), {'pts': '%.1f', 'opp_pts': '%.1f', 'margin': '%+.1f', 'wins': '%d'},
          tips={'location': "Home or away games", 'margin': "Average points margin"},
          sources={c: 'stats' for c in split.columns})

with trend_tab:
    window = st.segmented_control("Rolling window", [5, 10, 20], default=10, format_func=lambda n: f"{n} games",
                                  key='th_window') or 10
    roll = log[['off_rtg', 'def_rtg', 'pace']].rolling(window, min_periods=1).mean()
    fig = go.Figure()
    fig.add_scatter(x=log['label'], y=roll['off_rtg'], name='ORtg (scored)', line=dict(color=charts.OVER))
    fig.add_scatter(x=log['label'], y=roll['def_rtg'], name='DRtg (allowed)', line=dict(color=charts.UNDER))
    fig.add_hline(y=ratings['off_rtg'].mean(), line_dash='dot', line_color='#94a3b8', annotation_text="league avg")
    charts.show(charts.layout(fig, 320, f"Points per 100 possessions, {window}-game average",
                              xaxis=dict(type='category', tickangle=-50)), key='th_rtg')
    fig = go.Figure(go.Scatter(x=log['label'], y=roll['pace'], name='pace', line=dict(color=charts.NEUTRAL)))
    fig.add_hline(y=ratings['pace'].mean(), line_dash='dot', line_color='#94a3b8', annotation_text="league avg")
    charts.show(charts.layout(fig, 260, f"Pace (possessions per game), {window}-game average",
                              xaxis=dict(type='category', tickangle=-50)), key='th_pace')
    st.caption("A gap between the green line above the red one = outscoring opponents. Possessions are estimated "
               "as FGA + 0.44·FTA + TO − OREB.")

with defense_tab:
    stat = st.segmented_control("Stat allowed", ['PTS', 'REB', 'AST', '3PM', 'PA', 'PR', 'RA', 'ARP'], default='PTS',
                                format_func=lambda s: 'PRA' if s == 'ARP' else s, key='th_stat') or 'PTS'
    allowed = allowed_by_position(logs, stat)
    allowed = allowed[allowed.index.isin(NBA_TEAM_ABBRS)]
    if team not in allowed.index:
        st.caption("No games in the scope.")
    else:
        league = allowed[['G', 'F', 'C']].mean()
        rows = []
        for group, word in (('G', 'Guards'), ('F', 'Forwards'), ('C', 'Centers')):
            value = allowed.loc[team, group]
            rows.append({'position': word, 'allowed': value, 'league avg': league[group],
                         'vs avg %': 100 * (value / league[group] - 1),
                         'rank': int(allowed[group].rank(ascending=False, method='min')[team])})
        d = pd.DataFrame(rows)
        fig = go.Figure(go.Bar(x=d['position'], y=d['vs avg %'],
                               marker_color=np.where(d['vs avg %'] > 0, charts.OVER, charts.UNDER),
                               text=d['vs avg %'].map('{:+.0f}%'.format), textposition='outside'))
        fig.add_hline(y=0, line_color='#64748b')
        charts.show(charts.layout(fig, 280, f"{'PRA' if stat == 'ARP' else stat} {team.upper()} allows vs the "
                                            f"average defense (green = gives up more: good for Overs against them)",
                                  yaxis=dict(title='% vs league')), key='th_def')
        table(d, list(d.columns), {'allowed': '%.1f', 'league avg': '%.1f', 'vs avg %': '%+.0f', 'rank': '%d'},
              tips={'rank': f"1 = allows the most of {len(allowed)} teams",
                    'allowed': "Per game, all opposing players at the position together"},
              sources={c: 'stats' for c in d.columns})

with players_tab:
    roster = team_rotation(logs, team, 1, 0)
    if roster.empty:
        st.caption("No players in the scope.")
    else:
        team_logs = logs[(logs['team'] == team) & logs['player_id_ESPN'].isin(roster.index)]
        stats = team_logs.groupby('player_id_ESPN')[['PTS', 'REB', 'AST', '3PM']].mean()
        team_games = team_logs['game_id'].nunique()
        roster = roster.join(stats).assign(missed=lambda d: team_games - d['games'])
        roster['last_game'] = roster['last_game'].dt.date
        cols = ['name', 'position', 'games', 'starts', 'missed', 'mpg', 'PTS', 'REB', 'AST', '3PM', 'last_game']
        table(roster.reset_index(), cols, {'mpg': '%.1f', 'PTS': '%.1f', 'REB': '%.1f', 'AST': '%.1f', '3PM': '%.1f',
                                           'games': '%d', 'starts': '%d', 'missed': '%d'},
              tips={'missed': f"Team games without the player (of {team_games}; includes games before they joined)",
                    'mpg': "Minutes per game", 'last_game': "Most recent game"},
              sources={c: 'stats' for c in cols})
        if st.button(f"Open {team.upper()} in Lineup lab"):
            st.session_state['lineup_team'] = team
            st.switch_page(PAGES['lineup'])
