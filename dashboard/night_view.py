"""The "previous night" overview, drawn the same way by both dashboards: how every line and game of a night (or
several) resolved against the dashboard's last projection before tip-off (nightly.py does the numbers). lang:
'en' (dashboard v1, the default) or any i18n language (dashboard v2): words from i18n.TEXTS 'night.*', headers
and tooltips from i18n.TERMS."""
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from glossary import column_config, tinted
from i18n import t, value
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
# the group table's columns after the chosen axes (nightly.GROUP_AXES)
GROUP_COLUMNS = ['lines', 'side to bet', 'best side %', 'ci low %', 'ci high %', 'best side ROI %', 'over %',
                 'over ROI %', 'under %', 'under ROI %', 'our picks', 'our hit %', 'our ROI %']
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


def _words(df: pd.DataFrame, columns, lang: str) -> pd.DataFrame:
    """df with the words in `columns` (win, Over, none...) in `lang`."""
    return df.assign(**{c: df[c].map(lambda v: value(v, lang)) for c in columns if c in df})


def _config(columns, formats, tips, lang: str, v1: bool = True, **kwargs):
    """column_config: dashboard v1's English tooltips (`tips`), or dashboard v2's i18n terms in `lang`."""
    if v1:
        return column_config(columns, formats, tips=tips, **kwargs)
    return column_config(columns, formats, lang=lang, context='results', **kwargs)


def _rate(r) -> str:
    return f"{r['hit %']:.0f}%" if r['picks'] else "–"


def render(update_stats: Optional[Callable] = None, key: str = 'night', lang: str = 'en', v1: bool = True):
    """The overview. update_stats: draws a link to update the stats, for nights whose results aren't stored.
    lang / v1: dashboard v2 passes its language and v1=False (headers and tooltips from i18n.TERMS)."""
    available = nights(snapshot_history('superbet_props'), games(), datetime.now(timezone.utc))
    if available.empty:
        st.info(t('night.none', lang))
        return
    labels = {str(r['night'].date()): t('night.label', lang, night=f"{r['night']:%a %b %d}", games=r['games'],
                                        lines=r['lines'])
                                      + ("" if r['settled'] else t('night.pending_label', lang))
              for _, r in available.iterrows()}
    settled = available.set_index(available['night'].dt.strftime('%Y-%m-%d'))['settled']
    sent = st.session_state.pop(f'{key}_pick', None)         # a night sent from another page
    if sent in labels:
        st.session_state[f'{key}_nights'] = [sent]
    st.session_state.setdefault(f'{key}_nights', [next((n for n in labels if settled[n]), next(iter(labels)))])
    st.session_state[f'{key}_nights'] = [n for n in st.session_state[f'{key}_nights'] if n in labels]
    chosen = st.multiselect(t('night.pick', lang), list(labels), format_func=labels.get, key=f'{key}_nights',
                            help=t('night.pick_help', lang))
    pending = [n for n in chosen if not settled[n]]
    if pending:
        st.info(t('night.pending', lang, nights=', '.join(labels[n].split(' · ')[0] for n in pending)))
        if update_stats:
            update_stats()
    chosen = [n for n in chosen if settled[n]]
    if not chosen:
        return
    props, game_part = _combined(chosen)
    if len(props) and props['recomputed'].any():
        st.caption(t('night.recomputed', lang, n=int(props['recomputed'].sum())))
    s = night_summary(props, game_part)
    if s.get('lines'):
        c = st.columns(5)
        _kpi(c[0], t('night.kpi.settled', lang), f"{s['settled']:,}", t('night.kpi.settled_help', lang),
             t('night.kpi.settled_note', lang, lines=f"{s['lines']:,}", void=s['void'])
             + (t('night.kpi.unresolved_note', lang, n=s['unresolved']) if s['unresolved'] else ""))
        _kpi(c[1], t('night.kpi.picks', lang), _rate(s['picks']), t('night.kpi.picks_help', lang),
             t('night.kpi.roi', lang, roi=s['picks']['ROI %']) if s['picks']['picks'] else None)
        _kpi(c[2], t('night.kpi.edge', lang), _rate(s['edge picks']), t('night.kpi.edge_help', lang),
             t('night.kpi.n_picks', lang, n=s['edge picks']['picks']))
        _kpi(c[3], t('night.kpi.red', lang), _rate(s['red picks']), t('night.kpi.red_help', lang),
             t('night.kpi.n_picks', lang, n=s['red picks']['picks']))
        _kpi(c[4], t('night.kpi.closer', lang), f"{s['closer than line %']:.0f}%"
             if pd.notna(s['closer than line %']) else "–", t('night.kpi.closer_help', lang),
             t('night.kpi.closer_note', lang, proj=s['median proj miss'], line=s['median line miss']))
    props_tab, groups_tab, games_tab = st.tabs([t('night.tab.props', lang), t('night.tab.groups', lang),
                                                t('night.tab.games', lang)])
    with props_tab:
        _props(props, key, lang, v1)
    with groups_tab:
        _groups(props, key, lang, v1)
    with games_tab:
        _games(game_part, s, lang, v1)


