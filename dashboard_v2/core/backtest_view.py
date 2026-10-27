"""The Backtest 2022/23 page: the summary of `python -m backtest.run`, a strategy tester over its
priced lines, and a per-player view."""
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from backtest.explore import bets, cumulative, filter_lines, lines_summary, totals
from backtest.run import MIN_GAMES, picks_frame, rate_row, strategies
from core import charts
from core.state import language
from core.ui import kpis, table
from glossary import column_config, tinted
from i18n import label, t, value
from metrics import grouped_rates
from tracking import calibration

BACKTEST_FILE = os.path.join('data', 'backtest', '2022_lines.csv')
VIEWS = ['summary', 'tester', 'player', 'calibration']
CALIBRATION_REPORT = os.path.join('data', 'backtest', 'calibration.md')
BET_LABELS = ['model', 'average', 'under', 'over']
RATE_FORMATS = {'bets': '%d', 'hit %': '%.1f', 'ci low %': '%.1f', 'ci high %': '%.1f', 'ROI %': '%+.1f',
                'avg odds': '%.2f'}
BET_FORMATS = {'line': '%g', 'actual': '%g', 'avg': '%.1f', 'proj avg': '%.1f', 'edge pp': '%+.1f',
               'model %': '%.0f', 'bet odds': '%.2f', 'bet profit': '%+.2f', 'games': '%d'}
BET_COLUMNS = ['game_date', 'name_ESPN', 'team', 'bet_type', 'line', 'avg', 'proj avg', 'best side', 'signal',
               'edge pp', 'model %', 'bet side', 'bet odds', 'actual', 'bet result', 'bet profit', 'games']
SUMMARY_FORMATS = {'lines': '%d', 'over %': '%.0f', 'avg line': '%.1f', 'avg actual': '%.1f',
                   'actual − line': '%+.2f'}
STAT_NAME = lambda s: 'PRA' if s == 'ARP' else s


@st.cache_data(show_spinner="Reading the 2022/23 backtest...")
def backtest_lines(mtime: float) -> pd.DataFrame:
    """data/backtest/2022_lines.csv; mtime only makes a new run re-read."""
    return pd.read_csv(BACKTEST_FILE, parse_dates=['game_date'])


def _rates(rates: pd.DataFrame):
    lang = language()
    shown = rates.assign(**{c: rates[c].map(lambda v: value(v, lang)) for c in ('signal', 'bet side') if c in rates})
    st.dataframe(tinted(shown, RATE_FORMATS), hide_index=True, width='stretch',
                 column_config=column_config(shown.columns, RATE_FORMATS, lang=lang, context='backtest'))


def rates_table(b: pd.DataFrame, by: str):
    """metrics.grouped_rates of the decided bets of a bets() frame."""
    decided = b[b['bet result'].isin(['win', 'loss'])]
    if decided.empty:
        st.caption(t('bt.no_bets', language()))
        return
    _rates(grouped_rates(decided.assign(is_hit=decided['bet result'] == 'win', odds=decided['bet odds']), by))


def bet_kpis(b: pd.DataFrame):
    lang = language()
    s = totals(b)
    known = s['bets'] > 0
    kpis([{'label': t('bt.kpi.bets', lang), 'value': s['bets'], 'delta': t('bt.kpi.pushes', lang, n=s['pushes']),
           'delta_color': 'off'},
          {'label': t('bt.kpi.hit', lang), 'value': f"{s['hit %']:.1f}%" if known else "–",
           'delta': t('bt.kpi.needs', lang, be=s['break-even %']) if known else None, 'delta_color': 'off',
           'help': t('bt.kpi.hit_help', lang, low=s['ci low %'], high=s['ci high %']) if known else None},
          {'label': t('bt.kpi.profit', lang), 'value': f"{s['profit']:+.1f} u", 'help': t('bt.kpi.profit_help', lang)},
          {'label': t('bt.kpi.roi', lang), 'value': f"{s['ROI %']:+.1f}" if known else "–"}])


def profit_chart(b: pd.DataFrame, key: str, title: str):
    c = cumulative(b)
    fig = go.Figure(go.Scatter(x=c['game_date'], y=c['total'], mode='lines', line=dict(color=charts.NEUTRAL),
                               customdata=c[['bets', 'profit']],
                               hovertemplate=t('bt.curve_hover', language()) + "<extra></extra>"))
    fig.add_hline(y=0, line_color='#64748b')
    charts.show(charts.layout(fig, 300, title, yaxis=dict(title=t('bt.units', language()))), key=key)


