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
from core.ui import kpis, table
from glossary import column_config, tinted
from metrics import grouped_rates
from tracking import calibration

BACKTEST_FILE = os.path.join('data', 'backtest', '2022_lines.csv')
VIEWS = {'summary': "Summary", 'tester': "Strategy tester", 'player': "Player"}
BET_LABELS = {'model': "Model pick", 'average': "Toward the season average", 'under': "Always Under",
              'over': "Always Over"}
RATE_FORMATS = {'bets': '%d', 'hit %': '%.1f', 'ci low %': '%.1f', 'ci high %': '%.1f', 'ROI %': '%+.1f',
                'avg odds': '%.2f'}
RATE_TIPS = {'bets': "Won and lost bets (pushes left out)", 'hit %': "How often the bet won",
             'ROI %': "Profit per 100 staked, 1 unit per bet at the line's odds",
             'ci low %': "Low end of the hit rate's 95% range", 'ci high %': "High end of the hit rate's 95% range"}
BET_FORMATS = {'line': '%g', 'actual': '%g', 'avg': '%.1f', 'proj avg': '%.1f', 'edge pp': '%+.1f',
               'model %': '%.0f', 'bet odds': '%.2f', 'bet profit': '%+.2f', 'games': '%d'}
BET_COLUMNS = ['game_date', 'name_ESPN', 'team', 'bet_type', 'line', 'avg', 'proj avg', 'best side', 'signal',
               'edge pp', 'model %', 'bet side', 'bet odds', 'actual', 'bet result', 'bet profit', 'games']
BET_TIPS = {'name_ESPN': "Player", 'team': "Player's team", 'avg': "Season average before the game",
            'best side': "The model's pick", 'bet side': "The side the chosen strategy bets",
            'bet odds': "Unibet's odds for that side", 'actual': "The player's result",
            'bet result': "win / loss / push", 'bet profit': "Profit for 1 unit", 'games': "Games before the line"}
SUMMARY_FORMATS = {'lines': '%d', 'over %': '%.0f', 'avg line': '%.1f', 'avg actual': '%.1f',
                   'actual − line': '%+.2f'}
STAT_NAME = lambda s: 'PRA' if s == 'ARP' else s


@st.cache_data(show_spinner="Reading the 2022/23 backtest...")
def backtest_lines(mtime: float) -> pd.DataFrame:
    """data/backtest/2022_lines.csv; mtime only makes a new run re-read."""
    return pd.read_csv(BACKTEST_FILE, parse_dates=['game_date'])


def rates_table(b: pd.DataFrame, by: str):
    """metrics.grouped_rates of the decided bets of a bets() frame."""
    decided = b[b['bet result'].isin(['win', 'loss'])]
    if decided.empty:
        st.caption("No decided bets.")
        return
    t = grouped_rates(decided.assign(is_hit=decided['bet result'] == 'win', odds=decided['bet odds']), by)
    st.dataframe(tinted(t, RATE_FORMATS), hide_index=True, width='stretch',
                 column_config=column_config(t.columns, RATE_FORMATS, tips=RATE_TIPS))


def bet_kpis(b: pd.DataFrame):
    s = totals(b)
    known = s['bets'] > 0
    kpis([{'label': "Bets", 'value': s['bets'], 'delta': f"{s['pushes']} pushes", 'delta_color': 'off'},
          {'label': "Hit rate", 'value': f"{s['hit %']:.1f}%" if known else "–",
           'delta': f"needs {s['break-even %']:.1f}%" if known else None, 'delta_color': 'off',
           'help': f"95% range {s['ci low %']:.1f}–{s['ci high %']:.1f}%. Needs = break-even at the odds (the "
                   f"average of 1 / odds)" if known else None},
          {'label': "Profit", 'value': f"{s['profit']:+.1f} u", 'help': "Units, 1 unit on every bet"},
          {'label': "ROI", 'value': f"{s['ROI %']:+.1f}%" if known else "–"}])


