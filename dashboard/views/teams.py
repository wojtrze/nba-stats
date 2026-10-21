import plotly.express as px
import streamlit as st

from glossary import STAT_HELP, column_config, source_legend
from loaders import filtered_logs, games, sidebar_filters, today_props
from espn_scraper import NBA_TEAM_ABBRS, NBA_TEAM_NAMES
from metrics import allowed_by_position, matchup_verdict, team_ratings

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
st.caption("Pick a game: each side shows what one team's guards, forwards and centers usually get against the other "
           "team's defense.")
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

POSITIONS = {'G': 'guards', 'F': 'forwards', 'C': 'centers'}
STAT_WORDS = {'PTS': 'points', 'REB': 'rebounds', 'AST': 'assists', '3PM': 'three-pointers',
              'PA': 'points + assists', 'PR': 'points + rebounds', 'RA': 'rebounds + assists',
              'ARP': 'points + rebounds + assists'}
stat_name = 'PRA' if stat == 'ARP' else stat
rank = allowed[['G', 'F', 'C']].rank(ascending=False, method='min').astype(int)   # 1 = allows the most
name = lambda team: NBA_TEAM_NAMES.get(team, team.upper())

if away == home:
    st.warning("Pick two different teams.")
cols = st.columns(2)
# each side: one team's players against the *other* team's defense
for col, attack, defense in zip(cols, [away, home], [home, away]):
    with col:
        st.markdown(f"#### {name(attack)} players vs {name(defense)} defense")
        for group in ['G', 'F', 'C']:
            value, average = allowed.loc[defense, group], league[group]
            diff = value - average
            word, colour = matchup_verdict(diff, average)
            position = POSITIONS[group]
            with st.container(border=True):
                st.markdown(f"**{name(attack)} {position}** · :{colour}[**{word} matchup**]")
                st.markdown(
                    f"{name(defense)} allow opposing {position} to score "
                    f":{colour}[**{abs(diff):.1f} {STAT_WORDS[stat]} {'more' if diff > 0 else 'fewer'}**] per game "
                    f"than the average NBA defense ({value:.1f} vs {average:.1f}, all {position} together).",
                    help=f"{name(defense)} rank {rank.loc[defense, group]} of {len(rank)} in {stat_name} allowed to "
                         f"{position} (1 = allows the most). More allowed = good for {name(attack)} {position}' "
                         f"Overs; fewer = leans Under.")
links = st.columns(2)
for col, team in zip(links, [away, home]):
    if col.button(f"Open {team.upper()} in Lineup lab", key=f"lab_{team}"):
        st.session_state['lineup_team'] = team
        st.switch_page("views/lineup.py")
st.caption("Soft = that defense gives up at least 5% more than the average NBA defense (leans Over), tough = at "
           "least 5% less (leans Under). Positions are ESPN's listings. Hover ⓘ for the defense's rank.")

# --- tables ---
st.subheader(f"{stat_name} allowed by position (per game)")
st.caption(f"One row per defense: how many {STAT_WORDS[stat]} it allows per game to all opposing guards, forwards "
           f"and centers together, and how many more (green +) or fewer (red −) than the average NBA defense. "
           f"Sorted by guards; click a header to sort by another column.")
table = allowed.copy()
for group in ['G', 'F', 'C']:
    table[f'{group} vs avg'] = table[group] - league[group]
vs_avg = [f'{group} vs avg' for group in ['G', 'F', 'C']]
styled = (table.sort_values('G vs avg', ascending=False).rename(index=str.upper).style
          .map(lambda v: 'color: #16a34a' if v > 0 else 'color: #dc2626' if v < 0 else '', subset=vs_avg)
          .format({c: '{:.1f}' for c in ['G', 'F', 'C']} | {c: '{:+.1f}' for c in vs_avg} | {'games': '{:.0f}'}))
st.dataframe(styled, width='stretch',
             column_config=column_config(table.columns,
                                         tips={'games': "Games this team's defense played in the chosen period"})
             | {'_index': st.column_config.Column("defense", help="The defending team")})

st.subheader("Team ratings")
ratings = team_ratings(g).round(1)
fig = px.scatter(ratings.reset_index(), x='off_rtg', y='def_rtg', text=ratings.index.str.upper(), size='games',
                 labels={'off_rtg': 'Offensive rating: pts scored / 100 poss (right = better)',
                         'def_rtg': 'Defensive rating: pts allowed / 100 poss (up = better)'})
fig.update_yaxes(autorange='reversed')
fig.update_traces(textposition='top center')
fig.add_vline(x=ratings['off_rtg'].mean(), line_dash='dot', line_color='grey')
fig.add_hline(y=ratings['def_rtg'].mean(), line_dash='dot', line_color='grey')
for x, y, text, xanchor, yanchor in ((1, 1, "good attack, good defense", 'right', 'top'),
                                     (0, 1, "weak attack, good defense", 'left', 'top'),
                                     (1, 0, "good attack, weak defense", 'right', 'bottom'),
                                     (0, 0, "weak attack, weak defense", 'left', 'bottom')):
    fig.add_annotation(x=x, y=y, xref='paper', yref='paper', text=text, showarrow=False, xanchor=xanchor,
                       yanchor=yanchor, font=dict(color='grey'))
fig.update_layout(height=450, margin=dict(t=20))
st.plotly_chart(fig, width='stretch')
st.caption("Dotted lines = league average; bubble size = games played. Teams top-right outscore opponents; "
           "net rtg in the table below is the distance between the two ratings.")
st.dataframe(ratings.rename(index=str.upper), width='stretch',
             column_config=column_config(ratings.columns,
                                         formats={c: '%.1f' for c in ['pts', 'opp_pts', 'pace', 'off_rtg', 'def_rtg',
                                                                      'net_rtg']},
                                         tips={'games': "Games played in the chosen period"}))
st.caption("Possessions are estimated as FGA + 0.44·FTA + TO − OREB.")
