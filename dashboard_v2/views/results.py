import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import charts
from core.analysis import GAP_LABELS, settle_lines, side_rates
from core.ui import go_to_data, kpis, page_header, stop, table
from glossary import column_config, tinted
from loaders import filtered_logs, games, player_logs, snapshot_history
from schedule import nights_text
from tracking import calibration, edge_bucket, results_table, settle_games

seasons, season_types = page_header(
    "Results", "Every line the snapshots saved, settled against the stored stats: were Superbet's lines off from "
               "the players' averages, and did the dashboard's picks win?", with_scope=True)

RATE_FORMATS = {'lines': '%d', 'bets': '%d', 'hit %': '%.0f', 'ROI %': '%+.1f', 'ci low %': '%.0f',
                'ci high %': '%.0f', 'avg odds': '%.2f', 'avg CLV %': '%+.1f'}
RATE_TIPS = {'lines': "Won or lost (pushes and voids left out)", 'hit %': "How often that side won",
             'ROI %': "Profit per 100 staked, betting 1 unit on every line at the opening odds"}


@st.cache_data(ttl=600, show_spinner="Settling the saved lines...")
def settled(seasons, season_types) -> pd.DataFrame:
    return settle_lines(snapshot_history('superbet_props'), player_logs(), games(),
                        average_logs=filtered_logs(list(seasons), list(season_types)))


@st.cache_data(ttl=600, show_spinner=False)
def settled_games() -> pd.DataFrame:
    return settle_games(snapshot_history('superbet_game_odds'), games())


lines = settled(tuple(seasons), tuple(season_types))
if lines.empty:
    go_to_data("**No saved lines yet.** Fetch Superbet's lines before the games (Data center → Fetch & save; "
               "every fetch is saved), then update the stats the next morning to settle them.")
    stop()

# --- filters ---
f = st.columns([2, 5, 2])
dates = lines['game_date'].dropna()
start, end = dates.min().date(), dates.max().date()
# opened from "See how the last night's lines resolved": that night, on the list of every line
night = st.session_state.pop('results_night', None)
if night:
    st.session_state['res_dates'] = (max(night[0], start), min(night[-1], end))
    st.session_state['res_tab'] = "All settled lines"
st.session_state.setdefault('res_dates', (start, end))
period = f[0].date_input("Game dates", min_value=start, max_value=end, key='res_dates')
types = sorted(lines['bet_type'].unique())
type_filter = f[1].pills("Bet types", types, selection_mode='multi', key='res_types',
                         format_func=lambda t: 'PRA' if t == 'ARP' else t, help="None picked = all")
min_games = f[2].number_input("Min games before the line", 0, 82, 3, key='res_min_games',
                              help="Leave out lines on players with fewer stored games before the game: their "
                                   "average says little")
view = lines
if isinstance(period, tuple) and len(period) == 2:
    view = view[(view['game_date'].dt.date >= period[0]) & (view['game_date'].dt.date <= period[1])]
if type_filter:
    view = view[view['bet_type'].isin(type_filter)]
view = view[view['pre games'] >= min_games]
done = view[view['status'] == 'settled']

avg_decided = done[done['pre avg result'].isin(['win', 'loss'])]
kpis([{'label': "Settled lines", 'value': len(done),
       'delta': f"{(view['status'] == 'pending').sum()} pending, {(view['status'] == 'void').sum()} void",
       'delta_color': 'off', 'help': "pending = the game isn't in the stored stats yet; void = the player didn't play"},
      {'label': "Over hit rate", 'value': f"{100 * (done['actual'] > done['line']).mean():.0f}%" if len(done) else "–",
       'help': "How often the result went over the line. Far from 50% = the lines were set too low or high."},
      {'label': "Average line error", 'value': f"{done['line error'].mean():+.2f}" if len(done) else "–",
       'help': "Average of actual − line: + = players beat the lines on average"},
      {'label': "Toward the average: hit", 'value': f"{100 * (avg_decided['pre avg result'] == 'win').mean():.0f}%"
       if len(avg_decided) else "–", 'help': "Betting the side the player's pre-game average points to"},
      {'label': "Toward the average: ROI",
       'value': f"{100 * avg_decided['pre avg profit'].mean():+.1f}%" if len(avg_decided) else "–",
       'help': "At the opening odds of that side, 1 unit per line"}])

if night:
    st.caption(f"Showing the night of {nights_text(night)}: the last Superbet fetch. Change the dates above for "
               f"every saved night.")
avg_tab, picks_tab, games_tab, all_tab = st.tabs(
    ["Lines vs averages", "Dashboard's picks", "Game markets", "All settled lines"],
    default=st.session_state.get('res_tab'))

