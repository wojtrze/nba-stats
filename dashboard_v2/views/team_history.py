import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import charts
from core.analysis import team_game_log
from core.data import props
from core.state import language, persist, remember
from core.ui import PAGES, kpis, page_header, stop, table
from i18n import t, value

from espn_scraper import NBA_TEAM_ABBRS, NBA_TEAM_NAMES
from loaders import filtered_logs, games as all_games
from metrics import allowed_by_position, team_ratings, team_rotation

lang = language()
seasons, season_types = page_header(t('th.title', lang), t('th.purpose', lang), with_scope=True)
g = all_games()
g = g[g['season_id'].isin(seasons) & g['season_type'].isin(season_types)
      & g['home'].isin(NBA_TEAM_ABBRS) & g['away'].isin(NBA_TEAM_ABBRS)]
logs = filtered_logs(seasons, season_types)
if g.empty:
    st.info(t('th.none', lang))
    stop()

today = props()
playing = sorted(set(today['home']) | set(today['away'])) if len(today) else []
teams = playing + sorted(t for t in NBA_TEAM_ABBRS if t not in playing)
persist('th_team', teams[0])
team = st.selectbox(t('th.team', lang), teams, key='th_team', on_change=remember, args=('th_team',),
                    format_func=lambda tm: f"{tm.upper()} – {NBA_TEAM_NAMES.get(tm, '')}",
                    help=t('th.team_help', lang))

ratings = team_ratings(g)
if team not in ratings.index:
    st.info(t('th.no_team', lang, team=team.upper()))
    stop()
r = ratings.loc[team]
rank = lambda col, best_high=True: int(ratings[col].rank(ascending=not best_high, method='min')[team])
kpis([{'label': t('th.kpi.record', lang), 'value': f"{int(r['wins'])}-{int(r['losses'])}",
       'delta': t('th.kpi.home', lang, record=r['home']), 'delta_color': 'off'},
      {'label': t('th.kpi.off', lang), 'value': f"{r['off_rtg']:.1f}",
       'delta': t('th.kpi.rank', lang, rank=rank('off_rtg'), n=len(ratings)), 'delta_color': 'off',
       'help': t('th.kpi.off_help', lang)},
      {'label': t('th.kpi.def', lang), 'value': f"{r['def_rtg']:.1f}",
       'delta': t('th.kpi.rank', lang, rank=rank('def_rtg', best_high=False), n=len(ratings)), 'delta_color': 'off',
       'help': t('th.kpi.def_help', lang)},
      {'label': t('th.kpi.net', lang), 'value': f"{r['net_rtg']:+.1f}",
       'delta': t('th.kpi.net_rank', lang, rank=rank('net_rtg')), 'delta_color': 'off'},
      {'label': t('th.kpi.pace', lang), 'value': f"{r['pace']:.1f}",
       'delta': t('th.kpi.pace_rank', lang, rank=rank('pace')), 'delta_color': 'off',
       'help': t('th.kpi.pace_help', lang)}])

log = team_game_log(g, team)
# the year too: the same opponent on the same date in two seasons would share one bar
log['label'] = log['date'].dt.strftime('%y-%m-%d') + np.where(log['location'] == 'home', ' vs ', ' @ ') + \
    log['opp'].str.upper()

results_tab, trend_tab, defense_tab, players_tab = st.tabs(
    [t(f'th.tab.{k}', lang) for k in ('results', 'trend', 'defense', 'players')])

with results_tab:
    fig = go.Figure(go.Bar(x=log['label'], y=log['margin'], marker_color=np.where(log['win'], charts.OVER, charts.UNDER),
                           customdata=np.stack([log['pts'], log['opp_pts'], log['season_type']], axis=1),
                           hovertemplate="%{x}: %{customdata[0]}–%{customdata[1]} (%{customdata[2]})<extra></extra>"))
    charts.show(charts.layout(fig, 340, t('th.margin_title', lang), xaxis=dict(type='category', tickangle=-50),
                              yaxis=dict(title=t('th.points', lang))), key='th_margin')
    split = log.groupby('location').agg(games=('win', 'size'), wins=('win', 'sum'), pts=('pts', 'mean'),
                                        opp_pts=('opp_pts', 'mean'), margin=('margin', 'mean')).reset_index()
    split['location'] = split['location'].map(lambda v: value(v, lang))
    table(split, list(split.columns), {'pts': '%.1f', 'opp_pts': '%.1f', 'margin': '%+.1f', 'wins': '%d'},
          sources={c: 'stats' for c in split.columns}, context='team')

