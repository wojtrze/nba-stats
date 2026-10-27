import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import charts
from core.data import lineups as rotowire_lineups, props
from core.state import language, persist, remember
from core.ui import PAGES, page_header, stop
from espn_scraper import NBA_TEAM_ABBRS, NBA_TEAM_NAMES
from glossary import column_config, source_legend
import i18n
from i18n import STAT_NAMES, t
from loaders import filtered_logs, player_logs
from metrics import lineup_scenario, rotowire_team, starting_lineup, team_rotation, with_without_matrix

STATS = ['PTS', 'REB', 'AST', '3PM', 'PA', 'PR', 'RA', 'ARP', 'STL', 'BLK', 'TO', 'MIN', 'FGA']
lang = language()
SOURCES = {key: t(f'll.source.{key}', lang) for key in ('rotowire', 'last', 'frequent', 'custom')}

seasons, season_types = page_header(t('ll.title', lang), t('ll.purpose', lang), with_scope=True)

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
team = c[0].selectbox(t('ll.team', lang), teams, key='ll_team', on_change=remember, args=('ll_team',),
                      format_func=lambda tm: f"{tm.upper()} – {NBA_TEAM_NAMES.get(tm, '')}",
                      help=t('ll.team_help', lang))
stat = c[1].selectbox(t('ll.stat', lang), STATS, key='ll_stat', on_change=remember, args=('ll_stat',),
                      format_func=lambda s: f"{s} – {STAT_NAMES[s][lang]}")
all_seasons = c[2].toggle(t('ll.all_seasons', lang), key='ll_all_seasons', on_change=remember,
                          args=('ll_all_seasons',), help=t('ll.all_seasons_help', lang))
with c[3].popover(t('ll.settings', lang), width='stretch'):
    min_games = st.number_input(t('ll.min_games', lang), 1, 82, 5, help=t('ll.min_games_help', lang))
    min_minutes = st.number_input(t('ll.min_minutes', lang), 0, 40, 10, help=t('ll.min_minutes_help', lang))
    min_without = st.number_input(t('ll.min_without', lang), 1, 20, 3, help=t('ll.min_without_help', lang))
    shrink = st.number_input(t('ll.shrink', lang), 0, 30, 5, help=t('ll.shrink_help', lang))

logs = player_logs()[player_logs()['season_type'].isin(season_types)] if all_seasons else \
    filtered_logs(seasons, season_types)
rotation = team_rotation(logs, team, min_games, min_minutes)
roster = team_rotation(logs, team, 1, 0)
names = roster['name'].to_dict()
if rotation.empty:
    st.info(t('ll.no_rotation', lang, games=min_games, minutes=min_minutes, team=team.upper()))
    stop()


@st.cache_data(show_spinner=False)
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
    st.segmented_control(t('ll.lineup_from', lang), list(choices) + ['custom'], format_func=SOURCES.get,
                         key=source_key, on_change=pick_source, help=t('ll.lineup_from_help', lang))
    listed = lineups_rw[lineups_rw['team'] == team]
    if listed.empty:
        st.caption(t('ll.no_rotowire', lang, team=team.upper()))
    else:
        notes = [f"{r['name']} ({r['injury'] or '?'}, {r['play_pct']:.0f}%)" for _, r in listed.iterrows()
                 if r['role'] == 'may_not_play']
        status = listed['lineup_status'].iloc[0] or 'listed'
        status = t(f'overview.{status}', lang) if status in ('confirmed', 'expected') else status
        st.caption(t('ll.rotowire', lang, status=status, names=', '.join(notes) or '–'))
    label = lambda p: f"{names.get(p, p)} ({roster['position'].get(p, '')}, {roster['mpg'].get(p, 0):.0f} mpg)"
    l1, l2 = st.columns(2)
    starters = l1.multiselect(t('ll.starting', lang), list(roster.index), key=starters_key, format_func=label,
                              max_selections=5, on_change=manual_change, help=t('ll.starting_help', lang))
    st.session_state[out_key] = [p for p in st.session_state[out_key] if p not in starters]
    out = l2.multiselect(t('ll.out', lang), [p for p in roster.index if p not in starters], key=out_key,
                         format_func=label, on_change=manual_change, help=t('ll.out_help', lang))
    if len(starters) < 5:
        st.warning(t('ll.pick_five', lang, n=len(starters)))
bench = [p for p in rotation.index if p not in starters and p not in out]

