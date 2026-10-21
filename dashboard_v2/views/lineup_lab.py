import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import charts
from core.data import lineups as rotowire_lineups, props
from core.state import persist, remember
from core.ui import PAGES, page_header, stop
from espn_scraper import NBA_TEAM_ABBRS, NBA_TEAM_NAMES
from glossary import HELP, STAT_HELP, column_config, source_legend
from loaders import filtered_logs, player_logs
from metrics import lineup_scenario, rotowire_team, starting_lineup, team_rotation, with_without_matrix

STATS = ['PTS', 'REB', 'AST', '3PM', 'PA', 'PR', 'RA', 'ARP', 'STL', 'BLK', 'TO', 'MIN', 'FGA']
SOURCES = {'rotowire': "📋 RotoWire tonight", 'last': "Last game", 'frequent': "Most frequent (last 10)",
           'custom': "Custom"}

seasons, season_types = page_header(
    "Lineup lab", "How each player's numbers change when a teammate doesn't play, for any team, with or without "
                  "an expected lineup; then an estimate for a lineup you pick.", with_scope=True)

# --- team and data ---
today = props()
lineups_rw = rotowire_lineups()
playing = sorted(({t for pair in zip(today['away'], today['home']) for t in pair} if len(today) else set())
                 | set(lineups_rw['team']))
teams = playing + sorted(t for t in NBA_TEAM_ABBRS if t not in playing)
persist('ll_team', teams[0])
requested = st.session_state.pop('lineup_team', None)
if requested in teams:
    st.session_state['ll_team'] = requested
    remember('ll_team')
persist('ll_stat', 'PTS')
persist('ll_all_seasons', True)
c = st.columns([2, 2, 2, 1], vertical_alignment='bottom')
team = c[0].selectbox("Team", teams, key='ll_team', on_change=remember, args=('ll_team',),
                      format_func=lambda t: f"{t.upper()} – {NBA_TEAM_NAMES.get(t, '')}",
                      help="Teams playing today (Superbet or RotoWire) are listed first")
stat = c[1].selectbox("Stat", STATS, key='ll_stat', on_change=remember, args=('ll_stat',),
                      format_func=lambda s: f"{s} – {STAT_HELP[s]}")
all_seasons = c[2].toggle("Use every stored season", key='ll_all_seasons', on_change=remember,
                          args=('ll_all_seasons',),
                          help="Early in the season there are too few games without anyone. Earlier seasons only "
                               "count while both players were on the team.")
with c[3].popover("Settings", width='stretch'):
    min_games = st.number_input("Rotation: min games", 1, 82, 5, help="Fewer games for this team = left out")
    min_minutes = st.number_input("Rotation: min minutes", 0, 40, 10, help="Lower average = left out")
    min_without = st.number_input("Matrix: min games without", 1, 20, 3,
                                  help="Cells based on fewer games without the teammate stay empty")
    shrink = st.number_input("Estimate: shrink", 0, 30, 5,
                             help="Each change is weighted by n / (n + shrink), n = games without that teammate")

logs = player_logs()[player_logs()['season_type'].isin(season_types)] if all_seasons else \
    filtered_logs(seasons, season_types)
rotation = team_rotation(logs, team, min_games, min_minutes)
roster = team_rotation(logs, team, 1, 0)
names = roster['name'].to_dict()
if rotation.empty:
    st.info(f"No players with {min_games}+ games and {min_minutes}+ minutes for {team.upper()} in these games.")
    stop()


@st.cache_data(show_spinner="Calculating with/without for every pair...")
def matrix(all_seasons, seasons, season_types, ids, stat):
    source = player_logs()[player_logs()['season_type'].isin(season_types)] if all_seasons else \
        filtered_logs(list(seasons), list(season_types))
    return with_without_matrix(source[source['player_id_ESPN'].isin(ids)], list(ids), list(ids), stat)


# --- the lineup: RotoWire's when it lists the team, otherwise picked from the stored games ---
rw = rotowire_team(lineups_rw, team)
choices = {'last': (starting_lineup(logs, team, 'last'), []),
           'frequent': (starting_lineup(logs, team, 'frequent'), [])}
if rw['starters']:
    choices = {'rotowire': (rw['starters'], rw['out'])} | choices
saved = st.session_state.setdefault('ll_lineups', {})
source_key, starters_key, out_key = f'll_source_{team}', f'll_starters_{team}', f'll_out_{team}'