def profit_chart(b: pd.DataFrame, key: str, title: str):
    c = cumulative(b)
    fig = go.Figure(go.Scatter(x=c['game_date'], y=c['total'], mode='lines', line=dict(color=charts.NEUTRAL),
                               customdata=c[['bets', 'profit']],
                               hovertemplate="%{x|%b %d}: total %{y:+.1f} u<br>%{customdata[0]} bets, "
                                             "%{customdata[1]:+.1f} u that day<extra></extra>"))
    fig.add_hline(y=0, line_color='#64748b')
    charts.show(charts.layout(fig, 300, title, yaxis=dict(title='units')), key=key)


def bets_table(b: pd.DataFrame, height: int = 400):
    """The bets, newest first. Unstyled (no column tint): a whole season is too many cells for a pandas Styler."""
    shown = b.sort_values(['game_date', 'name_ESPN'], ascending=[False, True])
    shown = shown.assign(signal=shown['signal'].fillna(''))   # an empty signal reads 'None' otherwise
    st.dataframe(shown[BET_COLUMNS], hide_index=True, width='stretch', height=height,
                 column_config=column_config(BET_COLUMNS, BET_FORMATS, tips=BET_TIPS,
                                             sources={c: 'stats' for c in BET_COLUMNS})
                 | {'game_date': st.column_config.DateColumn("date", format='YYYY-MM-DD')})
    return shown


def summary_view(every: pd.DataFrame):
    t = every[every['main'] & (every['games'] >= MIN_GAMES)]
    st.caption(f"{len(t)} main lines of players with {MIN_GAMES}+ games, {t['game_date'].nunique()} dates.")
    rows = pd.DataFrame([{'strategy': name, **rate_row(t, side, odds)} for name, (side, odds) in strategies(t).items()])
    picks = picks_frame(t)
    by_name = rows.set_index('strategy')
    green, under = by_name.loc["Model pick, 🟢 only"], by_name.loc["Always Under"]
    kpis([{'label': "Model picks: hit", 'value': f"{100 * picks['is_hit'].mean():.1f}%",
           'help': "Every line's model pick; break-even at these odds is about 52.5%"},
          {'label': "Model picks: ROI", 'value': f"{100 * (np.where(picks['is_hit'], picks['odds'], 0) - 1).mean():+.1f}%"},
          {'label': "🟢 picks: ROI", 'value': f"{green['ROI %']:+.1f}%", 'delta': f"{green['bets']:.0f} bets",
           'delta_color': 'off'},
          {'label': "Always Under: ROI", 'value': f"{under['ROI %']:+.1f}%", 'help': "The simplest baseline"}])
    left, right = st.columns([3, 2])
    with left:
        st.markdown("**Strategies on the same lines**")
        table(rows, list(rows.columns), RATE_FORMATS, RATE_TIPS,
              sources={c: 'stats' for c in rows.columns if c != 'strategy'})
    with right:
        cal = calibration(picks)
        fig = go.Figure()
        fig.add_scatter(x=[0, 100], y=[0, 100], mode='lines', line=dict(dash='dot', color='grey'), name='calibrated')
        fig.add_scatter(x=cal['model %'], y=cal['actual %'], mode='markers+text', text=cal['bets'],
                        textposition='top center', marker=dict(size=10, color=charts.AVERAGE), name='picks')
        charts.show(charts.layout(fig, 320, "Model chance vs how often the pick won",
                                  xaxis=dict(title="model %", range=[20, 100]),
                                  yaxis=dict(title="won %", range=[20, 100])), key='bt_cal')
    for i, (title, by) in enumerate([("By signal", 'signal'), ("By edge (pp)", 'edge bucket'),
                                     ("By bet type", 'bet_type'), ("By month", 'month')]):
        if i % 2 == 0:
            cols = st.columns(2)
        with cols[i % 2]:
            st.markdown(f"**Model pick – {title.lower()}**")
            g = grouped_rates(picks, by)
            st.dataframe(tinted(g, RATE_FORMATS), hide_index=True, width='stretch',
                         column_config=column_config(g.columns, RATE_FORMATS, tips=RATE_TIPS))


