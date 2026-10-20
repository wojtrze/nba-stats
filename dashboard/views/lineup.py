import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from espn_scraper import NBA_TEAM_ABBRS
from glossary import HELP, STAT_HELP, column_config, source_legend
from loaders import filtered_logs, rotowire_lineups, season_label, sidebar_filters, today_props
from metrics import lineup_scenario, rotowire_team, starting_lineup, team_rotation, with_without_matrix

STATS = ['PTS', 'REB', 'AST', '3PM', 'PA', 'PR', 'RA', 'ARP', 'STL', 'BLK', 'TO', 'MIN', 'FGA']

st.title("Lineup lab")
st.caption("Pick a starting five and who's out. The matrix shows how each player's numbers change when a teammate "
           "doesn't play; the scenario combines those changes into an estimate for tonight.")
seasons, season_types = sidebar_filters()
logs = filtered_logs(seasons, season_types)
if logs.empty:
    st.info("No games for the chosen seasons and game types.")
    st.stop()


@st.cache_data(show_spinner="Calculating with/without for every pair...")
def cached_matrix(seasons, season_types, team, ids, stat):
    team_logs = filtered_logs(list(seasons), list(season_types))
    team_logs = team_logs[team_logs['player_id_ESPN'].isin(ids)]
    return with_without_matrix(team_logs, list(ids), list(ids), stat)


# --- team ---
teams = sorted(t for t in logs['team'].unique() if t in NBA_TEAM_ABBRS)
upcoming = today_props()
lineups_rw = rotowire_lineups()
quick = sorted({t for pair in zip(upcoming['away'], upcoming['home']) for t in pair} if not upcoming.empty else set()
               | set(lineups_rw['team']))
# a team sent from another page wins; otherwise restore the last team (widget state is dropped between pages)
requested = st.session_state.pop('lineup_team', None) or st.session_state.get('_lineup_team')
if requested in teams and ('lineup_team_select' not in st.session_state or requested != st.session_state.get('_lineup_team')):
    st.session_state['lineup_team_select'] = requested
c = st.columns([1, 1, 3])
team = c[0].selectbox("Team", quick + [t for t in teams if t not in quick], format_func=str.upper, key='lineup_team_select',
                      help="Teams playing today (Superbet or RotoWire) are listed first.")
st.session_state['_lineup_team'] = team
stat = c[1].selectbox("Stat", STATS, key='lineup_stat', format_func=lambda s: f"{s} – {STAT_HELP[s]}")
with c[2].expander("Settings"):
    s = st.columns(4)
    min_games = s[0].number_input("Rotation: min games", 1, 82, 5,
                                  help="Players with fewer games for this team are left out of the matrix and bench")
    min_minutes = s[1].number_input("Rotation: min minutes", 0, 40, 10,
                                    help="Players averaging fewer minutes are left out of the matrix and bench")
    min_without = s[2].number_input("Matrix: min games without", 1, 20, 3,
                                    help="Matrix cells based on fewer games without the teammate are left empty")
    shrink = s[3].number_input("Estimate: shrink", 0, 30, 5,
                               help="Each change is weighted by n / (n + shrink), n = games without that teammate")

rotation = team_rotation(logs, team, min_games, min_minutes)
roster = team_rotation(logs, team, 1, 0)          # anyone still on the team, for the starters/out pickers
names = roster['name'].to_dict()
if rotation.empty:
    st.info(f"No players with {min_games}+ games and {min_minutes}+ minutes for {team.upper()} in the chosen games.")
    st.stop()

# --- lineup (kept per team; RotoWire's projection is the default for teams it lists today) ---
lineups = st.session_state.setdefault('lineups', {})
starters_key, out_key = f'lineup_starters_{team}', f'lineup_out_{team}'


def set_lineup(starters, out, source):
    starters = [p for p in starters if p in names][:5]
    lineups[team] = {'starters': starters, 'out': [p for p in out if p in names and p not in starters], 'source': source}
    st.session_state[starters_key], st.session_state[out_key] = lineups[team]['starters'], lineups[team]['out']