def set_lineup(source, starters, out):
    starters = [p for p in starters if p in names][:5]
    saved[team] = {'source': source, 'starters': starters,
                   'out': [p for p in out if p in names and p not in starters]}
    st.session_state[source_key] = source
    st.session_state[starters_key], st.session_state[out_key] = saved[team]['starters'], saved[team]['out']


def pick_source():
    source = st.session_state[source_key]
    if source in choices:
        set_lineup(source, *choices[source])
    else:   # 'custom' keeps the current picks; a click on the selected option clears it, keep it then too
        set_lineup('custom', saved[team]['starters'], saved[team]['out'])


def manual_change():
    set_lineup('custom', st.session_state[starters_key], st.session_state[out_key])


if team not in saved or saved[team]['source'] not in list(choices) + ['custom']:
    set_lineup(next(iter(choices)), *choices[next(iter(choices))])
for key, value in ((source_key, saved[team]['source']), (starters_key, saved[team]['starters']),
                   (out_key, saved[team]['out'])):
    if key not in st.session_state:   # widget state is dropped when leaving the page
        st.session_state[key] = value

with st.container(border=True):
    st.segmented_control("Lineup from", list(choices) + ['custom'], format_func=SOURCES.get, key=source_key,
                         on_change=pick_source,
                         help="RotoWire's expected starters and out players when it lists the team today; "
                              "otherwise the last game's starters or the most frequent starters of the last 10 games")
    listed = lineups_rw[lineups_rw['team'] == team]
    if listed.empty:
        st.caption(f"📋 RotoWire lists no lineup for {team.upper()} today, so the lineup comes from the stored "
                   f"games. Pick who's out yourself.")
    else:
        notes = [f"{r['name']} ({r['injury'] or '?'}, {r['play_pct']:.0f}%)" for _, r in listed.iterrows()
                 if r['role'] == 'may_not_play']
        st.caption(f"📋 RotoWire: **{listed['lineup_status'].iloc[0] or 'listed'}** lineup. May not play: "
                   f"{', '.join(notes) or '–'}")
    label = lambda p: f"{names.get(p, p)} ({roster['position'].get(p, '')}, {roster['mpg'].get(p, 0):.0f} mpg)"
    l1, l2 = st.columns(2)
    starters = l1.multiselect("Starting five", list(roster.index), key=starters_key, format_func=label,
                              max_selections=5, on_change=manual_change,
                              help="Used for the exact-match games: team games where all five started")
    st.session_state[out_key] = [p for p in st.session_state[out_key] if p not in starters]
    out = l2.multiselect("Out", [p for p in roster.index if p not in starters], key=out_key, format_func=label,
                         on_change=manual_change, help="Missing players: their with/without changes are added to "
                                                       "everyone else's estimate")
    if len(starters) < 5:
        st.warning(f"Pick 5 starters ({len(starters)} selected).")
bench = [p for p in rotation.index if p not in starters and p not in out]

# --- the full matrix ---
st.subheader(f"With / without matrix · {stat}")
ids = tuple(sorted(set(rotation.index) | set(starters) | set(out)))
m = matrix(all_seasons, tuple(seasons), tuple(season_types), ids, stat)
rows = list(dict.fromkeys(starters + [p for p in rotation.index if p not in out]))
cols = list(dict.fromkeys(rows + out))
relative = st.toggle("Show as % of the player's usual average", key='ll_relative')
delta = m['delta'].loc[rows, cols].astype(float)
n_without = m['n_without'].loc[rows, cols]
usual = logs[logs['team'] == team].groupby('player_id_ESPN')[stat].mean()
if relative:
    delta = delta.div(usual.reindex(rows), axis=0) * 100
shown = delta.where(n_without >= min_without)
col_labels = [names.get(p, str(p)) + (" (OUT)" if p in out else "") for p in cols]
row_labels = [names.get(p, str(p)) + (" ★" if p in starters else "") for p in rows]
hover = [[f"{names.get(r)} when {names.get(c_)} is out<br>"
          f"with: {m['with'].loc[r, c_]:.1f} in {m['n_with'].loc[r, c_]:.0f} games<br>"
          f"without: {m['without'].loc[r, c_]:.1f} in {m['n_without'].loc[r, c_]:.0f} games"
          if r != c_ and m['n_without'].loc[r, c_] > 0 else
          ("" if r == c_ else f"{names.get(c_)} never missed a game {names.get(r)} played")
          for c_ in cols] for r in rows]
