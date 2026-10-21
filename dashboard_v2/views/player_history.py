import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import charts
from core.state import persist, remember
from core.ui import PAGES, kpis, page_header, stop
from glossary import STAT_HELP, column_config
from loaders import filtered_logs, player_logs, season_label
from metrics import STATS, line_percentile, player_summary, splits, teammates, with_without

seasons, season_types = page_header("Player history", "One player's games: form, how results spread around a line, "
                                                      "season trends, splits, opponents and teammates.",
                                    with_scope=True)
logs = filtered_logs(seasons, season_types)
every = player_logs()
every = every[every['season_type'].isin(season_types)]
if every.empty:
    st.info("No games stored for these game types.")
    stop()

# a line opened from Props preselects player, stat and line
pre = st.session_state.pop('player_preset', None)
players = (every.groupby('player_id_ESPN').agg(name=('player_display_name', 'last'), team=('team', 'last'),
                                               last=('Date', 'max'))
           .sort_values('name'))
labels = (players['name'] + " (" + players['team'].str.upper() + ")").to_dict()
persist('ph_player', None)
persist('ph_stat', 'PTS')
persist('ph_line', None)
if pre and pre['player_id'] in labels:
    st.session_state['ph_player'], st.session_state['ph_stat'] = pre['player_id'], pre['stat']
    st.session_state['ph_line'] = pre.get('line')
    for key in ('ph_player', 'ph_stat', 'ph_line'):
        remember(key)

c = st.columns([3, 2, 1])
player_id = c[0].selectbox("Player", list(labels), format_func=labels.get, key='ph_player', index=None,
                           placeholder="Type a name...", on_change=remember, args=('ph_player',))
stat = c[1].selectbox("Stat", STATS, key='ph_stat', format_func=lambda s: f"{s} – {STAT_HELP[s]}",
                      on_change=remember, args=('ph_stat',))
line = c[2].number_input("Line (optional)", min_value=0.0, step=0.5, key='ph_line',
                         placeholder="e.g. 18.5", on_change=remember, args=('ph_line',),
                         help="Colours the games over / under it and adds hit rates")
if player_id is None:
    st.info("Pick a player to see their history.", icon="👆")
    stop()

games = logs[logs['player_id_ESPN'] == player_id].sort_values('Date')
career = every[every['player_id_ESPN'] == player_id].sort_values('Date')
if games.empty:
    st.warning(f"{players.loc[player_id, 'name']} has no games in the scope; the season trend below covers every "
               f"stored season.")
else:
    s = player_summary(games, stat, line)
    items = [{'label': "Average", 'value': f"{s['avg']:.1f}", 'help': f"{s['games']} games in the scope"},
             {'label': "Last 5", 'value': f"{s['avg_last5']:.1f}", 'delta': f"{s['avg_last5'] - s['avg']:+.1f}",
              'help': "Average over the last 5 games, vs the average"},
             {'label': "Last 10", 'value': f"{s['avg_last10']:.1f}", 'delta': f"{s['avg_last10'] - s['avg']:+.1f}"},
             {'label': "Median", 'value': f"{s['median']:.1f}", 'help': "Half the games above, half below"},
             {'label': "Minutes", 'value': f"{s['min_avg']:.1f}", 'delta': f"{s['min_avg_last5'] - s['min_avg']:+.1f} L5",
              'help': "Average minutes; the small text is the last 5 games vs that"}]
    if line is not None:
        items.append({'label': f"Over {line:g}", 'value': f"{100 * s['over']:.0f}%",
                      'delta': f"{100 * s['over_last10']:.0f}% L10", 'delta_color': 'off',
                      'help': f"Share of games over the line; percentile of the line {s['percentile']:.0f}"})
    kpis(items)
    if c[0].button("Open the team in Lineup lab", key='ph_lab'):
        st.session_state['lineup_team'] = games['team'].iloc[-1]
        st.switch_page(PAGES['lineup'])

log_tab, dist_tab, trend_tab, split_tab, opp_tab, mate_tab, table_tab = st.tabs(
    ["Game log", "Distribution", "Season trend", "Splits", "Opponents", "With / without", "All games"])

with log_tab:
    if games.empty:
        st.caption("No games in the scope.")
    else:
        n = st.segmented_control("Games", [10, 20, 40, 0], default=20, format_func=lambda v: f"last {v}" if v else "all",
                                 key='ph_last')
        charts.show(charts.game_log(games, stat, line, last=n or None, minutes=True,
                                    title=f"{stat} per game" + (" vs the line" if line is not None else "")),
                    key='ph_log')
        st.caption("Bars: each game (green over / red under the line; light = preseason). Orange: 5- and 10-game "
                   "averages. Grey: minutes (right axis).")

with dist_tab:
    if games.empty:
        st.caption("No games in the scope.")
    else:
        left, right = st.columns([3, 2])
        with left:
            charts.show(charts.distribution(games[stat], stat, line, f"How often each {stat} result happened"),
                        key='ph_dist')
        with right:
            values = games[stat]
            q = values.quantile([0.1, 0.3, 0.5, 0.7, 0.9])
            st.markdown("**Percentiles**")
            st.dataframe(pd.DataFrame({'percentile': ['10th', '30th', 'median', '70th', '90th'], stat: q.values}),
                         hide_index=True, width='stretch',
                         column_config={stat: st.column_config.NumberColumn(format='%.1f')})
            st.caption("A line below the 30th or above the 70th percentile looks unusually low or high for this "
                       "player." + (f" This line sits at the {line_percentile(values, line):.0f}th." if line is not None
                                    else ""))