rw = rotowire_team(lineups_rw, team)
rw_listed = lineups_rw[lineups_rw['team'] == team]
if team not in lineups:
    if rw['starters']:
        set_lineup(rw['starters'], rw['out'], 'rotowire')
    else:
        set_lineup(starting_lineup(logs, team, 'last'), [], 'last game')
for key, field in ((starters_key, 'starters'), (out_key, 'out')):
    if key not in st.session_state:   # widget state is dropped when leaving the page; restore it
        st.session_state[key] = lineups[team][field]


def manual_change():
    set_lineup(st.session_state[starters_key], st.session_state[out_key], 'manual')


b = st.columns([1, 1, 1, 3])
b[0].button("RotoWire projection", on_click=set_lineup, args=(rw['starters'], rw['out'], 'rotowire'),
            disabled=not rw['starters'], help="Tonight's expected starters and players out (0-25% to play) "
                                              "from RotoWire's lineups page.")
b[1].button("Last game's starters", on_click=set_lineup, args=(starting_lineup(logs, team, 'last'), [], 'last game'))
b[2].button("Most frequent starters (last 10)", on_click=set_lineup,
            args=(starting_lineup(logs, team, 'frequent'), [], 'frequent'))
b[3].caption(f"Lineup source: **{'📋 RotoWire' if lineups[team]['source'] == 'rotowire' else lineups[team]['source']}**. The last game is sometimes a rest game; "
             f"switch to the most frequent starters if it looks off.")

if not rw_listed.empty:
    status = rw_listed['lineup_status'].iloc[0] or 'listed'
    notes = [f"{r['name']} ({r['injury'] or '?'}, {r['play_pct']:.0f}%)" for _, r in rw_listed.iterrows()
             if r['role'] == 'may_not_play']
    unmatched = rw_listed.loc[rw_listed['player_id_ESPN'].isna(), 'name'].tolist()
    st.caption(f"📋 RotoWire: **{status}** lineup. May not play: {', '.join(notes) or '–'}"
               + (f". No games in the data for: {', '.join(unmatched)}" if unmatched else ""))

label = lambda p: f"{names.get(p, p)} ({roster['position'].get(p, '')}, {roster['mpg'].get(p, 0):.0f} mpg)"
l1, l2 = st.columns(2)
starters = l1.multiselect("Starting five", list(roster.index), key=starters_key, format_func=label, max_selections=5,
                          on_change=manual_change, help="Tonight's starters. Used for the exact-match games: team "
                                                        "games where all five started together.")
st.session_state[out_key] = [p for p in st.session_state[out_key] if p not in starters]
out = l2.multiselect("Out tonight", [p for p in roster.index if p not in starters], key=out_key, format_func=label,
                     on_change=manual_change, help="Players missing tonight. Their with/without changes are added "
                                                   "to everyone else's estimate in Tonight's scenario.")
if len(starters) < 5:
    st.warning(f"Pick 5 starters ({len(starters)} selected).")
bench = [p for p in rotation.index if p not in starters and p not in out]
st.caption("Bench (available): " + (", ".join(names[p] for p in bench) or "–"))

# --- matrix ---
st.subheader(f"With / without matrix – {stat}")
rows = starters + bench
cols = list(dict.fromkeys(starters + bench + [p for p in out if p in rotation.index or p in names]))
ids = tuple(sorted(set(rows) | set(cols)))
m = cached_matrix(tuple(seasons), tuple(season_types), team, ids, stat)
relative = st.toggle("Show as % of the player's usual average")
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
fig = go.Figure(go.Heatmap(
    z=shown.values, x=col_labels, y=row_labels, colorscale='RdYlGn', zmid=0, zmin=-limit, zmax=limit,
    text=np.where(np.isnan(shown.values), '', np.vectorize(lambda v: f"{v:+.0f}%" if relative else f"{v:+.1f}")(shown.fillna(0).values)),
    texttemplate='%{text}', hovertext=hover, hoverinfo='text', xgap=2, ygap=2,
    colorbar=dict(title='% change' if relative else 'change')))
fig.update_layout(height=60 + 38 * len(rows), margin=dict(l=10, r=10, t=10, b=10),
                  yaxis=dict(autorange='reversed'), xaxis=dict(side='top', tickangle=-35))