# --- the full matrix ---
st.subheader(t('ll.matrix', lang, stat=stat))
ids = tuple(sorted(set(rotation.index) | set(starters) | set(out)))
with st.spinner(t('ll.matrix_spinner', lang)):
    m = matrix(all_seasons, tuple(seasons), tuple(season_types), ids, stat)
rows = list(dict.fromkeys(starters + [p for p in rotation.index if p not in out]))
cols = list(dict.fromkeys(rows + out))
relative = st.toggle(t('ll.relative', lang), key='ll_relative')
delta = m['delta'].loc[rows, cols].astype(float)
n_without = m['n_without'].loc[rows, cols]
usual = logs[logs['team'] == team].groupby('player_id_ESPN')[stat].mean()
if relative:
    delta = delta.div(usual.reindex(rows), axis=0) * 100
shown = delta.where(n_without >= min_without)
col_labels = [names.get(p, str(p)) + (t('ll.out_mark', lang) if p in out else "") for p in cols]
row_labels = [names.get(p, str(p)) + (" ★" if p in starters else "") for p in rows]
hover = [[t('ll.hover', lang, row=names.get(r), col=names.get(c_), with_=m['with'].loc[r, c_],
            n_with=m['n_with'].loc[r, c_], without=m['without'].loc[r, c_], n_without=m['n_without'].loc[r, c_])
          if r != c_ and m['n_without'].loc[r, c_] > 0 else
          ("" if r == c_ else t('ll.never', lang, col=names.get(c_), row=names.get(r)))
          for c_ in cols] for r in rows]
limit = np.nanmax(np.abs(shown.values)) if np.isfinite(shown.values).any() else 1
text = np.vectorize(lambda v: f"{v:+.0f}%" if relative else f"{v:+.1f}")(shown.fillna(0).values)
fig = go.Figure(go.Heatmap(z=shown.values, x=col_labels, y=row_labels, colorscale='RdYlGn', zmid=0, zmin=-limit,
                           zmax=limit, text=np.where(np.isnan(shown.values), '', text), texttemplate='%{text}',
                           hovertext=hover, hoverinfo='text', xgap=2, ygap=2,
                           colorbar=dict(title=t('ll.colorbar_pct' if relative else 'll.colorbar', lang))))
charts.show(charts.layout(fig, 80 + 34 * len(rows), yaxis=dict(autorange='reversed'),
                          xaxis=dict(side='top', tickangle=-35)), key='ll_matrix')
st.caption(t('ll.matrix_caption', lang, stat=stat, n=min_without))

# --- the scenario ---
st.subheader(t('ll.estimate', lang))
if not out:
    st.caption(t('ll.nobody_out', lang))
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
shown_table = shown_table.assign(role=shown_table['role'].map(lambda v: i18n.value(v, lang)),
                                 confidence=shown_table['confidence'].map(lambda v: i18n.value(v, lang)))
st.caption(source_legend(['stats']) + t('ll.calculated', lang))
st.data_editor(shown_table, hide_index=True, width='stretch', key=editor_key, on_change=toggle_out,
               disabled=[c_ for c_ in shown_table.columns if c_ != 'Out'],
               column_config=column_config(
                   shown_table.columns,
                   formats={'usual': '%.1f', 'exact match': '%.1f', 'estimate': '%.1f', 'change': '%+.1f',
                            'usual MIN': '%.1f', 'exact MIN': '%.1f', 'games': '%d', 'exact games': '%d'},
                   base={'Out': st.column_config.CheckboxColumn(i18n.label('Out', lang), help=i18n.tooltip('Out', lang))},
                   sources={c_: 'stats' for c_ in ['estimate', 'change', 'signal', 'confidence', 'usual', 'games',
                                                   'exact match', 'exact games', 'usual MIN', 'exact MIN']},
                   lang=lang, context='lineup'))
st.caption(t('ll.scenario_caption', lang))

p1, p2 = st.columns([3, 1])
open_id = p1.selectbox(t('ll.open', lang), scenario['player_id_ESPN'], format_func=lambda p: names.get(p, str(p)),
                       index=None, placeholder=t('ll.open_player', lang), label_visibility='collapsed')
if p2.button(t('ll.open', lang), disabled=open_id is None, width='stretch'):
    st.session_state['player_preset'] = {'player_id': open_id, 'stat': stat if stat != 'FGA' else 'PTS', 'line': None}
    st.switch_page(PAGES['player'])
