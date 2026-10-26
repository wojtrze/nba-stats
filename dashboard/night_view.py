"""The "previous night" overview, drawn the same way by both dashboards: how every line and game of a night (or
several) resolved against the dashboard's last projection before tip-off (nightly.py does the numbers)."""
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from glossary import column_config, tinted
from loaders import games, name_resolver, player_logs, snapshot_history
from metrics import grouped_rates
from nightly import (GROUP_AXES, pre_tip, group_outcomes, lineups_before_tip, night_games, night_props,
                     night_summary, nights, recompute_projection, recompute_props)

WIN, LOSS, PUSH, OVER, UNDER = '#16a34a', '#dc2626', '#9aa5b1', '#2563eb', '#f59e0b'
# Superbet's two prices on a line usually sum to about 105%, so a side needs about 52.5% to break even
BREAK_EVEN = 52.5
LINE_COLUMNS = ['night', 'name', 'game', 'bet_type', 'line', 'proj_avg', 'actual', 'pick', 'model_pct', 'signal',
                'result', 'proj error', 'closer than line', 'open line', 'pick at open', 'red_flag', 'recomputed']
LINE_FORMATS = {'line': '%g', 'proj_avg': '%.1f', 'actual': '%g', 'model_pct': '%.0f', 'proj error': '%+.1f',
                'open line': '%g'}
LINE_TIPS = {'proj_avg': "Our projected average at the last fetch before tip-off",
             'actual': "The player's result", 'pick': "Our pick at the last fetch before tip-off",
             'model_pct': "Our (calibrated) chance for the pick then",
             'result': "How the pick did: win / loss / push; void = didn't play",
             'proj error': "actual − projected average", 'closer than line': "Our projection was closer to the "
             "result than Superbet's line", 'open line': "The line at the first fetch",
             'pick at open': "Our pick at the first fetch", 'red_flag': "The red flags at the fetch (saved from "
             "Oct 22 on; recomputed lines get them recomputed)",
             'recomputed': "✔ = the fetch was saved without our numbers (before Oct 21): pick and projection are "
                           "recomputed from the games before that night", 'night': "Game date (US)"}
GROUP_FORMATS = {'lines': '%d', 'over %': '%.0f', 'over ROI %': '%+.1f', 'under %': '%.0f', 'under ROI %': '%+.1f',
                 'best side %': '%.1f', 'ci low %': '%.0f', 'ci high %': '%.0f', 'best side ROI %': '%+.1f',
                 'our picks': '%d', 'our hit %': '%.0f', 'our ROI %': '%+.1f'}
GROUP_TIPS = {'lines': "Settled lines in the group (pushes left out)",
              'over %': "How often betting Over won", 'over ROI %': "Profit per 100 staked betting every Over",
              'under %': "How often betting Under won", 'under ROI %': "Profit per 100 staked betting every Under",
              'side to bet': "The side that won more often in this group",
              'best side %': "How often that side won: the chance a bet on it succeeded",
              'ci low %': "Low end of that hit rate's 95% range: few lines make it wide",
              'ci high %': "High end of that hit rate's 95% range",
              'best side ROI %': "Profit per 100 staked on that side, at the lines' odds",
              'our picks': "Our picks in the group", 'our hit %': "How often our picks won",
              'our ROI %': "Profit per 100 staked on our picks", 'venue': "The player's team at home or away",
              'position': "G = guards, F = forwards, C = centers (ESPN's listing)", 'pick': "Our pick's side"}
GAME_COLUMNS = ['night', 'game', 'proj score', 'score', 'proj winner', 'winner', 'called', 'total error', 'best bet',
                'best result']
RATE_FORMATS = {'bets': '%d', 'hit %': '%.0f', 'ci low %': '%.0f', 'ci high %': '%.0f', 'ROI %': '%+.1f',
                'avg odds': '%.2f'}


@st.cache_data(ttl=600, show_spinner="Settling the night...")
def _night(night: str):
    """One night's lines and games; projections the fetches didn't save are recomputed."""
    rotowire = snapshot_history('rotowire_lineups')
    rotowire = name_resolver().add_ids(rotowire) if len(rotowire) else rotowire
    odds_snapshots = snapshot_history('superbet_game_odds')

    def recompute_lines(rows):
        rows = name_resolver().add_ids(rows, team_cols=('home', 'away'))
        odds = pre_tip(odds_snapshots, night)
        odds = odds[odds['fetched_at'] == odds['fetched_at'].max()] if len(odds) else odds
        return recompute_props(rows, player_logs(), games(), lineups_before_tip(rotowire, night,
                                                                                 rows['start_time'].min()),
                               odds, night)

    def recompute_game(event_odds):
        lineups = lineups_before_tip(rotowire, night, event_odds['start_time'].iloc[0])
        return recompute_projection(event_odds, games(), player_logs(), lineups, night)

    props = night_props(snapshot_history('superbet_props'), player_logs(), games(), night, recompute_lines)
    game_part = night_games(odds_snapshots, games(), night, recompute_game)
    stamp = lambda df: df.assign(night=pd.Timestamp(night).strftime('%b %d')) if len(df) else df
    return stamp(props), {'games': stamp(game_part['games']), 'outcomes': game_part['outcomes']}