def _props(props: pd.DataFrame, key: str, lang: str = 'en', v1: bool = True):
    if props.empty:
        st.caption(t('night.no_props', lang))
        return
    settled = props[props['status'] == 'settled']
    picks = settled[settled['result'].isin(['win', 'loss'])].assign(
        is_hit=lambda d: d['result'] == 'win', signal=lambda d: d['signal'].replace('', 'none'))
    left, right = st.columns([3, 2])
    with left:
        stats = sorted(settled['bet_type'].unique(), key=lambda t: (t not in ('PTS', 'REB', 'AST', 'ARP'), t))
        stat = st.segmented_control(t('night.stat', lang), stats, default=stats[0] if stats else None,
                                    key=f'{key}_stat',
                                    format_func=lambda t: 'PRA' if t == 'ARP' else t)
        stat = stat or (stats[0] if stats else None)
        part = settled[(settled['bet_type'] == stat) & settled['proj_avg'].notna()]
        colours = np.select([part['result'] == 'win', part['result'] == 'loss'], [WIN, LOSS], PUSH)
        top = float(max(part['proj_avg'].max(), part['actual'].max(), 1)) if len(part) else 1
        fig = go.Figure()
        fig.add_scatter(x=[0, top], y=[0, top], mode='lines', line=dict(dash='dot', color='#94a3b8'),
                        name='projection = result', hoverinfo='skip')
        words = _words(part, ['pick', 'result'], lang)
        fig.add_scatter(x=part['proj_avg'], y=part['actual'], mode='markers', name='lines',
                        marker=dict(size=8, color=colours, opacity=0.8),
                        customdata=np.stack([part['name'], part['line'], words['pick'].fillna('–'),
                                             words['result'].fillna('–'), part['night']], axis=1),
                        hovertemplate=t('night.scatter_hover', lang) + "<extra></extra>")
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=40, b=10), showlegend=False,
                          title=t('night.scatter', lang, stat='PRA' if stat == 'ARP' else stat),
                          xaxis=dict(title=t('night.x', lang)), yaxis=dict(title=t('night.y', lang)))
        st.plotly_chart(fig, width='stretch', key=f'{key}_scatter', config={'displayModeBar': False})
    with right:
        for title, by in ((t('night.by_signal', lang), 'signal'), (t('night.by_stat', lang), 'bet_type')):
            st.markdown(f"**{title}**")
            if len(picks):
                rates = _words(grouped_rates(picks, by), ['signal'], lang)
                st.dataframe(tinted(rates, RATE_FORMATS), hide_index=True, width='stretch',
                             column_config=_config(rates.columns, RATE_FORMATS, None, lang, v1=v1))
    st.markdown(t('night.every_line', lang))
    f = st.columns(4)
    game = f[0].multiselect(t('night.games', lang), sorted(props['game'].unique()), key=f'{key}_games',
                            placeholder=t('night.all_games', lang))
    stat_f = f[1].multiselect(t('night.stats', lang), sorted(props['bet_type'].unique()), key=f'{key}_stats',
                              placeholder=t('night.all', lang))
    result = f[2].multiselect(t('night.result', lang), ['win', 'loss', 'push', 'void'], key=f'{key}_results',
                              placeholder=t('night.all', lang), format_func=lambda v: value(v, lang))
    signal = f[3].multiselect(t('night.signal', lang), ['🟢', '🟡', '🔴', 'none'], key=f'{key}_signals',
                              placeholder=t('night.all', lang), format_func=lambda v: value(v, lang))
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
    st.dataframe(_words(shown[LINE_COLUMNS], ['pick', 'pick at open', 'result'], lang), hide_index=True,
                 width='stretch', height=420,
                 column_config=_config(LINE_COLUMNS, LINE_FORMATS, LINE_TIPS, lang, v1=v1))
    st.download_button(t('results.download', lang), shown[LINE_COLUMNS].to_csv(index=False),
                       file_name="night_lines.csv", key=f'{key}_download')