def bets_table(b: pd.DataFrame, height: int = 400):
    """The bets, newest first. Unstyled (no column tint): a whole season is too many cells for a pandas Styler."""
    shown = b.sort_values(['game_date', 'name_ESPN'], ascending=[False, True])
    shown = shown.assign(signal=shown['signal'].fillna(''))   # an empty signal reads 'None' otherwise
    lang = language()
    words = shown[BET_COLUMNS].assign(**{c: shown[c].map(lambda v: value(v, lang))
                                         for c in ('best side', 'bet side', 'bet result')})
    st.dataframe(words, hide_index=True, width='stretch', height=height,
                 column_config=column_config(BET_COLUMNS, BET_FORMATS, sources={c: 'stats' for c in BET_COLUMNS},
                                             lang=lang, context='backtest')
                 | {'game_date': st.column_config.DateColumn(label('game_date', lang), format='YYYY-MM-DD')})
    return shown


def summary_view(every: pd.DataFrame):
    lang = language()
    lines = every[every['main'] & (every['games'] >= MIN_GAMES)]
    st.caption(t('bt.lines_caption', lang, n=len(lines), games=MIN_GAMES, dates=lines['game_date'].nunique()))
    rows = pd.DataFrame([{'strategy': name, **rate_row(lines, side, odds)}
                         for name, (side, odds) in strategies(lines).items()])
    picks = picks_frame(lines)
    by_name = rows.set_index('strategy')
    green, under = by_name.loc["Model pick, 🟢 only"], by_name.loc["Always Under"]
    kpis([{'label': t('bt.kpi.picks_hit', lang), 'value': f"{100 * picks['is_hit'].mean():.1f}%",
           'help': t('bt.kpi.picks_hit_help', lang)},
          {'label': t('bt.kpi.picks_roi', lang),
           'value': f"{100 * (np.where(picks['is_hit'], picks['odds'], 0) - 1).mean():+.1f}"},
          {'label': t('bt.kpi.green_roi', lang), 'value': f"{green['ROI %']:+.1f}",
           'delta': t('bt.kpi.n_bets', lang, n=int(green['bets'])), 'delta_color': 'off'},
          {'label': t('bt.kpi.under_roi', lang), 'value': f"{under['ROI %']:+.1f}",
           'help': t('bt.kpi.under_help', lang)}])
    left, right = st.columns([3, 2])
    with left:
        st.markdown(t('bt.strategies', lang))
        table(rows, list(rows.columns), RATE_FORMATS, sources={c: 'stats' for c in rows.columns if c != 'strategy'},
              context='backtest')
    with right:
        cal = calibration(picks)
        fig = go.Figure()
        fig.add_scatter(x=[0, 100], y=[0, 100], mode='lines', line=dict(dash='dot', color='grey'),
                        name=t('results.calibration_ideal', lang))
        fig.add_scatter(x=cal['model %'], y=cal['actual %'], mode='markers+text', text=cal['bets'],
                        textposition='top center', marker=dict(size=10, color=charts.AVERAGE), name='picks')
        charts.show(charts.layout(fig, 320, t('bt.cal_title', lang),
                                  xaxis=dict(title=t('results.calibration_x', lang), range=[20, 100]),
                                  yaxis=dict(title=t('results.calibration_y', lang), range=[20, 100])), key='bt_cal')
        st.caption(t('results.calibration_caption', lang))
    for i, (what, by) in enumerate([('signal', 'signal'), ('edge', 'edge bucket'), ('stat', 'bet_type'),
                                    ('month', 'month')]):
        if i % 2 == 0:
            cols = st.columns(2)
        with cols[i % 2]:
            st.markdown(t('bt.by', lang, what=t(f'bt.by.{what}', lang)))
            _rates(grouped_rates(picks, by))