def _combined(chosen: List[str]):
    parts = [_night(n) for n in chosen]
    props = pd.concat([p for p, _ in parts if len(p)], ignore_index=True) if any(len(p) for p, _ in parts) \
        else pd.DataFrame()
    game_list = [g['games'] for _, g in parts if len(g['games'])]
    return props, {'games': pd.concat(game_list, ignore_index=True) if game_list else pd.DataFrame()}


def _kpi(col, label, value, help_=None, note=None):
    col.metric(label, value, note, delta_color='off', delta_arrow='off', help=help_, border=True)


def _rate(r) -> str:
    return f"{r['hit %']:.0f}%" if r['picks'] else "–"


def render(update_stats: Optional[Callable] = None, key: str = 'night'):
    """The overview. update_stats: draws a link to update the stats, for nights whose results aren't stored."""
    available = nights(snapshot_history('superbet_props'), games(), datetime.now(timezone.utc))
    if available.empty:
        st.info("No saved Superbet lines for a night that has started yet.")
        return
    labels = {str(r['night'].date()): f"{r['night']:%a %b %d} · {r['games']} games · {r['lines']:,} lines"
                                      + ("" if r['settled'] else " · results pending")
              for _, r in available.iterrows()}
    settled = available.set_index(available['night'].dt.strftime('%Y-%m-%d'))['settled']
    sent = st.session_state.pop(f'{key}_pick', None)         # a night sent from another page
    if sent in labels:
        st.session_state[f'{key}_nights'] = [sent]
    st.session_state.setdefault(f'{key}_nights', [next((n for n in labels if settled[n]), next(iter(labels)))])
    st.session_state[f'{key}_nights'] = [n for n in st.session_state[f'{key}_nights'] if n in labels]
    chosen = st.multiselect("Nights (US dates)", list(labels), format_func=labels.get, key=f'{key}_nights',
                            help="One night, or several to look at a period. Each line is judged by our last fetch "
                                 "before its tip-off.")
    pending = [n for n in chosen if not settled[n]]
    if pending:
        st.info(f"{', '.join(labels[n].split(' · ')[0] for n in pending)}: the games aren't in the stored stats yet, "
                f"so those lines can't be settled. Update the stats.")
        if update_stats:
            update_stats()
    chosen = [n for n in chosen if settled[n]]
    if not chosen:
        return
    props, game_part = _combined(chosen)
    if len(props) and props['recomputed'].any():
        st.caption(f"{props['recomputed'].sum():,} lines were fetched before our picks and projections were saved "
                   f"with each fetch (Oct 21): those are recomputed from the games before their night and the "
                   f"lineups and odds saved before tip-off (✔ in the recomputed column).")
    s = night_summary(props, game_part)
    if s.get('lines'):
        c = st.columns(5)
        _kpi(c[0], "Lines settled", f"{s['settled']:,}",
             "Lines whose player played; void = didn't play; unresolved = can't be settled from the stored stats",
             f"of {s['lines']:,}, {s['void']} void" + (f", {s['unresolved']} unresolved" if s['unresolved'] else ""))
        _kpi(c[1], "Our picks: hit", _rate(s['picks']), "Every line's pick at the last fetch before tip-off",
             f"ROI {s['picks']['ROI %']:+.1f}%" if s['picks']['picks'] else None)
        _kpi(c[2], "🟢🟡 picks: hit", _rate(s['edge picks']), "Picks with a positive edge",
             f"{s['edge picks']['picks']} picks")
        _kpi(c[3], "🔴 picks: hit", _rate(s['red picks']), "Picks with a red flag", f"{s['red picks']['picks']} picks")
        _kpi(c[4], "Projection beat the line", f"{s['closer than line %']:.0f}%"
             if pd.notna(s['closer than line %']) else "–",
             "How often our projected average was closer to the result than Superbet's line",
             f"median miss {s['median proj miss']:.1f} vs line {s['median line miss']:.1f}")
    props_tab, groups_tab, games_tab = st.tabs(["Player lines", "Where bets won", "Games"])
    with props_tab:
        _props(props, key)
    with groups_tab:
        _groups(props, key)
    with games_tab:
        _games(game_part, s)


