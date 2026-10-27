import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import charts
from core.state import language, persist, remember
from core.ui import PAGES, kpis, page_header, stop
from glossary import column_config
from i18n import STAT_NAMES, label, t, value
from loaders import filtered_logs, player_logs, season_label
from metrics import STATS, line_percentile, player_summary, splits, teammates, with_without

lang = language()
seasons, season_types = page_header(t('ph.title', lang), t('ph.purpose', lang), with_scope=True)
logs = filtered_logs(seasons, season_types)
every = player_logs()
every = every[every['season_type'].isin(season_types)]
if every.empty:
    st.info(t('ph.no_games', lang))
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
player_id = c[0].selectbox(t('ph.player', lang), list(labels), format_func=labels.get, key='ph_player', index=None,
                           placeholder=t('ph.type_name', lang), on_change=remember, args=('ph_player',))
stat = c[1].selectbox(t('ph.stat', lang), STATS, key='ph_stat', format_func=lambda s: f"{s} – {STAT_NAMES[s][lang]}",
                      on_change=remember, args=('ph_stat',))
line = c[2].number_input(t('ph.line', lang), min_value=0.0, step=0.5, key='ph_line',
                         placeholder=t('ph.line_example', lang), on_change=remember, args=('ph_line',),
                         help=t('ph.line_help', lang))
if player_id is None:
    st.info(t('ph.pick', lang), icon="👆")
    stop()

games = logs[logs['player_id_ESPN'] == player_id].sort_values('Date')
career = every[every['player_id_ESPN'] == player_id].sort_values('Date')
if games.empty:
    st.warning(t('ph.no_scope', lang, name=players.loc[player_id, 'name']))
else:
    s = player_summary(games, stat, line)
    items = [{'label': t('ph.kpi.avg', lang), 'value': f"{s['avg']:.1f}",
              'help': t('ph.kpi.avg_help', lang, n=s['games'])},
             {'label': t('ph.kpi.last5', lang), 'value': f"{s['avg_last5']:.1f}",
              'delta': f"{s['avg_last5'] - s['avg']:+.1f}", 'help': t('ph.kpi.last5_help', lang)},
             {'label': t('ph.kpi.last10', lang), 'value': f"{s['avg_last10']:.1f}",
              'delta': f"{s['avg_last10'] - s['avg']:+.1f}"},
             {'label': t('ph.kpi.median', lang), 'value': f"{s['median']:.1f}", 'help': t('ph.kpi.median_help', lang)},
             {'label': t('ph.kpi.minutes', lang), 'value': f"{s['min_avg']:.1f}",
              'delta': f"{s['min_avg_last5'] - s['min_avg']:+.1f} L5", 'help': t('ph.kpi.minutes_help', lang)}]
    if line is not None:
        items.append({'label': t('ph.kpi.over', lang, line=line), 'value': f"{100 * s['over']:.0f}%",
                      'delta': f"{100 * s['over_last10']:.0f}% L10", 'delta_color': 'off',
                      'help': t('ph.kpi.over_help', lang, pct=s['percentile'])})
    kpis(items)
    if c[0].button(t('ph.open_lab', lang), key='ph_lab'):
        st.session_state['lineup_team'] = games['team'].iloc[-1]
        st.switch_page(PAGES['lineup'])

log_tab, dist_tab, trend_tab, split_tab, opp_tab, mate_tab, table_tab = st.tabs(
    [t(f'ph.tab.{k}', lang) for k in ('log', 'dist', 'trend', 'splits', 'opp', 'mates', 'all')])

with log_tab:
    if games.empty:
        st.caption(t('ph.none', lang))
    else:
        n = st.segmented_control(t('ph.games', lang), [10, 20, 40, 0], default=20,
                                 format_func=lambda v: t('ph.last_n', lang, n=v) if v else t('ph.all', lang),
                                 key='ph_last')
        charts.show(charts.game_log(games, stat, line, last=n or None, minutes=True,
                                    title=t('ph.log_title', lang, stat=stat)
                                    + (t('ph.vs_line', lang) if line is not None else "")), key='ph_log')
        st.caption(t('ph.log_caption', lang))

with dist_tab:
    if games.empty:
        st.caption(t('ph.none', lang))
    else:
        left, right = st.columns([3, 2])
        with left:
            charts.show(charts.distribution(games[stat], stat, line, t('ph.dist_title', lang, stat=stat)),
                        key='ph_dist')
        with right:
            values = games[stat]
            q = values.quantile([0.1, 0.3, 0.5, 0.7, 0.9])
            st.markdown(t('ph.percentiles', lang))
            pct = pd.DataFrame({'percentile': [t(f'ph.pct.{p}', lang) for p in (10, 30, 50, 70, 90)],
                                stat: q.values})
            st.dataframe(pct, hide_index=True, width='stretch',
                         column_config=column_config(pct.columns, {stat: '%.1f'}, lang=lang, context='research'))
            st.caption(t('ph.pct_caption', lang)
                       + (t('ph.pct_line', lang, pct=line_percentile(values, line)) if line is not None else ""))