def tester_view(every: pd.DataFrame):
    st.caption("Choose which lines to bet and how; every number below is for exactly that selection, 1 unit per "
               "bet at Unibet's odds.")
    first, last = every['game_date'].min().date(), every['game_date'].max().date()
    f = st.columns([2, 3, 3, 2])
    period = f[0].date_input("Game dates", (first, last), min_value=first, max_value=last, key='bt_dates')
    players = f[1].multiselect("Players", sorted(every['name_ESPN'].unique()), key='bt_players',
                               placeholder="All players")
    stats = f[2].pills("Stats", sorted(every['bet_type'].unique()), selection_mode='multi', key='bt_stats',
                       format_func=STAT_NAME, help="None picked = all")
    signals = f[3].pills("Model signal", ['🟢', '🟡', 'none'], selection_mode='multi', key='bt_signals',
                         help="The model's signal on the line, whatever you bet on. None picked = all")
    g = st.columns([5, 2, 3], vertical_alignment='bottom')
    bet_on = g[0].segmented_control("Bet on", list(BET_LABELS), default='model', format_func=BET_LABELS.get,
                                    key='bt_bet_on') or 'model'
    side = g[1].segmented_control("Side", ['Over', 'Under'], key='bt_side',
                                  help="Only the bets on this side; none picked = both")
    with g[2].popover("More filters", width='stretch'):
        use_edge = st.toggle("Minimum model edge", key='bt_use_edge',
                             help="Only lines where the model's edge (for its own pick) is at least this many pp")
        min_edge = st.number_input("Edge (pp)", -50.0, 50.0, 5.0, 1.0, key='bt_min_edge', disabled=not use_edge)
        min_games = st.number_input("Min games before the line", 0, 82, MIN_GAMES, key='bt_min_games')
        main_only = st.toggle("Main lines only", value=True, key='bt_main',
                              help="The most balanced line per player, stat and game; off = also alternative lines")
    active = [f"edge ≥ {min_edge:g}"] * use_edge + [f"{min_games}+ games"] + ["main lines"] * main_only
    st.caption("Filters: " + ", ".join(active))
    since, until = period if isinstance(period, tuple) and len(period) == 2 else (first, last)
    chosen = filter_lines(every, since, until, players, stats, signals, min_edge if use_edge else None, min_games,
                          main_only)
    b = bets(chosen, bet_on, side)
    if b.empty:
        st.info("No bets match these filters.")
        return
    bet_kpis(b)
    profit_chart(b, 'bt_tester_curve', "Cumulative profit")
    left, right = st.columns(2)
    with left:
        st.markdown("**By stat**")
        rates_table(b, 'bet_type')
    with right:
        st.markdown("**By side**")
        rates_table(b, 'bet side')
    st.markdown(f"**The {len(b)} bets**")
    shown = bets_table(b)
    st.download_button("Download CSV", shown[BET_COLUMNS].to_csv(index=False), file_name="backtest_bets.csv")