def _props(props: pd.DataFrame, key: str):
    if props.empty:
        st.caption("No player lines were saved for these nights.")
        return
    settled = props[props['status'] == 'settled']
    picks = settled[settled['result'].isin(['win', 'loss'])].assign(
        is_hit=lambda d: d['result'] == 'win', signal=lambda d: d['signal'].replace('', 'none'))
    left, right = st.columns([3, 2])
    with left:
        stats = sorted(settled['bet_type'].unique(), key=lambda t: (t not in ('PTS', 'REB', 'AST', 'ARP'), t))
        stat = st.segmented_control("Stat", stats, default=stats[0] if stats else None, key=f'{key}_stat',
                                    format_func=lambda t: 'PRA' if t == 'ARP' else t)
        stat = stat or (stats[0] if stats else None)
        part = settled[(settled['bet_type'] == stat) & settled['proj_avg'].notna()]
        colours = np.select([part['result'] == 'win', part['result'] == 'loss'], [WIN, LOSS], PUSH)
        top = float(max(part['proj_avg'].max(), part['actual'].max(), 1)) if len(part) else 1
        fig = go.Figure()
        fig.add_scatter(x=[0, top], y=[0, top], mode='lines', line=dict(dash='dot', color='#94a3b8'),
                        name='projection = result', hoverinfo='skip')
        fig.add_scatter(x=part['proj_avg'], y=part['actual'], mode='markers', name='lines',
                        marker=dict(size=8, color=colours, opacity=0.8),
                        customdata=np.stack([part['name'], part['line'], part['pick'].fillna('–'),
                                             part['result'].fillna('–'), part['night']], axis=1),
                        hovertemplate="%{customdata[0]} (%{customdata[4]}): projected %{x:.1f}, got %{y}<br>line "
                                      "%{customdata[1]}, pick %{customdata[2]} → %{customdata[3]}<extra></extra>")
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=40, b=10), showlegend=False,
                          title=f"{'PRA' if stat == 'ARP' else stat}: projected average vs result (green = pick won)",
                          xaxis=dict(title='projected'), yaxis=dict(title='result'))
        st.plotly_chart(fig, width='stretch', key=f'{key}_scatter', config={'displayModeBar': False})
    with right:
        for title, by in (("Our picks by signal", 'signal'), ("Our picks by stat", 'bet_type')):
            st.markdown(f"**{title}**")
            if len(picks):
                t = grouped_rates(picks, by)
                st.dataframe(tinted(t, RATE_FORMATS), hide_index=True, width='stretch',
                             column_config=column_config(t.columns, RATE_FORMATS))
    st.markdown("**Every line**")
    f = st.columns(4)
    game = f[0].multiselect("Games", sorted(props['game'].unique()), key=f'{key}_games', placeholder="All games")
    stat_f = f[1].multiselect("Stats", sorted(props['bet_type'].unique()), key=f'{key}_stats', placeholder="All")
    result = f[2].multiselect("Result", ['win', 'loss', 'push', 'void'], key=f'{key}_results', placeholder="All")
    signal = f[3].multiselect("Signal", ['🟢', '🟡', '🔴', 'none'], key=f'{key}_signals', placeholder="All")
    shown = props
    if game:
        shown = shown[shown['game'].isin(game)]
    if stat_f:
        shown = shown[shown['bet_type'].isin(stat_f)]
    if result:
        shown = shown[shown['result'].isin(result)]
    if signal:
        shown = shown[shown['signal'].replace('', 'none').isin(signal)]
    shown = shown.sort_values(['night', 'game', 'name', 'bet_type']).assign(
        recomputed=lambda d: d['recomputed'].map({True: '✔', False: ''}))
    st.dataframe(shown[LINE_COLUMNS], hide_index=True, width='stretch', height=420,
                 column_config=column_config(LINE_COLUMNS, LINE_FORMATS, tips=LINE_TIPS))
    st.download_button("Download CSV", shown[LINE_COLUMNS].to_csv(index=False), file_name="night_lines.csv",
                       key=f'{key}_download')


