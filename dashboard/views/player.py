import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from loaders import filtered_logs, player_logs, season_label, sidebar_filters
from metrics import STATS, player_summary, splits, teammates, with_without

st.title("Player")
seasons, season_types = sidebar_filters()
logs = filtered_logs(seasons, season_types)
if logs.empty:
    st.info("No games for the chosen seasons and game types.")
    st.stop()

# a bet clicked on the Today page preselects player, stat and line
pre = st.session_state.pop("player_preset", None)
players = (logs.groupby(['player_id_ESPN', 'player_display_name', 'player_name_ESPN'])
           .agg(team=('team', 'last'), games=('game_id', 'size')).reset_index()
           .sort_values('player_display_name'))
options = players['player_id_ESPN'].tolist()
names = dict(zip(players['player_id_ESPN'], players['player_display_name'] + " (" + players['team'].str.upper() + ")"))
if pre and pre['player_id'] in names:
    st.session_state['player_id'] = pre['player_id']
    st.session_state['player_stat'] = pre['stat']
    if pre.get('line') is not None:
        st.session_state['player_line'] = float(pre['line'])
        st.session_state['player_use_line'] = True
    if pre.get('teammate') is not None:
        st.session_state['player_teammate_preset'] = pre['teammate']

c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
player_id = c1.selectbox("Player", options, format_func=names.get, key='player_id', index=None,
                         placeholder="Type a name...")
stat = c2.selectbox("Stat", STATS, key='player_stat')
use_line = c4.toggle("Compare with a line", key='player_use_line')
line = c3.number_input("Line", min_value=0.0, step=0.5, key='player_line', disabled=not use_line)
line = line if use_line else None
if player_id is None:
    st.info("Pick a player to see their game log, splits and how a line compares.")
    st.stop()

games = logs[logs['player_id_ESPN'] == player_id].sort_values('Date')
s = player_summary(games, stat, line)
info, link = st.columns([4, 1])
info.caption(f"{s['games']} games in {', '.join(season_label(x) for x in sorted(seasons))}, "
             f"types: {', '.join(season_types)}")
if link.button(f"Open {games['team'].iloc[-1].upper()} in Lineup lab"):
    st.session_state['lineup_team'] = games['team'].iloc[-1]
    st.switch_page("views/lineup.py")

# --- summary cards ---
cards = st.columns(6)
cards[0].metric("Average", f"{s['avg']:.1f}", f"{s['avg_last5'] - s['avg']:+.1f} last 5", help="Season average; delta = last-5 average minus season average")
cards[1].metric("Median", f"{s['median']:.1f}")
cards[2].metric("30–70% band", f"{s['p30']:.1f} – {s['p70']:.1f}", help="betfinder.py checks whether the line falls inside this band")
cards[3].metric("Trend (last 5)", f"{s['trend5']:+.1f}" if not np.isnan(s['trend5']) else "–", help="Average game-to-game change")
cards[4].metric("Minutes", f"{s['min_avg']:.1f}", f"{s['min_avg_last5'] - s['min_avg']:+.1f} last 5")
if line is not None:
    cards[5].metric("Line percentile", f"{s['percentile']:.0f}", "inside band" if s['in_band'] else "outside band",
                    delta_color="off", help="Share of games below the line (50 = at the median)")
    h = st.columns(3)
    for col, label, over, under in ((h[0], "Last 5", s['over_last5'], s['under_last5']),
                                    (h[1], "Last 10", s['over_last10'], s['under_last10']),
                                    (h[2], "All shown games", s['over'], s['under'])):
        col.metric(f"{label}: Over / Under {line}", f"{100 * over:.0f}% / {100 * under:.0f}%")

# --- game log chart ---
colors = np.where(games['season_type'] == 'pre', '#9aa5b1', '#1f77b4')
if line is not None:
    colors = np.where(games[stat] > line, '#2ca02c', np.where(games[stat] < line, '#d62728', '#9aa5b1'))
fig = go.Figure()
fig.add_bar(x=games['game_label'] + ' ' + games['Date'].dt.strftime('%y'), y=games[stat], marker_color=colors,
            marker_pattern_shape=np.where(games['season_type'] == 'pre', '/', ''),
            customdata=np.stack([games['Result'], games['MIN'], games['season_type']], axis=1),
            hovertemplate=f"%{{x}}<br>{stat}: %{{y}}<br>%{{customdata[0]}}, %{{customdata[1]}} min, %{{customdata[2]}}<extra></extra>",
            name=stat)
fig.add_scatter(x=games['game_label'] + ' ' + games['Date'].dt.strftime('%y'), y=games[stat].rolling(5, min_periods=1).mean(),
                mode='lines', name='5-game average', line=dict(color='#ff7f0e'))
if line is not None:
    fig.add_hline(y=line, line_dash='dash', annotation_text=f"line {line}")
fig.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10), xaxis=dict(type='category', tickangle=-60),
                  legend=dict(orientation='h', y=1.1), title=f"{stat} per game (hatched = preseason)")
st.plotly_chart(fig, width='stretch')

# --- splits ---
left, right = st.columns(2)
with left:
    st.subheader("Splits")
    st.dataframe(splits(games, stat, line).round(1), hide_index=True, width='stretch')

    st.subheader("Against each opponent (all seasons)")
    every = player_logs()
    every = every[(every['player_id_ESPN'] == player_id) & every['season_type'].isin(season_types)]
    vs = every.groupby('OPP').agg(games=(stat, 'size'), avg=(stat, 'mean'), last=('Date', 'max')).round({'avg': 1})
    st.dataframe(vs.sort_values('last', ascending=False), width='stretch', height=250)

with right:
    st.subheader("With / without a teammate")
    mates = teammates(logs, player_id)
    if mates.empty:
        st.caption("No teammates in the chosen games.")
    else:
        mate_names = dict(zip(mates['player_id_ESPN'], mates['player_display_name'] + " – " + mates['shared_games'].astype(str) + " games together"))
        preset_mate = st.session_state.pop('player_teammate_preset', None)
        if preset_mate in mate_names:
            st.session_state['player_teammate'] = preset_mate
        elif st.session_state.get('player_teammate') not in mate_names:
            st.session_state.pop('player_teammate', None)
        mate = st.selectbox("Teammate", mates['player_id_ESPN'].tolist(), format_func=mate_names.get, key='player_teammate')
        ww = with_without(logs, player_id, mate, stat)
        if ww.empty or len(ww) < 2:
            st.caption("The teammate didn't miss any of the player's games in this period, so there's nothing to compare.")
        st.dataframe(ww.round(1), width='stretch')
        st.caption("Only games from the teammate's first to last game on this team count, so a trade doesn't show as 'out'.")

st.subheader("Game log")
cols = ['Date', 'OPP', 'type', 'Result', 'season_type', 'starter', 'MIN', 'PTS', 'REB', 'AST', '3PM', 'PA', 'PR', 'ARP',
        'STL', 'BLK', 'TO', 'FGM', 'FGA', '3PA', 'FTM', 'FTA', 'PLUS_MINUS', 'rest_days']
table = games[cols].sort_values('Date', ascending=False)
st.dataframe(table, hide_index=True, width='stretch',
             column_config={'Date': st.column_config.DateColumn(format='YYYY-MM-DD')})
st.download_button("Download CSV", table.to_csv(index=False), file_name=f"{games['player_name_ESPN'].iloc[0]}_{stat}.csv")