def player_view(every: pd.DataFrame):
    counts = every[every['main']].groupby('name_ESPN').size().sort_values(ascending=False)
    c = st.columns([3, 1], vertical_alignment='bottom')
    player = c[0].selectbox("Player", list(counts.index), key='bt_player', index=None,
                            format_func=lambda n: f"{n} ({counts[n]} lines)",
                            placeholder="Type a name... (most lines first)")
    main_only = c[1].toggle("Main lines only", value=True, key='bt_player_main')
    if player is None:
        st.info("Pick a player to see how their 2022/23 lines resolved and how the model did on them.", icon="👆")
        return
    mine = filter_lines(every, players=[player], main_only=main_only)
    picks = bets(mine, 'model')
    s = totals(picks)
    decided = mine[mine['actual'] != mine['line']]
    kpis([{'label': "Lines", 'value': len(mine), 'delta': f"{mine['game_date'].nunique()} games",
           'delta_color': 'off'},
          {'label': "Went over", 'value': f"{100 * (decided['actual'] > decided['line']).mean():.0f}%"
           if len(decided) else "–", 'help': "How often the result beat the line (pushes left out)"},
          {'label': "Actual − line", 'value': f"{(mine['actual'] - mine['line']).mean():+.2f}",
           'help': "Average miss: + = the lines were set too low for this player"},
          {'label': "Model picks: hit", 'value': f"{s['hit %']:.0f}%" if s['bets'] else "–",
           'delta': f"{s['bets']} bets", 'delta_color': 'off'},
          {'label': "Model picks: profit", 'value': f"{s['profit']:+.1f} u"}])
    by_stat = lines_summary(mine, 'bet_type')
    stat = st.segmented_control("Stat", list(by_stat['bet_type']), default=by_stat['bet_type'].iloc[0],
                                format_func=STAT_NAME, key='bt_player_stat') or by_stat['bet_type'].iloc[0]
    part = mine[mine['bet_type'] == stat].sort_values('game_date')
    colours = np.where(part['actual'] > part['line'], charts.OVER,
                       np.where(part['actual'] < part['line'], charts.UNDER, charts.PUSH))
    fig = go.Figure()
    fig.add_scatter(x=part['game_date'], y=part['line'], mode='lines', name='line',
                    line=dict(color='#64748b', dash='dash', shape='hv'))
    fig.add_scatter(x=part['game_date'], y=part['avg'], mode='lines', name='season average before',
                    line=dict(color=charts.AVERAGE))
    fig.add_scatter(x=part['game_date'], y=part['actual'], mode='markers', name='result', marker=dict(size=9, color=colours),
                    customdata=part[['line', 'best side', 'signal']].fillna(''),
                    hovertemplate="%{x|%b %d}: %{y} vs line %{customdata[0]}<br>model pick %{customdata[1]} "
                                  "%{customdata[2]}<extra></extra>")
    charts.show(charts.layout(fig, 340, f"{player}: {STAT_NAME(stat)} lines and results (green = over the line)",
                              yaxis=dict(title=STAT_NAME(stat))), key='bt_player_chart')
    left, right = st.columns([3, 2])
    with left:
        st.markdown("**How the lines resolved, by stat**")
        table(by_stat, list(by_stat.columns), SUMMARY_FORMATS,
              tips={'over %': "How often the result beat the line (pushes left out)",
                    'actual − line': "Average miss: + = lines too low", 'avg line': "Average line",
                    'avg actual': "Average result"},
              sources={c: 'stats' for c in by_stat.columns if c != 'bet_type'})
    with right:
        st.markdown("**The model's picks on them**")
        rates_table(picks, 'bet_type')
    profit_chart(picks, 'bt_player_curve', f"Betting every model pick on {player}")
    st.markdown("**Every line**")
    bets_table(picks, height=360)


def render():
    if not os.path.exists(BACKTEST_FILE):
        st.info("No backtest yet. Run `python -m backtest.run` (about 10 minutes) to price Unibet's 2022/23 lines "
                "with today's model.")
        return
    bt = backtest_lines(os.path.getmtime(BACKTEST_FILE))
    top = st.columns([2, 3])
    variant = top[0].segmented_control(
        "Tonight's lineup", ['none', 'absences'], default='none', key='bt_variant',
        format_func={'none': "Not known (no RotoWire)", 'absences': "Perfectly known (upper bound)"}.get,
        help="What the model knew about who's out: nothing, or exactly who didn't play (an upper bound for "
             "RotoWire's value)") or 'none'
    view = top[1].segmented_control("View", list(VIEWS), default='summary', format_func=VIEWS.get,
                                    key='bt_view') or 'summary'
    st.caption("Unibet's 2022/23 player lines, each priced by today's props model from the games before its date "
               "only. No historical game odds, so the implied-team-total factor is off. Details: "
               "data/backtest/2022_summary.md.")
    every = bt[bt['variant'] == variant]
    {'summary': summary_view, 'tester': tester_view, 'player': player_view}[view](every)
