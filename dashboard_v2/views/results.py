import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import charts
from core.analysis import GAP_LABELS, settle_lines, side_rates
from core.data import shortlist_record
from core.columns import RESULTS_ALL, RESULTS_BY_TYPE
from core.state import language
from core.ui import PAGES, go_to_data, kpis, page_header, stop, table
from glossary import column_config, tinted
from i18n import label, t, value
from loaders import filtered_logs, games, player_logs, snapshot_history
import night_view
from glossary import signal_legend
from tracking import (EVERY_LINE, RECOMPUTED, RECORDED, calibration, edge_bucket, paper_accumulators,
                      results_table, settle_games, star_scorecard, threshold_table)
from decisions import star_text

lang = language()
seasons, season_types = page_header(t('results.title', lang), t('results.purpose', lang), with_scope=True)

RATE_FORMATS = {'lines': '%d', 'bets': '%d', 'expected %': '%.0f', 'hit %': '%.0f', 'ROI %': '%+.1f',
                'ROI % std': '%+.1f', 'break-even %': '%.1f', 'break-even % std': '%.1f',
                'ci low %': '%.0f', 'ci high %': '%.0f', 'avg odds': '%.2f', 'avg odds vs last %': '%+.1f', 'edge ≥ pp': '%d',
                'nights': '%d', 'price said %': '%.0f', 'won − price pp': '%+.1f'}


def rates(df: pd.DataFrame, words=('signal', 'pick', 'market')):
    """A rates table (results_table / threshold_table) as shown: its group words in the chosen language, headers
    and tooltips from i18n."""
    shown = df.assign(**{c: df[c].map(lambda v: value(v, lang)) for c in words if c in df})
    st.dataframe(tinted(shown, RATE_FORMATS), hide_index=True, width='stretch',
                 column_config=column_config(shown.columns, RATE_FORMATS, lang=lang, context='results'))


@st.cache_data(ttl=600, show_spinner="Settling the saved lines...")
def settled(seasons, season_types) -> pd.DataFrame:
    return settle_lines(snapshot_history('superbet_props'), player_logs(), games(),
                        average_logs=filtered_logs(list(seasons), list(season_types)))


@st.cache_data(ttl=600, show_spinner=False)
def settled_games() -> pd.DataFrame:
    return settle_games(snapshot_history('superbet_game_odds'), games())


# opened from "See how the last night's lines resolved": that night in Previous night
night = st.session_state.pop('results_night', None)
if night:
    st.session_state['night_pick'] = str(night[-1])
night_tab, saved_tab = st.tabs([t('results.tab.night', lang), t('results.tab.saved', lang)])

with night_tab:
    night_view.render(update_stats=lambda: st.page_link(PAGES['data'], label=t('results.update', lang), icon="🔄"),
                      key='night', lang=lang, v1=False)