st.plotly_chart(fig, width='stretch')
st.caption(f"Row player's {stat} when the column player is OUT minus when they play. ★ = in the starting five. "
           f"Only games inside the column player's time on the team count. Empty cells: fewer than {min_without} "
           f"games without that player.")

# --- scenario ---
st.subheader("Tonight's scenario")
if not out:
    st.caption("Nobody is out, so every estimate equals the usual average. Tick Out next to a player to see how the "
               "others' numbers shift.")
scenario = lineup_scenario(logs[logs['player_id_ESPN'].isin(ids)], team, starters, out, bench, stat, shrink,
                           matrix={k: v.astype(float) for k, v in m.items()})
# out players stay in the table (ticked, no numbers) so they can be unticked here too
out_rows = pd.DataFrame({'player_id_ESPN': out, 'name': [names.get(p, str(p)) for p in out], 'role': 'Out'})
table = pd.concat([scenario, out_rows], ignore_index=True)
table.insert(0, 'Out', table['player_id_ESPN'].isin(out))
table['signal'] = np.select([table['change'] >= 1, table['change'] <= -1], ['🟢', '🔴'], '')
# the estimate for tonight first, then what it's built from
table = table[['player_id_ESPN', 'Out', 'name', 'role', 'estimate', 'change', 'signal', 'confidence', 'usual',
               'games', 'exact match', 'exact games', 'usual MIN', 'exact MIN']]
row_ids = table['player_id_ESPN'].tolist()
editor_version = st.session_state.setdefault(f'scenario_version_{team}', 0)
editor_key = f'scenario_{team}_{editor_version}'


def toggle_out():
    """Apply the ticked/unticked Out boxes; a starter marked out leaves the starting five."""
    edits = st.session_state[editor_key]['edited_rows']
    new_out = list(out)
    for i, change in edits.items():
        p = row_ids[int(i)]
        if change.get('Out') and p not in new_out:
            new_out.append(p)
        elif change.get('Out') is False and p in new_out:
            new_out.remove(p)
    set_lineup([p for p in starters if p not in new_out], new_out, 'manual')
    st.session_state[f'scenario_version_{team}'] += 1   # fresh editor, so old ticks don't linger


shown = table.drop(columns='player_id_ESPN')
st.caption(source_legend(['stats']) + " — every number here is calculated from the scraped games")
st.data_editor(shown, hide_index=True, width='stretch', key=editor_key, on_change=toggle_out,
               disabled=[c for c in shown.columns if c != 'Out'],
               column_config=column_config(
                   shown.columns,
                   formats={'usual': '%.1f', 'exact match': '%.1f', 'estimate': '%.1f', 'change': '%+.1f',
                            'usual MIN': '%.1f', 'exact MIN': '%.1f', 'games': '%d', 'exact games': '%d'},
                   tips={'games': f"Games the player played for {team.upper()} in the chosen seasons",
                         'usual': f"Player's average {stat} for {team.upper()} in the chosen games",
                         'signal': f"🟢 estimate at least 1 {stat} above usual, 🔴 at least 1 below"},
                   base={'Out': st.column_config.CheckboxColumn(help=HELP['Out'])},
                   sources={c: 'stats' for c in ['estimate', 'change', 'signal', 'confidence', 'usual', 'games',
                                                 'exact match', 'exact games', 'usual MIN', 'exact MIN']}))
st.caption(f"Tick **Out** to take a player out, untick to bring them back. Hover a column header for what it means. "
           f"Games used: {season_label(min(seasons))}–{season_label(max(seasons))}, {', '.join(season_types)}.")

p1, p2 = st.columns([3, 1])
open_id = p1.selectbox("Player details", scenario['player_id_ESPN'], format_func=lambda p: names.get(p, str(p)),
                       index=None, placeholder="Pick a player to open their page...", label_visibility='collapsed')
if p2.button("Open player page", disabled=open_id is None):
    st.session_state['player_preset'] = {'player_id': open_id, 'stat': stat if stat != 'FGA' else 'PTS',
                                         'line': None, 'teammate': out[0] if out else None}
    st.switch_page("views/player.py")
