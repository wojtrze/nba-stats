import plotly.express as px
import streamlit as st

from loaders import filtered_logs, games, sidebar_filters, today_props
from espn_scraper import NBA_TEAM_ABBRS
from metrics import allowed_by_position, team_ratings

st.title("Teams & matchups")
seasons, season_types = sidebar_filters()
g = games()
g = g[g['season_id'].isin(seasons) & g['season_type'].isin(season_types) &
      g['home'].isin(NBA_TEAM_ABBRS) & g['away'].isin(NBA_TEAM_ABBRS)]
logs = filtered_logs(seasons, season_types)
if g.empty:
    st.info("No games for the chosen seasons and game types.")
    st.stop()

stat = st.radio("Stat allowed", ['PTS', 'REB', 'AST', '3PM', 'PA', 'PR', 'ARP'], horizontal=True)
allowed = allowed_by_position(logs, stat)
league = allowed[['G', 'F', 'C']].mean()

# --- matchup ---
st.subheader("Matchup")
upcoming = today_props()
matchups = sorted({f"{a} @ {h}" for h, a in zip(upcoming['home'], upcoming['away'])}) if not upcoming.empty else []
teams = sorted(allowed.index)
c = st.columns([2, 2, 3])


def pick_matchup():
    if st.session_state['team_matchup']:
        st.session_state['team_away'], st.session_state['team_home'] = st.session_state['team_matchup'].split(' @ ')


if matchups:
    c[2].selectbox("Today's games (Superbet)", [None] + matchups, key='team_matchup', on_change=pick_matchup,
                   format_func=lambda m: m.upper() if m else "–")
away = c[0].selectbox("Away", teams, key='team_away', format_func=str.upper)
home = c[1].selectbox("Home", teams, key='team_home', format_func=str.upper, index=min(1, len(teams) - 1))

side = allowed.loc[[away, home], ['G', 'F', 'C']]
diff = (side - league).round(1)
cols = st.columns(2)
for col, team in zip(cols, [away, home]):
    with col:
        st.markdown(f"**{team.upper()} defense** – {stat} allowed per game to opponents' guards / forwards / centers "
                    f"(vs league average)")
        m = st.columns(3)
        for box, group in zip(m, ['G', 'F', 'C']):
            box.metric(group, f"{side.loc[team, group]:.1f}", f"{diff.loc[team, group]:+.1f}", delta_color="inverse",
                       help="Red = allows more than average, so a good matchup for that position's Overs")
links = st.columns(2)
for col, team in zip(links, [away, home]):
    if col.button(f"Open {team.upper()} in Lineup lab", key=f"lab_{team}"):
        st.session_state['lineup_team'] = team
        st.switch_page("views/lineup.py")
st.caption("A positive number (red) means the defense gives up more than average to that position group: "
           "a softer matchup for those players' Overs.")

# --- tables ---
st.subheader(f"{stat} allowed by position (per game)")
table = allowed.copy()
for group in ['G', 'F', 'C']:
    table[f'{group} vs avg'] = table[group] - league[group]
st.dataframe(table.round(1).sort_values('G vs avg', ascending=False).rename(index=str.upper), width='stretch',
             column_config={'games': st.column_config.NumberColumn(format='%d')})

st.subheader("Team ratings")
ratings = team_ratings(g).round(1)
fig = px.scatter(ratings.reset_index(), x='off_rtg', y='def_rtg', text=ratings.index.str.upper(), size='games',
                 labels={'off_rtg': 'Offensive rating (pts / 100 poss)', 'def_rtg': 'Defensive rating (lower is better)'})
fig.update_yaxes(autorange='reversed')
fig.update_traces(textposition='top center')
fig.update_layout(height=450, margin=dict(t=20))
st.plotly_chart(fig, width='stretch')
st.dataframe(ratings.rename(index=str.upper), width='stretch')
st.caption("Possessions are estimated as FGA + 0.44·FTA + TO − OREB. Pace is the average of both teams' possessions.")