with trend_tab:
    st.caption("Every stored season of the chosen game types, regardless of the scope.")
    by_season = career.groupby('season_id').agg(games=(stat, 'size'), avg=(stat, 'mean'), minutes=('MIN', 'mean'),
                                                 team=('team', 'last')).reset_index()
    by_season['season'] = by_season['season_id'].map(season_label)
    monthly = career.assign(month=career['Date'].dt.to_period('M').dt.to_timestamp()) \
        .groupby('month').agg(avg=(stat, 'mean'), games=(stat, 'size')).reset_index()
    left, right = st.columns(2)
    with left:
        fig = go.Figure(go.Bar(x=by_season['season'], y=by_season['avg'], marker_color=charts.NEUTRAL,
                               text=by_season['avg'].map('{:.1f}'.format), textposition='outside',
                               customdata=by_season[['games', 'minutes']],
                               hovertemplate="%{x}: %{y:.1f} in %{customdata[0]} games, %{customdata[1]:.1f} min"
                                             "<extra></extra>"))
        if line is not None:
            fig.add_hline(y=line, line_dash='dash', annotation_text=f"line {line:g}")
        charts.show(charts.layout(fig, 300, f"{stat} per season"), key='ph_season')
    with right:
        fig = go.Figure(go.Scatter(x=monthly['month'], y=monthly['avg'], mode='lines+markers',
                                   line=dict(color=charts.AVERAGE), customdata=monthly['games'],
                                   hovertemplate="%{x|%b %Y}: %{y:.1f} in %{customdata} games<extra></extra>"))
        charts.show(charts.layout(fig, 300, f"{stat} per month"), key='ph_month')

with split_tab:
    if games.empty:
        st.caption("No games in the scope.")
    else:
        sp = splits(games, stat, line)
        fig = go.Figure(go.Bar(x=sp['avg'], y=sp['split'] + ': ' + sp['value'].astype(str), orientation='h',
                               marker_color=charts.NEUTRAL, text=sp['avg'].map('{:.1f}'.format) + ' (' +
                               sp['games'].astype(str) + ' g)', textposition='outside'))
        fig.add_vline(x=games[stat].mean(), line_color=charts.AVERAGE, annotation_text="overall")
        if line is not None:
            fig.add_vline(x=line, line_dash='dash', annotation_text=f"line {line:g}")
        charts.show(charts.layout(fig, 60 + 30 * len(sp), f"{stat} by situation", yaxis=dict(autorange='reversed')),
                    key='ph_splits')
        st.dataframe(sp, hide_index=True, width='stretch',
                     column_config=column_config(sp.columns, {'avg': '%.1f', 'median': '%.1f', 'over %': '%.0f'}))

with opp_tab:
    vs = career.groupby('OPP').agg(games=(stat, 'size'), avg=(stat, 'mean'), last=('Date', 'max')).reset_index()
    vs = vs.sort_values('avg', ascending=False)
    fig = go.Figure(go.Bar(x=vs['OPP'], y=vs['avg'], marker_color=np.where(vs['avg'] >= career[stat].mean(),
                                                                          charts.OVER, charts.UNDER),
                           customdata=vs['games'], hovertemplate="vs %{x}: %{y:.1f} in %{customdata} games"
                                                                  "<extra></extra>"))
    fig.add_hline(y=career[stat].mean(), line_color=charts.AVERAGE, annotation_text="career avg")
    charts.show(charts.layout(fig, 320, f"{stat} against each opponent (every stored season)"), key='ph_opp')
    st.caption("Green = above the player's average against everyone. Few games against a team make its bar noisy.")

with mate_tab:
    mates = teammates(career, player_id)
    if mates.empty:
        st.caption("No teammates in the stored games.")
    else:
        mate_labels = dict(zip(mates['player_id_ESPN'], mates['player_display_name'] + " – "
                               + mates['shared_games'].astype(str) + " games together"))
        mate = st.selectbox("Teammate", list(mate_labels), format_func=mate_labels.get, key='ph_mate')
        ww = with_without(career, player_id, mate, stat)
        if len(ww) < 2:
            st.caption("The teammate didn't miss any of the player's games while on the team, so there's nothing to "
                       "compare.")
        if len(ww):
            st.dataframe(ww, width='stretch',
                         column_config=column_config(ww.columns, {c: '%.1f' for c in ['avg', 'median', 'minutes',
                                                                                     'shots']}))
        st.caption("Every stored season; only games from the teammate's first to last game on the team count. "
                   "The full matrix for a whole rotation is in Lineup lab.")

with table_tab:
    cols = ['Date', 'OPP', 'type', 'Result', 'season_type', 'starter', 'MIN', 'PTS', 'REB', 'AST', '3PM', 'PA', 'PR',
            'ARP', 'STL', 'BLK', 'TO', 'FGM', 'FGA', '3PA', 'FTM', 'FTA', 'PLUS_MINUS', 'rest_days']
    full = career[cols].sort_values('Date', ascending=False)
    st.dataframe(full, hide_index=True, width='stretch', height=420,
                 column_config=column_config(cols) | {'Date': st.column_config.DateColumn(format='YYYY-MM-DD')})
    st.download_button("Download CSV", full.to_csv(index=False),
                       file_name=f"{career['player_name_ESPN'].iloc[0]}.csv")