def _groups(props: pd.DataFrame, key: str, lang: str = 'en', v1: bool = True):
    """Which kinds of lines a bet was most likely to win on: groups by the chosen axes, the better side first."""
    if props.empty:
        st.caption(t('night.no_props', lang))
        return
    st.caption(t('night.groups_caption', lang, be=BREAK_EVEN))
    c = st.columns([4, 1])
    axes = c[0].multiselect(t('night.group_by', lang), list(GROUP_AXES), default=['bet_type'],
                            format_func=lambda a: t(f'night.axis.{a}', lang), key=f'{key}_axes',
                            help=t('night.group_by_help', lang))
    min_lines = c[1].number_input(t('night.min_lines', lang), 1, 500, 10, key=f'{key}_min_lines',
                                  help=t('night.min_lines_help', lang))
    if not axes:
        st.info(t('night.pick_axis', lang))
        return
    lines = props.assign(bet_type=props['bet_type'].replace({'ARP': 'PRA'}),
                         signal=props['signal'].replace('', 'none'))
    g = group_outcomes(lines, axes, min_lines)
    if g.empty:
        st.info(t('night.no_group', lang))
        return
    g = _words(g, [a for a in axes if a in ('venue', 'pick', 'signal')] + ['best side'], lang)
    g['group'] = g[axes].astype(str).agg(' · '.join, axis=1)
    top = g.head(25).iloc[::-1]
    fig = go.Figure(go.Bar(x=top['best side %'], y=top['group'], orientation='h',
                           marker_color=np.where(top['best side'] == value('Over', lang), OVER, UNDER),
                           error_x=dict(type='data', symmetric=False, array=top['ci high %'] - top['best side %'],
                                        arrayminus=top['best side %'] - top['ci low %'], color='#94a3b8'),
                           text=[t('night.group_text', lang, side=s, pct=p, n=n) for s, p, n in
                                 zip(top['best side'], top['best side %'], top['lines'])],
                           textposition='inside', insidetextanchor='start',
                           customdata=np.stack([top['best side ROI %'], top['lines']], axis=1),
                           hovertemplate=t('night.group_hover', lang) + "<extra></extra>"))
    fig.add_vline(x=BREAK_EVEN, line_dash='dash', line_color='#64748b')
    fig.update_layout(height=80 + 28 * len(top), margin=dict(l=10, r=10, t=40, b=10),
                      title=t('night.groups_chart', lang),
                      xaxis=dict(title=t('night.won_axis', lang), range=[0, 100]))
    st.plotly_chart(fig, width='stretch', key=f'{key}_groups', config={'displayModeBar': False})
    # 'best side' is the model's pick everywhere else ("pick"); here it's the side that won more
    g = g.rename(columns={'best side': 'side to bet'})
    cols = axes + GROUP_COLUMNS
    st.dataframe(tinted(g[cols], GROUP_FORMATS), hide_index=True, width='stretch',
                 column_config=_config(cols, GROUP_FORMATS, GROUP_TIPS, lang, v1=v1,
                                       sources={c_: 'stats' for c_ in cols if c_ not in axes}))


def _games(part: Dict, s: Dict, lang: str = 'en', v1: bool = True):
    g = part['games']
    if g.empty:
        st.caption(t('night.no_games', lang))
        return
    if 'games scored' in s:
        c = st.columns(3)
        _kpi(c[0], t('night.kpi.called', lang),
             t('night.kpi.called_value', lang, n=s['winners called'], total=s['games scored']),
             t('night.kpi.called_help', lang))
        _kpi(c[1], t('night.kpi.total', lang), f"{s['mean total miss']:.1f}" if s['games scored'] else "–",
             t('night.kpi.total_help', lang))
        _kpi(c[2], t('night.kpi.best', lang),
             t('night.kpi.called_value', lang, n=int((g['best result'] == 'win').sum()),
               total=int(g['best result'].isin(['win', 'loss']).sum())), t('night.kpi.best_help', lang))
    t_ = g.assign(**{'proj score': [f"{a:.0f} – {h:.0f}" if pd.notna(h) else '–'
                                   for a, h in zip(g['proj away'], g['proj home'])],
                    'score': [f"{a:.0f} – {h:.0f}" if pd.notna(h) else t('night.score_pending', lang)
                              for a, h in zip(g['away score'], g['home score'])],
                    'called': g['winner called'].map({True: '✔', False: '✖'}).fillna('')})
    table = _words(t_[GAME_COLUMNS], ['best result'], lang)
    st.dataframe(table, hide_index=True, width='stretch',
                 column_config=_config(GAME_COLUMNS, {'total error': '%+.1f'}, {
                     'proj score': "Our projected score (away – home) at the last fetch before tip-off",
                     'score': "Final score (away – home)", 'called': "✔ = our projected winner won",
                     'total error': "actual total − projected total", 'night': "Game date (US)",
                     'best bet': "The market outcome with our biggest edge", 'best result': "How it did"}, lang,
                     v1=v1))
    if g['recomputed'].any():
        st.caption(t('night.games_recomputed', lang))