def tester_view(every: pd.DataFrame):
    lang = language()
    st.caption(t('bt.tester_caption', lang))
    first, last = every['game_date'].min().date(), every['game_date'].max().date()
    f = st.columns([2, 3, 3, 2])
    period = f[0].date_input(t('bt.dates', lang), (first, last), min_value=first, max_value=last, key='bt_dates')
    players = f[1].multiselect(t('bt.players', lang), sorted(every['name_ESPN'].unique()), key='bt_players',
                               placeholder=t('bt.all_players', lang))
    stats = f[2].pills(t('bt.stats', lang), sorted(every['bet_type'].unique()), selection_mode='multi',
                       key='bt_stats', format_func=STAT_NAME, help=t('bt.none_all', lang))
    signals = f[3].pills(t('bt.signal', lang), ['🟢', '🟡', 'none'], selection_mode='multi', key='bt_signals',
                         format_func=lambda v: value(v, lang), help=t('bt.signal_help', lang))
    g = st.columns([5, 2, 3], vertical_alignment='bottom')
    bet_on = g[0].segmented_control(t('bt.bet_on', lang), BET_LABELS, default='model',
                                    format_func=lambda k: t(f'bt.bet.{k}', lang), key='bt_bet_on') or 'model'
    side = g[1].segmented_control(t('bt.side', lang), ['Over', 'Under'], key='bt_side',
                                  format_func=lambda v: value(v, lang), help=t('bt.side_help', lang))
    with g[2].popover(t('bt.more', lang), width='stretch'):
        use_edge = st.toggle(t('bt.use_edge', lang), key='bt_use_edge', help=t('bt.use_edge_help', lang))
        min_edge = st.number_input(t('bt.edge', lang), -50.0, 50.0, 5.0, 1.0, key='bt_min_edge',
                                   disabled=not use_edge)
        min_games = st.number_input(t('bt.min_games', lang), 0, 82, MIN_GAMES, key='bt_min_games')
        main_only = st.toggle(t('bt.main', lang), value=True, key='bt_main', help=t('bt.main_help', lang))
    active = [t('bt.f.edge', lang, edge=min_edge)] * use_edge + [t('bt.f.games', lang, n=min_games)] \
        + [t('bt.f.main', lang)] * main_only
    st.caption(t('bt.filters', lang, list=", ".join(active)))
    since, until = period if isinstance(period, tuple) and len(period) == 2 else (first, last)
    chosen = filter_lines(every, since, until, players, stats, signals, min_edge if use_edge else None, min_games,
                          main_only)
    b = bets(chosen, bet_on, side)
    if b.empty:
        st.info(t('bt.no_match', lang))
        return
    bet_kpis(b)
    profit_chart(b, 'bt_tester_curve', t('bt.curve', lang))
    left, right = st.columns(2)
    with left:
        st.markdown(t('bt.by_stat', lang))
        rates_table(b, 'bet_type')
    with right:
        st.markdown(t('bt.by_side', lang))
        rates_table(b, 'bet side')
    st.markdown(t('bt.the_bets', lang, n=len(b)))
    shown = bets_table(b)
    st.download_button(t('results.download', lang), shown[BET_COLUMNS].to_csv(index=False),
                       file_name="backtest_bets.csv")