with trend_tab:
    window = st.segmented_control(t('th.window', lang), [5, 10, 20], default=10,
                                  format_func=lambda n: t('th.window_value', lang, n=n), key='th_window') or 10
    roll = log[['off_rtg', 'def_rtg', 'pace']].rolling(window, min_periods=1).mean()
    fig = go.Figure()
    fig.add_scatter(x=log['label'], y=roll['off_rtg'], name=t('th.off_line', lang), line=dict(color=charts.OVER))
    fig.add_scatter(x=log['label'], y=roll['def_rtg'], name=t('th.def_line', lang), line=dict(color=charts.UNDER))
    fig.add_hline(y=ratings['off_rtg'].mean(), line_dash='dot', line_color='#94a3b8',
                  annotation_text=t('th.league_avg', lang))
    charts.show(charts.layout(fig, 320, t('th.rtg_title', lang, n=window),
                              xaxis=dict(type='category', tickangle=-50)), key='th_rtg')
    fig = go.Figure(go.Scatter(x=log['label'], y=roll['pace'], name='pace', line=dict(color=charts.NEUTRAL)))
    fig.add_hline(y=ratings['pace'].mean(), line_dash='dot', line_color='#94a3b8',
                  annotation_text=t('th.league_avg', lang))
    charts.show(charts.layout(fig, 260, t('th.pace_title', lang, n=window),
                              xaxis=dict(type='category', tickangle=-50)), key='th_pace')
    st.caption(t('th.trend_caption', lang))

with defense_tab:
    stat = st.segmented_control(t('th.stat_allowed', lang), ['PTS', 'REB', 'AST', '3PM', 'PA', 'PR', 'RA', 'ARP'], default='PTS',
                                format_func=lambda s: 'PRA' if s == 'ARP' else s, key='th_stat') or 'PTS'
    allowed = allowed_by_position(logs, stat)
    allowed = allowed[allowed.index.isin(NBA_TEAM_ABBRS)]
    if team not in allowed.index:
        st.caption(t('th.none', lang))
    else:
        league = allowed[['G', 'F', 'C']].mean()
        rows = []
        for group, word in (('G', 'Guards'), ('F', 'Forwards'), ('C', 'Centers')):
            allowed_value = allowed.loc[team, group]
            rows.append({'position': value(word, lang), 'allowed': allowed_value, 'league avg': league[group],
                         'vs avg %': 100 * (allowed_value / league[group] - 1),
                         'rank': int(allowed[group].rank(ascending=False, method='min')[team])})
        d = pd.DataFrame(rows)
        fig = go.Figure(go.Bar(x=d['position'], y=d['vs avg %'],
                               marker_color=np.where(d['vs avg %'] > 0, charts.OVER, charts.UNDER),
                               text=d['vs avg %'].map('{:+.0f}%'.format), textposition='outside'))
        fig.add_hline(y=0, line_color='#64748b')
        charts.show(charts.layout(fig, 280, t('th.def_title', lang, stat='PRA' if stat == 'ARP' else stat,
                                              team=team.upper()),
                                  yaxis=dict(title=t('th.vs_league', lang))), key='th_def')
        table(d, list(d.columns), {'allowed': '%.1f', 'league avg': '%.1f', 'vs avg %': '%+.0f', 'rank': '%d'},
              sources={c: 'stats' for c in d.columns}, context='team')

with players_tab:
    roster = team_rotation(logs, team, 1, 0)
    if roster.empty:
        st.caption(t('th.no_players', lang))
    else:
        team_logs = logs[(logs['team'] == team) & logs['player_id_ESPN'].isin(roster.index)]
        stats = team_logs.groupby('player_id_ESPN')[['PTS', 'REB', 'AST', '3PM']].mean()
        team_games = team_logs['game_id'].nunique()
        roster = roster.join(stats).assign(missed=lambda d: team_games - d['games'])
        roster['last_game'] = roster['last_game'].dt.date
        cols = ['name', 'position', 'games', 'starts', 'missed', 'mpg', 'PTS', 'REB', 'AST', '3PM', 'last_game']
        table(roster.reset_index(), cols, {'mpg': '%.1f', 'PTS': '%.1f', 'REB': '%.1f', 'AST': '%.1f', '3PM': '%.1f',
                                           'games': '%d', 'starts': '%d', 'missed': '%d'},
              sources={c: 'stats' for c in cols}, context='team')
        if st.button(t('th.open_lab', lang, team=team.upper())):
            st.session_state['lineup_team'] = team
            st.switch_page(PAGES['lineup'])