with avg_tab:
    if done.empty:
        st.info("Nothing settled in this selection yet: update the stats after the games (Data center).")
    else:
        left, right = st.columns(2)
        with left:
            by_gap = side_rates(done, 'gap', 'pre avg')
            by_gap = by_gap[by_gap['lines'] > 0]
            fig = go.Figure(go.Bar(x=by_gap['gap'].astype(str), y=by_gap['hit %'],
                                   marker_color=np.where(by_gap['ROI %'] > 0, charts.OVER, charts.UNDER),
                                   text=[f"{h:.0f}% ({n})" for h, n in zip(by_gap['hit %'], by_gap['lines'])],
                                   textposition='outside', customdata=by_gap['ROI %'],
                                   hovertemplate="%{x}: won %{y:.0f}%, ROI %{customdata:+.1f}%<extra></extra>"))
            fig.add_hline(y=50, line_dash='dot', line_color='#94a3b8')
            charts.show(charts.layout(fig, 340, "Betting toward the average, by how far the line was from it",
                                      xaxis=dict(categoryorder='array', categoryarray=GAP_LABELS),
                                      yaxis=dict(title='hit %', range=[0, 105])), key='res_gap')
            st.caption("Each bar: lines grouped by the line's distance from the player's pre-game average, and how "
                       "often the side toward the average won (lines in brackets). Green = profitable at the odds.")
        with right:
            fig = go.Figure()
            for t in sorted(done['bet_type'].unique()):
                fig.add_box(y=done.loc[done['bet_type'] == t, 'line error'], name='PRA' if t == 'ARP' else t,
                            boxmean=True, marker_color=charts.NEUTRAL, showlegend=False)
            fig.add_hline(y=0, line_color='#64748b')
            charts.show(charts.layout(fig, 340, "Actual − line, per bet type", yaxis=dict(title='actual − line')),
                        key='res_error')
            st.caption("Boxes above 0 = players beat Superbet's lines in that bet type (Overs did well); dashed line "
                       "in a box = its average.")
        st.markdown("**By bet type**")
        rows = []
        for t, part in done.groupby('bet_type'):
            avg_part = part[part['pre avg result'].isin(['win', 'loss'])]
            proj_part = part[part['proj_avg result'].isin(['win', 'loss'])]
            rows.append({'bet_type': t, 'lines': len(part), 'over %': 100 * (part['actual'] > part['line']).mean(),
                         'line error': part['line error'].mean(),
                         'line − avg': (part['line'] - part['pre avg']).mean(),
                         'toward avg hit %': 100 * (avg_part['pre avg result'] == 'win').mean() if len(avg_part)
                         else np.nan,
                         'toward avg ROI %': 100 * avg_part['pre avg profit'].mean() if len(avg_part) else np.nan,
                         'toward proj hit %': 100 * (proj_part['proj_avg result'] == 'win').mean() if len(proj_part)
                         else np.nan})
        by_type = pd.DataFrame(rows)
        table(by_type, list(by_type.columns),
              {'lines': '%d', 'over %': '%.0f', 'line error': '%+.2f', 'line − avg': '%+.2f',
               'toward avg hit %': '%.0f', 'toward avg ROI %': '%+.1f', 'toward proj hit %': '%.0f'},
              tips={'over %': "How often the result went over the line",
                    'line error': "Average actual − line",
                    'line − avg': "How far the lines sat from the players' pre-game averages, on average",
                    'toward avg hit %': "How often the side toward the pre-game average won",
                    'toward avg ROI %': "Its profit per 100 staked at the opening odds",
                    'toward proj hit %': "The same toward the model's proj avg (saved with newer snapshots only)"},
              sources={c: 'stats' for c in by_type.columns if c != 'bet_type'})
        st.caption("The pre-game average uses the scope's seasons and game types and only games before the line's "
                   "game, so it's what you could have known when betting.")