def player_view(every: pd.DataFrame):
    lang = language()
    counts = every[every['main']].groupby('name_ESPN').size().sort_values(ascending=False)
    c = st.columns([3, 1], vertical_alignment='bottom')
    player = c[0].selectbox(t('bt.player', lang), list(counts.index), key='bt_player', index=None,
                            format_func=lambda n: t('bt.player_lines', lang, name=n, n=int(counts[n])),
                            placeholder=t('bt.player_pick', lang))
    main_only = c[1].toggle(t('bt.main', lang), value=True, key='bt_player_main')
    if player is None:
        st.info(t('bt.pick_player', lang), icon="👆")
        return
    mine = filter_lines(every, players=[player], main_only=main_only)
    picks = bets(mine, 'model')
    s = totals(picks)
    decided = mine[mine['actual'] != mine['line']]
    kpis([{'label': t('bt.kpi.lines', lang), 'value': len(mine),
           'delta': t('bt.kpi.games', lang, n=mine['game_date'].nunique()), 'delta_color': 'off'},
          {'label': t('bt.kpi.over', lang), 'value': f"{100 * (decided['actual'] > decided['line']).mean():.0f}%"
           if len(decided) else "–", 'help': t('bt.kpi.over_help', lang)},
          {'label': t('bt.kpi.miss', lang), 'value': f"{(mine['actual'] - mine['line']).mean():+.2f}",
           'help': t('bt.kpi.miss_help', lang)},
          {'label': t('bt.kpi.picks_hit', lang), 'value': f"{s['hit %']:.0f}%" if s['bets'] else "–",
           'delta': t('bt.kpi.n_bets', lang, n=s['bets']), 'delta_color': 'off'},
          {'label': t('bt.kpi.picks_profit', lang), 'value': f"{s['profit']:+.1f} u"}])
    by_stat = lines_summary(mine, 'bet_type')
    stat = st.segmented_control(t('bt.stat', lang), list(by_stat['bet_type']), default=by_stat['bet_type'].iloc[0],
                                format_func=STAT_NAME, key='bt_player_stat') or by_stat['bet_type'].iloc[0]
    part = mine[mine['bet_type'] == stat].sort_values('game_date')
    colours = np.where(part['actual'] > part['line'], charts.OVER,
                       np.where(part['actual'] < part['line'], charts.UNDER, charts.PUSH))
    fig = go.Figure()
    fig.add_scatter(x=part['game_date'], y=part['line'], mode='lines', name=t('bt.line', lang),
                    line=dict(color='#64748b', dash='dash', shape='hv'))
    fig.add_scatter(x=part['game_date'], y=part['avg'], mode='lines', name=t('bt.avg_before', lang),
                    line=dict(color=charts.AVERAGE))
    fig.add_scatter(x=part['game_date'], y=part['actual'], mode='markers', name=t('bt.result', lang),
                    marker=dict(size=9, color=colours),
                    customdata=part[['line', 'best side', 'signal']].fillna('').assign(
                        **{'best side': lambda d: d['best side'].map(lambda v: value(v, lang))}),
                    hovertemplate=t('bt.player_hover', lang) + "<extra></extra>")
    charts.show(charts.layout(fig, 340, t('bt.player_chart', lang, name=player, stat=STAT_NAME(stat)),
                              yaxis=dict(title=STAT_NAME(stat))), key='bt_player_chart')
    left, right = st.columns([3, 2])
    with left:
        st.markdown(t('bt.resolved', lang))
        table(by_stat, list(by_stat.columns), SUMMARY_FORMATS,
              sources={c: 'stats' for c in by_stat.columns if c != 'bet_type'}, context='backtest')
    with right:
        st.markdown(t('bt.model_on_them', lang))
        rates_table(picks, 'bet_type')
    profit_chart(picks, 'bt_player_curve', t('bt.every_pick', lang, name=player))
    st.markdown(t('bt.every_line', lang))
    bets_table(picks, height=360)


def render():
    lang = language()
    if not os.path.exists(BACKTEST_FILE):
        st.info(t('bt.no_file', lang))
        return
    bt = backtest_lines(os.path.getmtime(BACKTEST_FILE))
    top = st.columns([2, 3])
    variant = top[0].segmented_control(
        t('bt.lineup', lang), ['none', 'absences'], default='none', key='bt_variant',
        format_func=lambda k: t(f'bt.lineup.{k}', lang), help=t('bt.lineup_help', lang)) or 'none'
    view = top[1].segmented_control(t('bt.view', lang), VIEWS, default='summary',
                                    format_func=lambda k: t(f'bt.view.{k}', lang), key='bt_view') or 'summary'
    calibrated = 'raw model %' in bt and (bt['raw model %'] - bt['model %']).abs().max() > 0.5
    st.caption(t('bt.caption', lang) + (t('bt.in_sample', lang) if calibrated else ""))
    if view == 'calibration':
        calibration_view()
        return
    every = bt[bt['variant'] == variant]
    {'summary': summary_view, 'tester': tester_view, 'player': player_view}[view](every)


def calibration_view():
    """The report of python -m backtest.calibrate: fitted on the earlier 2022/23 and Superbet lines, scored on the
    later ones, with the 🟢 threshold."""
    if not os.path.exists(CALIBRATION_REPORT):
        st.info(t('bt.no_calibration', language()))
        return
    if language() != 'en':
        st.caption(t('bt.report_english', language()))
    with open(CALIBRATION_REPORT, encoding='utf-8') as f:
        st.markdown(f.read().split('\n', 1)[1])   # without the report's own title