def _groups(props: pd.DataFrame, key: str):
    """Which kinds of lines a bet was most likely to win on: groups by the chosen axes, the better side first."""
    if props.empty:
        st.caption("No player lines were saved for these nights.")
        return
    st.caption("Every settled line, grouped. For each group: how often betting Over and betting Under won and "
               "paid at the lines' odds, and how our picks did. The groups where a bet was most likely to win come "
               f"first; the dashed line is break-even (about {BREAK_EVEN}%). One night is a small sample: check the "
               "range and look at several nights before trusting a pattern.")
    c = st.columns([4, 1])
    axes = c[0].multiselect("Group by", list(GROUP_AXES), default=['bet_type'], format_func=GROUP_AXES.get,
                            key=f'{key}_axes', help="One axis (e.g. Stat) or several (e.g. Position + Stat)")
    min_lines = c[1].number_input("Min lines", 1, 500, 10, key=f'{key}_min_lines',
                                  help="Leave out groups with fewer settled lines")
    if not axes:
        st.info("Pick at least one axis to group by.")
        return
    lines = props.assign(bet_type=props['bet_type'].replace({'ARP': 'PRA'}),
                         signal=props['signal'].replace('', 'none'))
    g = group_outcomes(lines, axes, min_lines)
    if g.empty:
        st.info("No group has that many lines; lower Min lines.")
        return
    g['group'] = g[axes].astype(str).agg(' · '.join, axis=1)
    top = g.head(25).iloc[::-1]
    fig = go.Figure(go.Bar(x=top['best side %'], y=top['group'], orientation='h',
                           marker_color=np.where(top['best side'] == 'Over', OVER, UNDER),
                           error_x=dict(type='data', symmetric=False, array=top['ci high %'] - top['best side %'],
                                        arrayminus=top['best side %'] - top['ci low %'], color='#94a3b8'),
                           text=[f"{s} {p:.0f}% · {n} lines" for s, p, n in
                                 zip(top['best side'], top['best side %'], top['lines'])],
                           textposition='inside', insidetextanchor='start',
                           customdata=np.stack([top['best side ROI %'], top['lines']], axis=1),
                           hovertemplate="%{y}: %{x:.1f}% won · ROI %{customdata[0]:+.1f}% · %{customdata[1]} lines"
                                         "<extra></extra>"))
    fig.add_vline(x=BREAK_EVEN, line_dash='dash', line_color='#64748b')
    fig.update_layout(height=80 + 28 * len(top), margin=dict(l=10, r=10, t=40, b=10),
                      title="How often the better side won (blue = Over, orange = Under; whiskers = 95% range; "
                            "dashed = break-even)",
                      xaxis=dict(title='won %', range=[0, 100]))
    st.plotly_chart(fig, width='stretch', key=f'{key}_groups', config={'displayModeBar': False})
    # 'best side' is the model's pick everywhere else ("pick"); here it's the side that won more
    g = g.rename(columns={'best side': 'side to bet'})
    cols = axes + ['lines', 'side to bet', 'best side %', 'ci low %', 'ci high %', 'best side ROI %', 'over %',
                   'over ROI %', 'under %', 'under ROI %', 'our picks', 'our hit %', 'our ROI %']
    st.dataframe(tinted(g[cols], GROUP_FORMATS), hide_index=True, width='stretch',
                 column_config=column_config(cols, GROUP_FORMATS, tips=GROUP_TIPS,
                                             sources={c_: 'stats' for c_ in cols if c_ not in axes}))


def _games(part: Dict, s: Dict):
    g = part['games']
    if g.empty:
        st.caption("No game odds were saved for these nights.")
        return
    if 'games scored' in s:
        c = st.columns(3)
        _kpi(c[0], "Winners called", f"{s['winners called']} of {s['games scored']}", "Our projected winner won")
        _kpi(c[1], "Total points: mean miss", f"{s['mean total miss']:.1f}" if s['games scored'] else "–",
             "Average |actual total − projected total|")
        _kpi(c[2], "Best market bets won",
             f"{(g['best result'] == 'win').sum()} of {g['best result'].isin(['win', 'loss']).sum()}",
             "The market outcome with our biggest edge, per game")
    t = g.assign(**{'proj score': [f"{a:.0f} – {h:.0f}" if pd.notna(h) else '–'
                                   for a, h in zip(g['proj away'], g['proj home'])],
                    'score': [f"{a:.0f} – {h:.0f}" if pd.notna(h) else 'pending'
                              for a, h in zip(g['away score'], g['home score'])],
                    'called': g['winner called'].map({True: '✔', False: '✖'}).fillna('')})
    st.dataframe(t[GAME_COLUMNS], hide_index=True, width='stretch',
                 column_config=column_config(GAME_COLUMNS, {'total error': '%+.1f'}, tips={
                     'proj score': "Our projected score (away – home) at the last fetch before tip-off",
                     'score': "Final score (away – home)", 'called': "✔ = our projected winner won",
                     'total error': "actual total − projected total", 'night': "Game date (US)",
                     'best bet': "The market outcome with our biggest edge", 'best result': "How it did"}))
    if g['recomputed'].any():
        st.caption("Projected scores weren't saved with these fetches (they are from Oct 22 on), so they're "
                   "recomputed as the dashboard would have made them: ratings from the games before that night and "
                   "the RotoWire lineups saved before tip-off.")