limit = np.nanmax(np.abs(shown.values)) if np.isfinite(shown.values).any() else 1
text = np.vectorize(lambda v: f"{v:+.0f}%" if relative else f"{v:+.1f}")(shown.fillna(0).values)
fig = go.Figure(go.Heatmap(z=shown.values, x=col_labels, y=row_labels, colorscale='RdYlGn', zmid=0, zmin=-limit,
                           zmax=limit, text=np.where(np.isnan(shown.values), '', text), texttemplate='%{text}',
                           hovertext=hover, hoverinfo='text', xgap=2, ygap=2,
                           colorbar=dict(title='% change' if relative else 'change')))
charts.show(charts.layout(fig, 80 + 34 * len(rows), yaxis=dict(autorange='reversed'),
                          xaxis=dict(side='top', tickangle=-35)), key='ll_matrix')
st.caption(f"Each cell: the row player's {stat} when the column player is **out** minus when they play (green = "
           f"more). ★ = starting five. Empty: fewer than {min_without} games without that player. Only games inside "
           f"the column player's time on the team count. Hover a cell for the averages and games behind it.")

# --- the scenario ---
st.subheader("Estimate for this lineup")
if not out:
    st.caption("Nobody is out, so every estimate equals the usual average. Tick Out to see how the others shift.")
scenario = lineup_scenario(logs[logs['player_id_ESPN'].isin(ids)], team, starters, out, bench, stat, shrink,
                           matrix={k: v.astype(float) for k, v in m.items()})
out_rows = pd.DataFrame({'player_id_ESPN': out, 'name': [names.get(p, str(p)) for p in out], 'role': 'Out'})
scenario_table = pd.concat([scenario, out_rows], ignore_index=True)
scenario_table.insert(0, 'Out', scenario_table['player_id_ESPN'].isin(out))
scenario_table['signal'] = np.select([scenario_table['change'] >= 1, scenario_table['change'] <= -1], ['🟢', '🔴'], '')
scenario_table = scenario_table[['player_id_ESPN', 'Out', 'name', 'role', 'estimate', 'change', 'signal',
                                 'confidence', 'usual', 'games', 'exact match', 'exact games', 'usual MIN',
                                 'exact MIN']]
row_ids = scenario_table['player_id_ESPN'].tolist()
version = st.session_state.setdefault(f'll_editor_{team}', 0)
editor_key = f'll_scenario_{team}_{version}'


def toggle_out():
    """Apply ticked/unticked Out boxes; a starter marked out leaves the starting five."""
    new_out = list(out)
    for i, change in st.session_state[editor_key]['edited_rows'].items():
        p = row_ids[int(i)]
        if change.get('Out') and p not in new_out:
            new_out.append(p)
        elif change.get('Out') is False and p in new_out:
            new_out.remove(p)
    set_lineup('custom', [p for p in starters if p not in new_out], new_out)
    st.session_state[f'll_editor_{team}'] += 1   # a fresh editor, so old ticks don't linger


shown_table = scenario_table.drop(columns='player_id_ESPN')
st.caption(source_legend(['stats']) + " — calculated from the scraped games")
st.data_editor(shown_table, hide_index=True, width='stretch', key=editor_key, on_change=toggle_out,
               disabled=[c_ for c_ in shown_table.columns if c_ != 'Out'],
               column_config=column_config(
                   shown_table.columns,
                   formats={'usual': '%.1f', 'exact match': '%.1f', 'estimate': '%.1f', 'change': '%+.1f',
                            'usual MIN': '%.1f', 'exact MIN': '%.1f', 'games': '%d', 'exact games': '%d'},
                   tips={'games': f"Games the player played for {team.upper()}",
                         'usual': f"Player's average {stat} for {team.upper()}",
                         'signal': f"🟢 estimate at least 1 {stat} above usual, 🔴 at least 1 below"},
                   base={'Out': st.column_config.CheckboxColumn(help=HELP['Out'])},
                   sources={c_: 'stats' for c_ in ['estimate', 'change', 'signal', 'confidence', 'usual', 'games',
                                                   'exact match', 'exact games', 'usual MIN', 'exact MIN']}))
st.caption("Tick **Out** to take a player out, untick to bring them back. estimate = usual + each out player's "
           "change, shrunk when based on few games; exact match = the average in games with exactly this situation.")

p1, p2 = st.columns([3, 1])
open_id = p1.selectbox("Player details", scenario['player_id_ESPN'], format_func=lambda p: names.get(p, str(p)),
                       index=None, placeholder="Open a player's history...", label_visibility='collapsed')
if p2.button("Open in Player history", disabled=open_id is None, width='stretch'):
    st.session_state['player_preset'] = {'player_id': open_id, 'stat': stat if stat != 'FGA' else 'PTS', 'line': None}
    st.switch_page(PAGES['player'])