with trend_tab:
    st.caption(t('ph.trend_caption', lang))
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
                               hovertemplate=t('ph.season_hover', lang) + "<extra></extra>"))
        if line is not None:
            fig.add_hline(y=line, line_dash='dash', annotation_text=t('ph.line_label', lang, line=line))
        charts.show(charts.layout(fig, 300, t('ph.per_season', lang, stat=stat)), key='ph_season')
    with right:
        fig = go.Figure(go.Scatter(x=monthly['month'], y=monthly['avg'], mode='lines+markers',
                                   line=dict(color=charts.AVERAGE), customdata=monthly['games'],
                                   hovertemplate=t('ph.month_hover', lang) + "<extra></extra>"))
        charts.show(charts.layout(fig, 300, t('ph.per_month', lang, stat=stat)), key='ph_month')

with split_tab:
    if games.empty:
        st.caption(t('ph.none', lang))
    else:
        sp = splits(games, stat, line)
        sp = sp.assign(split=sp['split'].map(lambda v: value(v, lang)),
                       value=sp['value'].astype(str).map(lambda v: value(v, lang)))
        fig = go.Figure(go.Bar(x=sp['avg'], y=sp['split'] + ': ' + sp['value'], orientation='h',
                               marker_color=charts.NEUTRAL, text=sp['avg'].map('{:.1f}'.format) + ' (' +
                               sp['games'].astype(str) + f" {t('ph.games_short', lang)})", textposition='outside'))
        fig.add_vline(x=games[stat].mean(), line_color=charts.AVERAGE, annotation_text=t('ph.overall', lang))
        if line is not None:
            fig.add_vline(x=line, line_dash='dash', annotation_text=t('ph.line_label', lang, line=line))
        charts.show(charts.layout(fig, 60 + 30 * len(sp), t('ph.by_situation', lang, stat=stat),
                                  yaxis=dict(autorange='reversed')), key='ph_splits')
        st.dataframe(sp, hide_index=True, width='stretch',
                     column_config=column_config(sp.columns, {'avg': '%.1f', 'median': '%.1f', 'over %': '%.0f'},
                                                 lang=lang, context='research'))

with opp_tab:
    vs = career.groupby('OPP').agg(games=(stat, 'size'), avg=(stat, 'mean'), last=('Date', 'max')).reset_index()
    vs = vs.sort_values('avg', ascending=False)
    fig = go.Figure(go.Bar(x=vs['OPP'], y=vs['avg'], marker_color=np.where(vs['avg'] >= career[stat].mean(),
                                                                          charts.OVER, charts.UNDER),
                           customdata=vs['games'], hovertemplate=t('ph.opp_hover', lang) + "<extra></extra>"))
    fig.add_hline(y=career[stat].mean(), line_color=charts.AVERAGE, annotation_text=t('ph.career_avg', lang))
    charts.show(charts.layout(fig, 320, t('ph.opp_title', lang, stat=stat)), key='ph_opp')
    st.caption(t('ph.opp_caption', lang))

with mate_tab:
    mates = teammates(career, player_id)
    if mates.empty:
        st.caption(t('ph.no_mates', lang))
    else:
        mate_labels = {pid: t('ph.together', lang, name=name, n=n)
                       for pid, name, n in zip(mates['player_id_ESPN'], mates['player_display_name'],
                                               mates['shared_games'])}
        mate = st.selectbox(t('ph.mate', lang), list(mate_labels), format_func=mate_labels.get, key='ph_mate')
        ww = with_without(career, player_id, mate, stat)
        if len(ww) < 2:
            st.caption(t('ph.never_missed', lang))
        if len(ww):
            ww = ww.rename(index=lambda v: value(v, lang))
            st.dataframe(ww, width='stretch',
                         column_config=column_config(ww.columns, {c: '%.1f' for c in ['avg', 'median', 'minutes',
                                                                                     'shots']},
                                                     lang=lang, context='research'))
        st.caption(t('ph.mates_caption', lang))

with table_tab:
    cols = ['Date', 'OPP', 'type', 'Result', 'season_type', 'starter', 'MIN', 'PTS', 'REB', 'AST', '3PM', 'PA', 'PR',
            'ARP', 'STL', 'BLK', 'TO', 'FGM', 'FGA', '3PA', 'FTM', 'FTA', 'PLUS_MINUS', 'rest_days']
    full = career[cols].sort_values('Date', ascending=False)
    st.dataframe(full, hide_index=True, width='stretch', height=420,
                 column_config=column_config(cols, lang=lang, context='research')
                 | {'Date': st.column_config.DateColumn(label('Date', lang),
                                                        format='YYYY-MM-DD')})
    st.download_button(t('results.download', lang), full.to_csv(index=False),
                       file_name=f"{career['player_name_ESPN'].iloc[0]}.csv")
