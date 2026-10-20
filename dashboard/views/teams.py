import plotly.express as px
import streamlit as st

from glossary import STAT_HELP, column_config, source_legend
from loaders import filtered_logs, games, sidebar_filters, today_props
from espn_scraper import NBA_TEAM_ABBRS
from metrics import allowed_by_position, team_ratings

st.title("Teams & matchups")
st.caption(source_legend(['stats']) + " — every number on this page is calculated from the scraped "
           "ESPN games; 💰 Superbet only supplies the list of today's games")
seasons, season_types = sidebar_filters()
g = games()
g = g[g['season_id'].isin(seasons) & g['season_type'].isin(season_types) &
      g['home'].isin(NBA_TEAM_ABBRS) & g['away'].isin(NBA_TEAM_ABBRS)]
logs = filtered_logs(seasons, season_types)
if g.empty:
    st.info("No games for the chosen seasons and game types.")
    st.stop()

stat = st.radio("Stat allowed", ['PTS', 'REB', 'AST', '3PM', 'PA', 'PR', 'RA', 'ARP'], horizontal=True,
                format_func=lambda s: 'PRA' if s == 'ARP' else s,
                help="The stat opponents' players produce against each defense. " +
                     ", ".join(f"{s} = {STAT_HELP[s].lower()}" for s in ['PA', 'PR', 'RA', 'ARP']))
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
    c[2].selectbox("💰 Today's games (Superbet)", [None] + matchups, key='team_matchup', on_change=pick_matchup,
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
            box.metric({'G': 'Guards', 'F': 'Forwards', 'C': 'Centers'}[group], f"{side.loc[team, group]:.1f}",
                       f"{diff.loc[team, group]:+.1f}", delta_color="inverse",
                       help=f"{stat} per game this defense allows to opponents' {group} players combined. The small "
                            f"number is the difference from the league average; red = allows more, a softer "
                            f"matchup for those players' Overs.")
links = st.columns(2)
for col, team in zip(links, [away, home]):
    if col.button(f"Open {team.upper()} in Lineup lab", key=f"lab_{team}"):
        st.session_state['lineup_team'] = team
        st.switch_page("views/lineup.py")
st.caption("Red = the defense gives up more than average to that position: a softer matchup for those players' "
           "Overs. Hover the numbers for details.")

# --- tables ---
st.subheader(f"{stat} allowed by position (per game)")
table = allowed.copy()
for group in ['G', 'F', 'C']:
    table[f'{group} vs avg'] = table[group] - league[group]
st.dataframe(table.sort_values('G vs avg', ascending=False).rename(index=str.upper), width='stretch',
             column_config=column_config(table.columns,
                                         formats={c: '%.1f' for c in table.columns if c != 'games'} | {'games': '%d'},
                                         tips={'games': "Games this team's defense played in the chosen period"}))

st.subheader("Team ratings")
ratings = team_ratings(g).round(1)
fig = px.scatter(ratings.reset_index(), x='off_rtg', y='def_rtg', text=ratings.index.str.upper(), size='games',
                 labels={'off_rtg': 'Offensive rating (pts / 100 poss)', 'def_rtg': 'Defensive rating (lower is better)'})
fig.update_yaxes(autorange='reversed')
fig.update_traces(textposition='top center')
fig.update_layout(height=450, margin=dict(t=20))
st.plotly_chart(fig, width='stretch')
st.dataframe(ratings.rename(index=str.upper), width='stretch',
             column_config=column_config(ratings.columns,
                                         formats={c: '%.1f' for c in ['pts', 'opp_pts', 'pace', 'off_rtg', 'def_rtg',
                                                                      'net_rtg']},
                                         tips={'games': "Games played in the chosen period"}))
st.caption("Possessions are estimated as FGA + 0.44·FTA + TO − OREB.")