with picks_tab:
    picks = view[view['pick'].notna()]
    picks_done = picks[picks['result'].isin(['win', 'loss'])]
    if picks_done.empty:
        st.info("No settled picks yet. Snapshots save the dashboard's pick with each line (Data center → Save "
                "snapshot); older snapshots have odds but no pick, so they only count under Lines vs averages.")
    else:
        kpis([{'label': "Picks settled", 'value': len(picks_done)},
              {'label': "Hit rate", 'value': f"{100 * (picks_done['result'] == 'win').mean():.0f}%"},
              {'label': "Profit (1 unit each)", 'value': f"{picks['profit'].sum():+.2f}"},
              {'label': "ROI", 'value': f"{100 * picks_done['profit'].mean():+.1f}%"},
              {'label': "Avg CLV", 'value': f"{picks_done['clv odds %'].mean():+.1f}%"
               if picks_done['clv odds %'].notna().any() else "–",
               'help': "Opening odds vs the last snapshot before tip-off: beating the close is the best early sign "
                       "of a real edge"}])
        picks = picks.assign(**{'edge bucket': edge_bucket(picks['edge_pp']),
                                'signal': picks['signal'].replace('', 'none')})
        left, right = st.columns(2)
        with left:
            curve = picks.sort_values('game_date').assign(cum=lambda d: d['profit'].fillna(0).cumsum())
            fig = go.Figure(go.Scatter(x=np.arange(1, len(curve) + 1), y=curve['cum'], mode='lines',
                                       line=dict(color=charts.NEUTRAL)))
            fig.add_hline(y=0, line_color='#64748b')
            charts.show(charts.layout(fig, 300, "Cumulative profit, 1 unit per pick", xaxis=dict(title='picks'),
                                      yaxis=dict(title='units')), key='res_curve')
        with right:
            cal = calibration(picks)
            fig = go.Figure()
            fig.add_scatter(x=[0, 100], y=[0, 100], mode='lines', line=dict(dash='dot', color='grey'),
                            name='calibrated')
            fig.add_scatter(x=cal['model %'], y=cal['actual %'], mode='markers+text', text=cal['bets'],
                            textposition='top center', marker=dict(size=10, color=charts.AVERAGE), name='picks')
            charts.show(charts.layout(fig, 300, "Model chance vs how often it won",
                                      xaxis=dict(title="model %", range=[0, 100]),
                                      yaxis=dict(title="won %", range=[0, 100])), key='res_cal')
        for i, (title, by) in enumerate([("By signal", 'signal'), ("By edge (pp)", 'edge bucket'),
                                         ("By bet type", 'bet_type'), ("By side", 'pick')]):
            if i % 2 == 0:
                cols = st.columns(2)
            with cols[i % 2]:
                st.markdown(f"**{title}**")
                t = results_table(picks, by)
                if len(t):
                    st.dataframe(tinted(t, RATE_FORMATS), hide_index=True, width='stretch',
                                 column_config=column_config(t.columns, RATE_FORMATS))

with games_tab:
    g = settled_games()
    g = g[g['model_pct'].notna() & g['main']] if len(g) else g
    decided = g[g['result'].isin(['win', 'loss'])] if len(g) else g
    if decided.empty:
        st.info("No settled game picks yet (main lines only).")
    else:
        kpis([{'label': "Settled", 'value': len(decided)},
              {'label': "Hit rate", 'value': f"{100 * (decided['result'] == 'win').mean():.0f}%"},
              {'label': "ROI", 'value': f"{100 * decided['profit'].mean():+.1f}%"}])
        g = g.assign(**{'edge bucket': edge_bucket(g['edge_pp'])})
        for title, by in (("By edge (pp)", 'edge bucket'), ("By market", 'market')):
            st.markdown(f"**{title}**")
            t = results_table(g, by)
            if len(t):
                st.dataframe(tinted(t, RATE_FORMATS), hide_index=True, width='stretch',
                             column_config=column_config(t.columns, RATE_FORMATS))

with all_tab:
    cols = ['game_date', 'name', 'game', 'bet_type', 'line', 'pre avg', 'pre avg L10', 'pre games', 'proj_avg',
            'actual', 'status', 'pre avg side', 'pre avg result', 'pick', 'result', 'over_odds', 'under_odds',
            'close line']
    st.dataframe(view.sort_values(['game_date', 'name'], ascending=[False, True])[cols], hide_index=True,
                 width='stretch', height=480,
                 column_config=column_config(cols, {'line': '%g', 'pre avg': '%.1f', 'pre avg L10': '%.1f',
                                                    'proj_avg': '%.1f', 'actual': '%g', 'over_odds': '%.2f',
                                                    'under_odds': '%.2f', 'close line': '%g', 'pre games': '%d'},
                                             tips={'pre avg': "Player's average before the game (scope seasons)",
                                                   'pre avg L10': "Average of the 10 games before",
                                                   'pre games': "Games behind the pre-game average",
                                                   'pre avg side': "The side the pre-game average points to",
                                                   'pre avg result': "How that side did",
                                                   'pick': "The dashboard's pick when the snapshot was saved",
                                                   'result': "How the pick did"})
                 | {'game_date': st.column_config.DateColumn("date", format='YYYY-MM-DD')})
    st.download_button("Download CSV", view[cols].to_csv(index=False), file_name="settled_lines.csv")