with saved_tab:
    lines = settled(tuple(seasons), tuple(season_types))
    if lines.empty:
        go_to_data(t('results.no_lines', lang))
        stop()

    # --- filters ---
    f = st.columns([2, 5, 2])
    dates = lines['game_date'].dropna()
    start, end = dates.min().date(), dates.max().date()
    st.session_state.setdefault('res_dates', (start, end))
    period = f[0].date_input(t('results.dates', lang), min_value=start, max_value=end, key='res_dates')
    types = sorted(lines['bet_type'].unique())
    type_filter = f[1].pills(t('results.types', lang), types, selection_mode='multi', key='res_types',
                             format_func=lambda s: 'PRA' if s == 'ARP' else s, help=t('results.types_help', lang))
    min_games = f[2].number_input(t('results.min_games', lang), 0, 82, 3, key='res_min_games',
                                  help=t('results.min_games_help', lang))
    view = lines
    if isinstance(period, tuple) and len(period) == 2:
        view = view[(view['game_date'].dt.date >= period[0]) & (view['game_date'].dt.date <= period[1])]
    if type_filter:
        view = view[view['bet_type'].isin(type_filter)]
    view = view[view['pre games'] >= min_games]
    done = view[view['status'] == 'settled']

    avg_decided = done[done['pre avg result'].isin(['win', 'loss'])]
    kpis([{'label': t('results.kpi.settled', lang), 'value': len(done),
           'delta': t('results.kpi.settled_note', lang, pending=int((view['status'] == 'pending').sum()),
                      void=int((view['status'] == 'void').sum()),
                      unresolved=int((view['status'] == 'unresolved').sum())),
           'delta_color': 'off', 'help': t('results.kpi.settled_help', lang)},
          {'label': t('results.kpi.over', lang),
           'value': f"{100 * (done['actual'] > done['line']).mean():.0f}%" if len(done) else "–",
           'help': t('results.kpi.over_help', lang)},
          {'label': t('results.kpi.error', lang), 'value': f"{done['line error'].mean():+.2f}" if len(done) else "–",
           'help': t('results.kpi.error_help', lang)},
          {'label': t('results.kpi.toward', lang),
           'value': f"{100 * (avg_decided['pre avg result'] == 'win').mean():.0f}%" if len(avg_decided) else "–",
           'help': t('results.kpi.toward_help', lang)},
          {'label': t('results.kpi.toward_roi', lang),
           'value': f"{100 * avg_decided['pre avg profit'].mean():+.1f}" if len(avg_decided) else "–",
           'help': t('results.kpi.toward_roi_help', lang)}])

    avg_tab, picks_tab, shortlist_tab, games_tab, all_tab = st.tabs(
        [t('results.tab.avg', lang), t('results.tab.picks', lang), t('results.tab.shortlist', lang),
         t('results.tab.games', lang), t('results.tab.all', lang)])

    with avg_tab:
        if done.empty:
            st.info(t('results.nothing', lang))
        else:
            left, right = st.columns(2)
            with left:
                by_gap = side_rates(done, 'gap', 'pre avg')
                by_gap = by_gap[by_gap['lines'] > 0]
                fig = go.Figure(go.Bar(x=by_gap['gap'].astype(str), y=by_gap['hit %'],
                                       marker_color=np.where(by_gap['ROI %'] > 0, charts.OVER, charts.UNDER),
                                       text=[f"{h:.0f}% ({n})" for h, n in zip(by_gap['hit %'], by_gap['lines'])],
                                       textposition='outside', customdata=by_gap['ROI %'],
                                       hovertemplate=t('results.gap_hover', lang) + "<extra></extra>"))
                fig.add_hline(y=50, line_dash='dot', line_color='#94a3b8')
                charts.show(charts.layout(fig, 340, t('results.gap_chart', lang),
                                          xaxis=dict(categoryorder='array', categoryarray=GAP_LABELS),
                                          yaxis=dict(title=t('results.calibration_y', lang), range=[0, 105])),
                            key='res_gap')
                st.caption(t('results.gap_caption', lang))
            with right:
                fig = go.Figure()
                for stat in sorted(done['bet_type'].unique()):
                    fig.add_box(y=done.loc[done['bet_type'] == stat, 'line error'],
                                name='PRA' if stat == 'ARP' else stat,
                                boxmean=True, marker_color=charts.NEUTRAL, showlegend=False)
                fig.add_hline(y=0, line_color='#64748b')
                charts.show(charts.layout(fig, 340, t('results.error_chart', lang),
                                          yaxis=dict(title=t('results.error_chart', lang).split(',')[0])),
                            key='res_error')
                st.caption(t('results.error_caption', lang))
            st.markdown(t('results.by_type', lang))
            rows = []
            for stat, part in done.groupby('bet_type'):
                avg_part = part[part['pre avg result'].isin(['win', 'loss'])]
                proj_part = part[part['proj_avg result'].isin(['win', 'loss'])]
                rows.append({'bet_type': stat, 'lines': len(part),
                             'over %': 100 * (part['actual'] > part['line']).mean(),
                             'line error': part['line error'].mean(),
                             'line − avg': (part['line'] - part['pre avg']).mean(),
                             'toward avg hit %': 100 * (avg_part['pre avg result'] == 'win').mean() if len(avg_part)
                             else np.nan,
                             'toward avg ROI %': 100 * avg_part['pre avg profit'].mean() if len(avg_part) else np.nan,
                             'toward proj hit %': 100 * (proj_part['proj_avg result'] == 'win').mean() if len(proj_part)
                             else np.nan})
            by_type = pd.DataFrame(rows, columns=RESULTS_BY_TYPE)
            table(by_type, list(by_type.columns),
                  {'lines': '%d', 'over %': '%.0f', 'line error': '%+.2f', 'line − avg': '%+.2f',
                   'toward avg hit %': '%.0f', 'toward avg ROI %': '%+.1f', 'toward proj hit %': '%.0f'},
                  sources={c: 'stats' for c in by_type.columns if c != 'bet_type'}, context='results')
            st.caption(t('results.avg_caption', lang))

    with picks_tab:
        picks = view[view['pick'].notna()]
        picks_done = picks[picks['result'].isin(['win', 'loss'])]
        if picks_done.empty:
            st.info(t('results.no_picks', lang))
        else:
            kpis([{'label': t('results.kpi.picks', lang), 'value': len(picks_done)},
                  {'label': t('results.kpi.hit', lang),
                   'value': f"{100 * (picks_done['result'] == 'win').mean():.0f}%"},
                  {'label': t('results.kpi.profit', lang), 'value': f"{picks['profit'].sum():+.2f}"},
                  {'label': t('results.kpi.roi', lang), 'value': f"{100 * picks_done['profit'].mean():+.1f} / "
                                                                   f"{100 * picks_done['profit std'].mean():+.1f}"},
                  {'label': t('results.kpi.vs_last', lang), 'value': f"{picks_done['odds vs last %'].mean():+.1f}%"
                   if picks_done['odds vs last %'].notna().any() else "–",
                   'help': t('results.kpi.vs_last_help', lang)}])
            picks = picks.assign(**{'edge bucket': edge_bucket(picks['edge_pp']),
                                    'signal': picks['signal'].replace('', 'none')})
            st.markdown(t('results.efficiency', lang))
            efficiency = threshold_table(picks)
            if efficiency.empty:
                st.caption(t('results.no_edge_yet', lang))
            else:
                rates(efficiency)
            st.caption(signal_legend(lang))
            left, right = st.columns(2)
            with left:
                curve = picks.sort_values('game_date').assign(cum=lambda d: d['profit'].fillna(0).cumsum())
                fig = go.Figure(go.Scatter(x=np.arange(1, len(curve) + 1), y=curve['cum'], mode='lines',
                                           line=dict(color=charts.NEUTRAL)))
                fig.add_hline(y=0, line_color='#64748b')
                charts.show(charts.layout(fig, 300, t('results.curve', lang),
                                          xaxis=dict(title=t('results.curve_x', lang)),
                                          yaxis=dict(title=t('results.curve_y', lang))), key='res_curve')
            with right:
                cal = calibration(picks)
                fig = go.Figure()
                fig.add_scatter(x=[0, 100], y=[0, 100], mode='lines', line=dict(dash='dot', color='grey'),
                                name=t('results.calibration_ideal', lang))
                fig.add_scatter(x=cal['model %'], y=cal['actual %'], mode='markers+text', text=cal['bets'],
                                textposition='top center', marker=dict(size=10, color=charts.AVERAGE), name='picks')
                charts.show(charts.layout(fig, 300, t('results.calibration', lang),
                                          xaxis=dict(title=t('results.calibration_x', lang), range=[0, 100]),
                                          yaxis=dict(title=t('results.calibration_y', lang), range=[0, 100])),
                            key='res_cal')
                st.caption(t('results.calibration_caption', lang))
            for i, (title, by) in enumerate([('results.by_signal', 'signal'), ('results.by_edge', 'edge bucket'),
                                             ('results.by_stat', 'bet_type'), ('results.by_side', 'pick')]):
                if i % 2 == 0:
                    cols = st.columns(2)
                with cols[i % 2]:
                    st.markdown(t(title, lang))
                    grouped = results_table(picks, by)
                    if len(grouped):
                        rates(grouped)

    with games_tab:
        g = settled_games()
        g = g[g['model_pct'].notna() & g['main']] if len(g) else g
        decided = g[g['result'].isin(['win', 'loss'])] if len(g) else g
        if decided.empty:
            st.info(t('results.no_games', lang))
        else:
            kpis([{'label': t('results.kpi.games', lang), 'value': len(decided)},
                  {'label': t('results.kpi.hit', lang), 'value': f"{100 * (decided['result'] == 'win').mean():.0f}%"},
                  {'label': t('results.kpi.roi', lang), 'value': f"{100 * decided['profit'].mean():+.1f} / "
                                                                   f"{100 * decided['profit std'].mean():+.1f}"}])
            g = g.assign(**{'edge bucket': edge_bucket(g['edge_pp']),
                            'market': g['market'].map(lambda m: t(f'market.{m}', lang))})
            for title, by in (('results.by_edge', 'edge bucket'), ('results.by_market', 'market')):
                st.markdown(t(title, lang))
                grouped = results_table(g, by)
                if len(grouped):
                    rates(grouped)

    with shortlist_tab:
        record = shortlist_record()
        st.caption(t('results.shortlist_intro', lang))
        scorecard = star_scorecard(record)
        if scorecard.empty or not scorecard.loc[scorecard['stars'] == EVERY_LINE, 'bets'].sum():
            st.info(t('results.shortlist_none', lang))
        else:
            nights = record.drop_duplicates('game_date')
            st.caption(t('results.shortlist_origin', lang, recorded=int((nights['origin'] == RECORDED).sum()),
                         recomputed=int((nights['origin'] == RECOMPUTED).sum())))
            rates(scorecard.assign(stars=[star_text(n) if isinstance(n, int) else
                                          t('results.every_line', lang) if n == EVERY_LINE else n
                                          for n in scorecard['stars']]))
            st.markdown(f"**{t('results.ako', lang)}**")
            st.caption(t('results.ako_intro', lang))
            ako = paper_accumulators(record)
            if len(ako):
                st.caption(t('results.ako_summary', lang, n=len(ako), won=int((ako['result'] == 'win').sum()),
                             total=ako['profit std'].sum()))
                shown = ako.sort_values('game_date', ascending=False)
                st.dataframe(shown.assign(result=shown['result'].map(lambda v: value(v, lang))), hide_index=True,
                             width='stretch',
                             column_config=column_config(list(shown.columns),
                                                         {'odds': '%.2f', 'profit': '%+.2f', 'profit std': '%+.2f',
                                                          'cumulative std': '%+.2f'}, lang=lang, context='results')
                             | {'game_date': st.column_config.DateColumn(label('game_date', lang),
                                                                         format='YYYY-MM-DD')})

    with all_tab:
        cols = RESULTS_ALL
        shown = view.sort_values(['game_date', 'name'], ascending=[False, True])[cols]
        shown = shown.assign(**{c: shown[c].map(lambda v: value(v, lang))
                                for c in ('status', 'pre avg side', 'pre avg result', 'pick', 'result')})
        st.dataframe(shown, hide_index=True, width='stretch', height=480,
                     column_config=column_config(cols, {'line': '%g', 'pre avg': '%.1f', 'pre avg L10': '%.1f',
                                                        'proj_avg': '%.1f', 'actual': '%g', 'over_odds': '%.2f',
                                                        'under_odds': '%.2f', 'last line': '%g', 'pre games': '%d'},
                                                 lang=lang, context='results')
                     | {'game_date': st.column_config.DateColumn(label('game_date', lang), format='YYYY-MM-DD')})
        st.download_button(t('results.download', lang), view[cols].to_csv(index=False), file_name="settled_lines.csv")
