import numpy as np
import pandas as pd
import streamlit as st

from components import decision_text, decision_times, reasons_panel
from core import charts
from core.analysis import gap_groups, last_game_line, sd_group, teammate_impact
from core.data import (lineups as rotowire_lineups, odds_paths, player_decisions, priced_props, rotowire,
                       settled_lines, superbet)
from decisions import OBSTAW, offer_changed, offer_decision, offer_key, star_text, stars
from core.columns import PROPS_MAIN as MAIN_COLUMNS, PROPS_MORE as MORE_COLUMNS
from core.state import cost_profile, language, persist, remember
from core.ui import PAGES, go_to_data, kpis, no_offers, page_header, pl_time, stop, table
from glossary import column_config
from i18n import t, value
from reasons import flag_texts
from loaders import filtered_logs, player_logs, snapshot_history
from metrics import STATS, hit_rates, percentile_band, rotowire_team, splits
from mispricing import offer_signals
from models import calibration_warning, load_calibration, top_up_logs
from reasons import offer_context, prop_reasons
from tracking import PROP_KEY
import whatif

lang = language()
seasons, season_types = page_header(t('props.title', lang), t('props.purpose', lang), with_scope=True)
logs = filtered_logs(seasons, season_types)
lineups = rotowire_lineups()
table_all = priced_props(seasons, season_types)
decided = player_decisions(table_all)
# every line's stars (decisions.stars): its place among tonight's lines, ★★★★☆; 'star count' sorts and filters
if len(table_all):
    rated = stars(table_all, decided)[PROP_KEY + ['stars']].rename(columns={'stars': 'star count'})
    table_all = table_all.merge(rated, on=PROP_KEY, how='left')
    table_all['stars'] = table_all['star count'].map(star_text)
if warning := calibration_warning(table_all['calibration'].iloc[0] if len(table_all) else None, lang):
    st.warning(warning, icon="⚠️")

DEFAULT_TYPES = ['PTS', 'REB', 'AST', '3PM', 'PA', 'PR', 'RA', 'ARP']
FORMATS = {'raw model %': '%.0f', 'line': '%g', 'side odds': '%.2f', 'p win %': '%.0f', 'p push %': '%.0f',
           'break-even net %': '%.1f', 'edge net pp': '%+.1f', 'ev net 100': '%+.1f',
           'proj avg': '%.1f', 'pick % L10': '%.0f', 'pick %': '%.0f',
           'avg': '%.1f', 'adj avg': '%.1f', 'avg L5': '%.1f', 'min L5': '%.1f', 'percentile': '%.0f',
           'over_odds': '%.2f', 'under_odds': '%.2f', 'games': '%d', 'line move': '%+g', 'open line': '%g',
           'spread': '%+g', 'game total': '%g'}


# how the table can be ordered (i18n 'props.sort.*'): by tip-off by default; none of them says what to bet
SORTS = ['tip', 'stars', 'return', 'chance']


def sort_lines(rows: pd.DataFrame, how: str) -> pd.DataFrame:
    """The lines in the chosen order, warnings always last. tip: the earliest game first; return: the highest
    expected return after the tax; chance: the highest chance to win (mostly low odds); stars: the most stars
    first (decisions.stars), then by expected return."""
    rows = rows.assign(warned=rows['red flag'].fillna('') != '')
    if 'star count' not in rows:
        rows = rows.assign(**{'star count': pd.NA, 'stars': '–'})
    rows = rows.assign(listed=-pd.to_numeric(rows['star count'], errors='coerce').fillna(-1))
    by = {'return': ['warned', 'ev net 100'], 'chance': ['warned', 'p win %'],
          'tip': ['warned', 'tip_at', 'game', 'ev net 100'], 'stars': ['warned', 'listed', 'ev net 100']}[how]
    ascending = {'return': [True, False], 'chance': [True, False], 'tip': [True, True, True, False],
                 'stars': [True, True, False]}[how]
    return rows.sort_values(by, ascending=ascending, kind='stable').drop(columns=['warned', 'listed'])


def line_decision(row) -> dict:
    """The decision of the line's game as it applies to this line (decisions.offer_decision)."""
    return offer_decision(decided[row['event_id']], row)


def display_values(rows: pd.DataFrame) -> pd.DataFrame:
    """The rows as shown: the decision, the evaluated side and the role in the chosen language, warnings worded in
    the chosen language (the table keeps the English originals for sorting and filtering)."""
    out = rows.assign(decision=[t(f"decision.{line_decision(r)['status']}", lang) for _, r in rows.iterrows()])
    for col in ('side', 'RotoWire'):
        out[col] = out[col].map(lambda v: value(v, lang))
    if lang != 'en' and 'flag items' in out:
        out['red flag'] = ['; '.join(flag_texts(items, lang)) if isinstance(items, list) else flag
                           for items, flag in zip(out['flag items'], out['red flag'])]
    return out


def decisions_banner(event_ids):
    """The one decision for the players of each game shown, earliest first, with its odds and lineup times."""
    with st.container(border=True):
        st.markdown(f"**{t('decision.title', lang)}** · {t('decision.players', lang)}")
        for event_id in event_ids:
            d = decided[event_id]
            game = table_all.loc[table_all['event_id'] == event_id, 'game'].iloc[0]
            offer = f" · {d['offer']['name']} {value(d['offer']['side'], lang)} {d['offer']['line']:g} " \
                    f"{d['offer']['bet_type']} @ {d['offer']['side odds']:.2f}" if d['status'] == OBSTAW else ''
            st.markdown(f"- **{game}**: {decision_text(d, lang)}{offer}  \n  :gray[{decision_times(d, lang)}]")


def lineup_banner():
    """Says whether tonight's numbers include RotoWire's lineups, game by game."""
    games_ = table_all.drop_duplicates('event_id')[['game', 'home', 'away']]
    listed = lineups.drop_duplicates('team').set_index('team')['lineup_status'] if len(lineups) else pd.Series()
    confirmed = sum(listed.get(h) == 'confirmed' and listed.get(a) == 'confirmed'
                    for h, a in zip(games_['home'], games_['away']))
    known = [g for g, h, a in zip(games_['game'], games_['home'], games_['away']) if h in listed and a in listed]
    missing = [g for g in games_['game'] if g not in known]
    if not known:
        st.info(t('banner.none', lang), icon="ℹ️")
    elif missing:
        st.caption(t('banner.some', lang, known=len(known), total=len(games_), confirmed=confirmed,
                     missing=', '.join(missing)))
    else:
        st.caption(t('banner.all', lang, confirmed=confirmed, total=len(games_)))


def detail(row: pd.Series, changed=None):
    """The selected line: verdict, teammates, history and line movement in tabs."""
    pid = row['player_id']
    # the games the line was priced from (priced_props tops a player with few games up with last season's)
    games = top_up_logs(logs[logs['player_id_ESPN'] == pid], player_logs(), max(seasons), [pid]).sort_values('Date')
    stat, line = row['bet_type'], row['line']
    side = f"{value(row['side'], lang)} {line:g} {stat} @ {row['side odds']:.2f}"
    decision = line_decision(row)
    # only an OBSTAW offer is named as one; any other line shows its evaluated side and what it returns
    st.markdown("### " + (f"{row['name']} · {side}" if decision['status'] == OBSTAW else
                          t('detail.pass_title', lang, name=row['name'], side=side, ev=row['ev net 100'])))
    st.caption(f"{row['game']} · {pl_time(row['start_time'])} · "
               f"{value(row['RotoWire'], lang) or t('detail.not_listed', lang)}")
    verdict_tab, whatif_tab, mates_tab, history_tab, move_tab = st.tabs(
        [t('detail.tab.verdict', lang), t('detail.tab.whatif', lang), t('detail.tab.mates', lang),
         t('detail.tab.history', lang), t('detail.tab.move', lang)])

    with verdict_tab:
        every = player_logs()
        history = every[(every['player_id_ESPN'] == pid) & every['season_type'].isin(season_types)
                        & (every['OPP'].str.lower() == (row['opp'] or ''))]
        names = logs.groupby('player_id_ESPN')['player_display_name'].last()
        odds_at = superbet()['fetched_at']
        bet = offer_context(row, games, logs, lineups, names, odds_at, rotowire()['fetched_at'])
        # where Superbet's prices of this player's lines may be wrong (docs/hipotezy_wyceny.md: H1, H2, H6)
        player_lines = table_all[(table_all['player_id'] == pid) & (table_all['event_id'] == row['event_id'])]
        signals = offer_signals(player_lines, games, logs, odds_at)
        reasons_panel(f"{value(row['side'], lang)} {line:g} {stat}", decision,
                      prop_reasons(bet, games, history, lang, signals=signals), games, stat, line, lang, changed)
        st.markdown(t('detail.built', lang))
        kpis([{'label': t('detail.kpi.avg', lang), 'value': f"{row['avg']:.1f}",
               'help': t('detail.kpi.avg_help', lang, games=row['games'])},
              {'label': t('detail.kpi.out', lang), 'value': f"{row['adj avg']:.1f}",
               'delta': f"{row['lineup adj']:+.1f}", 'delta_color': 'off', 'help': t('detail.kpi.out_help', lang)},
              {'label': t('detail.kpi.game', lang), 'value': f"{row['proj avg']:.1f}",
               'delta': f"{row['proj avg'] - row['adj avg']:+.1f}", 'delta_color': 'off',
               'help': t('detail.kpi.game_help', lang, pace=row['pace factor'], matchup=row['matchup factor'],
                         word=value(row['matchup'], lang) or t('detail.unknown', lang))},
              {'label': t('detail.kpi.line', lang), 'value': f"{line:g}",
               'delta': t('detail.kpi.line_delta', lang, gap=line - row['proj avg']), 'delta_color': 'off'}])
        b = st.columns(3)
        if b[0].button(t('detail.open_player', lang), width='stretch'):
            st.session_state['player_preset'] = {'player_id': pid, 'stat': stat, 'line': float(line)}
            st.switch_page(PAGES['player'])
        if row['team'] and b[1].button(t('detail.open_lineup', lang, team=row['team'].upper()), width='stretch'):
            st.session_state['lineup_team'] = row['team']
            st.switch_page(PAGES['lineup'])

    with whatif_tab:
        whatif_panel(row, games)

    with mates_tab:
        if not row['team']:
            st.caption(t('mates.no_team', lang))
        else:
            out = rotowire_team(lineups, row['team'])['out']
            every_season = st.toggle(t('mates.every_season', lang), value=True, key='mates_all_seasons',
                                     help=t('mates.every_season_help', lang))
            source = player_logs()[player_logs()['season_type'].isin(season_types)] if every_season else logs
            impact = teammate_impact(source, pid, row['team'], stat, out)
            shown = impact[impact['n_without'] > 0]
            if row['team'] not in set(lineups['team']):
                st.caption(t('mates.not_listed', lang))
            elif out:
                st.caption(t('mates.out', lang, names=', '.join(impact.loc[impact['out tonight'], 'teammate']),
                             adj=row['lineup adj']))
            if shown.empty:
                st.caption(t('mates.none', lang))
            else:
                shown = shown.assign(hover=[t('mates.hover', lang, mate=r['teammate'], without=r['without'],
                                              n_without=r['n_without'], with_=r['with'], n_with=r['n_with'])
                                            for _, r in shown.iterrows()])
                charts.show(charts.change_bars(shown.head(12), 'teammate', 'change', 'out tonight', 'hover',
                                               t('mates.chart', lang, name=row['name'], stat=stat)),
                            key='mates_chart')
                st.dataframe(impact, hide_index=True, width='stretch', column_order=[
                    'teammate', 'out tonight', 'change', 'without', 'n_without', 'with', 'n_with'],
                    column_config={'teammate': st.column_config.Column(t('mates.col.teammate', lang)),
                                   'out tonight': st.column_config.Column(t('mates.col.out', lang)),
                                   'change': st.column_config.NumberColumn(
                                       t('mates.col.change', lang), format='%+.1f',
                                       help=t('mates.col.change_help', lang, stat=stat)),
                                   'with': st.column_config.NumberColumn(t('mates.col.with', lang, stat=stat),
                                                                         format='%.1f'),
                                   'without': st.column_config.NumberColumn(t('mates.col.without', lang, stat=stat),
                                                                            format='%.1f'),
                                   'n_with': st.column_config.NumberColumn(t('mates.col.n_with', lang), format='%d'),
                                   'n_without': st.column_config.NumberColumn(t('mates.col.n_without', lang),
                                                                              format='%d')})
                st.caption(t('mates.reliability', lang))

    with history_tab:
        if games.empty:
            st.caption(t('history.none', lang))
        else:
            charts.show(charts.game_log(games, stat, line, last=20, minutes=True,
                                        title=t('history.chart', lang, n=min(20, len(games)))), key='hist_log')
            left, right = st.columns(2)
            with left:
                charts.show(charts.distribution(games[stat], stat, line, t('history.dist', lang)), key='hist_dist')
            with right:
                st.markdown(t('history.splits', lang))
                sp = splits(games, stat, line)
                st.dataframe(sp, hide_index=True, width='stretch',
                             column_config=column_config(sp.columns, {'avg': '%.1f', 'median': '%.1f',
                                                                      'over %': '%.0f'}))
                if len(history):
                    st.markdown(t('history.vs_opp', lang, opp=row['opp'].upper(), avg=history[stat].mean(),
                                  n=len(history), line=line, over=int((history[stat] > line).sum())))

    with move_tab:
        snaps = snapshot_history('superbet_props')
        if snaps.empty:
            st.caption(t('move.none', lang))
        else:
            key = dict(zip(PROP_KEY, [row['event_id'], row['name_ESPN'], stat]))
            mine = snaps[(snaps['event_id'] == key['event_id']) & (snaps['name_ESPN'] == key['name_ESPN'])
                         & (snaps['bet_type'] == stat)]
            if mine.empty:
                st.caption(t('move.not_saved', lang))
            else:
                mine = mine.assign(time=pd.to_datetime(mine['fetched_at'], utc=True)
                                   .dt.tz_convert('Europe/Warsaw').dt.strftime('%a %H:%M'))
                st.dataframe(mine[['time', 'line', 'over_odds', 'under_odds']], hide_index=True, width='stretch',
                             column_config=column_config(['line', 'over_odds', 'under_odds'],
                                                         {'over_odds': '%.2f', 'under_odds': '%.2f', 'line': '%g'},
                                                         base={'time': st.column_config.Column(t('move.time', lang))},
                                                         lang=lang))
                st.caption(t('move.now', lang, line=line, over=row['over_odds'], under=row['under_odds']))


def _distance(p: float, be: float):
    """The distance to break-even after tax in words (whatif.short / whatif.above + the fixed caveat)."""
    if p > be:
        st.markdown(t('whatif.above', lang, p=p, be=be, gap=p - be))
        st.caption(t('whatif.caveat', lang))
    else:
        st.markdown(t('whatif.short', lang, p=p, be=be, gap=be - p))


def whatif_panel(row: pd.Series, games: pd.DataFrame):
    """What would have to change for the line's evaluated side to reach break-even after tax (whatif.py), and the
    look-back: his last game's line and every settled line by its gap in the player's spreads."""
    stat, line, side = row['bet_type'], float(row['line']), row['side']
    if side not in ('Over', 'Under') or games.empty or stat not in games:
        st.caption(t('whatif.no_side', lang))
        return
    coef, profile = load_calibration(), cost_profile()
    if side == 'Over':
        side_odds, other = float(row['over_odds']), float(row['under_odds'])
    else:
        side_odds, other = float(row['under_odds']), float(row['over_odds'])
    args = dict(values=games[stat], proj_avg=row['proj avg'], side=side, other_odds=other, coef=coef,
                profile=profile)
    side_word = value(side, lang)
    key = f"{row['event_id']}_{row['name_ESPN']}_{stat}"
    st.caption(t('whatif.intro', lang))

    now = whatif.evaluate(line=line, side_odds=side_odds, **args)
    _distance(now['p win %'], now['break-even %'])
    gap = whatif.gap_in_spreads(row['proj avg'], line, row['sd'], row['games'])
    if pd.notna(gap):
        st.markdown(t('whatif.gap', lang, proj=row['proj avg'], line=line, gap=gap, sd=row['sd'], n=int(row['games'])))
    else:
        st.markdown(t('whatif.gap_none', lang, proj=row['proj avg'], line=line))

    # what would be enough, each on its own
    st.markdown(t('whatif.needs', lang))
    need_odds = whatif.needed_odds(line=line, side_odds=side_odds, **args)
    if need_odds is None:
        st.markdown(t('whatif.need_odds_none', lang))
    elif need_odds <= side_odds:
        st.markdown(t('whatif.need_odds_now', lang, now=side_odds))
    else:
        st.markdown(t('whatif.need_odds', lang, need=need_odds, side=side_word, now=side_odds))
    need_line = whatif.needed_line(line=line, side_odds=side_odds, sd=row['sd'], **args)
    if need_line is not None:
        st.markdown(t('whatif.need_line', lang, need=need_line, now=line))
    else:
        st.markdown(t('whatif.need_line_none', lang))
    st.markdown(t('whatif.need_chance', lang, need=now['break-even %'], now=now['p win %']))
    st.caption(t('whatif.why', lang, b=100 * coef.get('b', 1.0)))
    if need_odds is not None and need_odds > side_odds:
        moved = whatif.move_share(odds_paths(), stat, side, need_odds / side_odds)
        if moved['lines']:
            st.caption(t('whatif.history', lang, side=side_word, stat=stat, **moved))
        else:
            st.caption(t('whatif.history_none', lang, stat=stat))

    # sliders: another price or line, priced the same way
    st.markdown(t('whatif.sliders', lang))
    c = st.columns(2)
    odds = c[0].slider(t('whatif.slider_odds', lang, side=side_word), 1.10, 5.00,
                       float(min(max(side_odds, 1.10), 5.0)), 0.01, key=f"whatif_odds_{key}")
    sd = row['sd'] if pd.notna(row['sd']) and row['sd'] > 0 else 1.0
    steps = int(max(1, round(3 * sd)))
    lines = sorted({line + k for k in range(-steps, steps + 1) if line + k >= 0})
    chosen_line = c[1].select_slider(t('whatif.slider_line', lang), lines, value=line, key=f"whatif_line_{key}")
    tried = whatif.evaluate(line=chosen_line, side_odds=odds, **args)
    st.markdown(t('whatif.result', lang, odds=odds, line=chosen_line, p=tried['p win %'], be=tried['break-even %'],
                  dist=tried['distance pp'], ev=tried['ev net 100']))
    if tried['p win %'] > tried['break-even %'] and (odds, chosen_line) != (side_odds, line):
        st.caption(t('whatif.caveat', lang))
    grid = np.round(np.arange(1.10, 5.001, 0.05), 2)
    ev = np.array([whatif.evaluate(line=chosen_line, side_odds=o, **args)['ev net 100'] for o in grid])
    labels = {'x': t('whatif.chart_x', lang, side=side_word), 'y': t('whatif.chart_y', lang),
              'now': t('whatif.chart_now', lang), 'chosen': t('whatif.chart_chosen', lang)}
    charts.show(charts.breakeven_curve(grid, ev, side_odds, odds, labels, t('whatif.chart', lang, line=chosen_line)),
                key='whatif_curve')

    # look back: his last game, then every settled line by its gap in spreads
    st.markdown(t('whatif.lookback', lang))
    settled = settled_lines(tuple(seasons), tuple(season_types))
    tip = pd.to_datetime(row['start_time'], utc=True).tz_convert('US/Eastern').tz_localize(None)
    last = last_game_line(settled, row['player_id'], stat, tip) if pd.notna(row['player_id']) else None
    if last is None:
        st.caption(t('whatif.last_none', lang, stat=stat))
    else:
        result = last['result']
        st.markdown(t('whatif.last', lang, date=f"{pd.Timestamp(last['game_date']):%d.%m}", game=last['game'],
                      line=last['line'], proj=last['proj_avg'],
                      gap=f"{last['gap sd']:+.1f}" if pd.notna(last['gap sd']) else '?',
                      side=value(last['side'], lang), actual=last['actual'],
                      result=t(f"whatif.result.{result}", lang) if result in ('win', 'loss', 'push') else '?',
                      ret=last['return 100'] if pd.notna(last['return 100']) else 0.0))
    groups = gap_groups(settled)
    if groups.empty:
        st.caption(t('whatif.check_none', lang))
        return
    mark = sd_group(pd.Series([gap])).iloc[0] if pd.notna(gap) else None
    st.caption(t('whatif.check', lang))
    charts.show(charts.gap_check(groups, mark, {'won': t('whatif.check_won', lang),
                                                'price': t('whatif.check_price', lang), 'y': '%'},
                                 t('whatif.check_chart', lang)), key='whatif_check')
    here = groups[groups['group'] == mark]
    if len(here):
        g = here.iloc[0]
        st.markdown(t('whatif.check_read', lang, group=g['group'], won=g['won %'], price=g['price %'],
                      diff=g['won − price pp'], low=g['low pp'], high=g['high pp'], ret=g['return 100']))


def line_checker():
    if logs.empty:
        st.caption(t('history.none', lang))
        return
    players = logs.groupby('player_id_ESPN')['player_display_name'].last().sort_values()
    c = st.columns([3, 1, 1])
    pid = c[0].selectbox(t('checker.player', lang), players.index, format_func=players.get, index=None,
                         placeholder=t('checker.pick', lang), key='checker_player')
    stat = c[1].selectbox(t('checker.stat', lang), [s for s in STATS if s != 'MIN'], key='checker_stat')
    line = c[2].number_input(t('checker.line', lang), 0.0, 100.0, 10.5, 0.5, key='checker_line')
    if pid is None:
        return
    values = logs[logs['player_id_ESPN'] == pid].sort_values('Date')[stat]
    rates, last10 = hit_rates(values, line), hit_rates(values.tail(10), line)
    p30, p70 = percentile_band(values)
    kpis([{'label': t('checker.games', lang), 'value': len(values)},
          {'label': t('checker.all', lang), 'value': f"{100 * rates['over']:.0f}% / {100 * rates['under']:.0f}%"},
          {'label': t('checker.last10', lang),
           'value': f"{100 * last10['over']:.0f}% / {100 * last10['under']:.0f}%"},
          {'label': t('checker.band', lang), 'value': f"{p30:.1f} – {p70:.1f}", 'help': t('checker.band_help', lang),
           'delta': t('checker.inside' if p30 <= line <= p70 else 'checker.outside', lang), 'delta_color': 'off'}])


if superbet()['status']['state'] != 'available':
    no_offers(superbet()['status'])
    with st.expander(t('props.checker_any', lang)):
        line_checker()
    stop()
if table_all.empty:
    go_to_data(t('props.no_props', lang))
    with st.container(border=True):
        st.markdown(f"**{t('props.checker', lang)}**")
        line_checker()
    stop()

lineup_banner()

# --- filters ---
for key, default in (('props_games', []), ('props_types', DEFAULT_TYPES), ('props_hide_red', False),
                     ('props_only_best', False),
                     ('props_hide_out', True), ('props_min_games', 5), ('props_more', False),
                     ('props_sort', 'tip')):
    persist(key, default)
if st.session_state['props_sort'] not in SORTS:      # an older choice ('edge') is now the tip-off
    st.session_state['props_sort'] = st.session_state['_props_sort'] = 'tip'
f = st.columns([2, 4, 3, 1], vertical_alignment='bottom')
# tip-off times change their label as the game nears, so they're computed on every run, not cached
table_all = table_all.assign(**{'tip-off': [pl_time(t) for t in table_all['start_time']],
                                'tip_at': pd.to_datetime(table_all['start_time'], utc=True)})
games_by_tip = table_all.sort_values('tip_at').drop_duplicates('game')['game'].tolist()
game_filter = f[0].multiselect(t('props.filter.games', lang), games_by_tip, key='props_games', on_change=remember,
                               args=('props_games',), placeholder=t('props.filter.all_games', lang))
available = sorted(table_all['bet_type'].unique(), key=lambda t: (t not in DEFAULT_TYPES, t))
st.session_state['props_types'] = [t for t in st.session_state['props_types'] if t in available]
type_filter = f[1].pills(t('props.filter.types', lang), available, key='props_types', selection_mode='multi',
                         on_change=remember, args=('props_types',), format_func=lambda s: 'PRA' if s == 'ARP' else s,
                         help=t('props.filter.types_help', lang))
sort = f[2].segmented_control(t('props.sort', lang), SORTS, key='props_sort', on_change=remember,
                              args=('props_sort',), format_func=lambda k: t(f'props.sort.{k}', lang),
                              help=t('props.sort_help', lang)) or 'tip'
with f[3].popover(t('props.more', lang), width='stretch'):
    only_best = st.toggle(t('props.only_best', lang), key='props_only_best', on_change=remember,
                          args=('props_only_best',), help=t('props.only_best_help', lang))
    hide_red = st.toggle(t('props.hide_red', lang), key='props_hide_red', on_change=remember,
                         args=('props_hide_red',))
    hide_out = st.toggle(t('props.hide_out', lang), key='props_hide_out', on_change=remember,
                         args=('props_hide_out',))
    min_games = st.number_input(t('props.min_games', lang), 0, 100, key='props_min_games', on_change=remember,
                                args=('props_min_games',), help=t('props.min_games_help', lang))
    more = st.toggle(t('props.every_column', lang), key='props_more', on_change=remember, args=('props_more',))

shown = table_all[table_all['games'] >= min_games]
if game_filter:
    shown = shown[shown['game'].isin(game_filter)]
if type_filter:
    shown = shown[shown['bet_type'].isin(type_filter)]
if only_best:
    shown = shown[pd.to_numeric(shown['star count'], errors='coerce') >= 3]
if hide_red:
    shown = shown[shown['red flag'].fillna('') == '']
if hide_out:
    shown = shown[~shown['RotoWire'].str.startswith(('Out', 'OFS'))]
shown = sort_lines(shown, sort).reset_index(drop=True)

kpis([{'label': t('props.kpi.shown', lang), 'value': f"{len(shown)} / {len(table_all)}",
       'help': t('props.kpi.shown_help', lang)},
      {'label': t('props.kpi.obstaw', lang), 'value': sum(d['status'] == OBSTAW for d in decided.values()),
       'help': t('props.kpi.obstaw_help', lang)},
      {'label': t('props.kpi.games', lang), 'value': shown['event_id'].nunique()},
      {'label': t('props.kpi.red', lang), 'value': int((shown['red flag'].fillna('') != '').sum()),
       'help': t('props.kpi.red_help', lang)}])

st.markdown(t('props.how_to_choose', lang))
if not any(d['status'] == OBSTAW for d in decided.values()):
    st.info(t('props.all_pass', lang), icon="⚖️")
decisions_banner(table_all.sort_values('tip_at').drop_duplicates('event_id')['event_id']
                 [lambda e: e.isin(shown['event_id']) if len(shown) else e])
columns = MAIN_COLUMNS + (MORE_COLUMNS if more else [])
picked = table(display_values(shown), columns, FORMATS, key='props_table', select=True, height=420,
               legend=['superbet', 'rotowire', 'stats'])
if picked is not None and (st.session_state.get('props_open') or {}).get('index') != picked:
    st.session_state.pop('props_open', None)          # a new pick: its decision is the one now shown
st.caption(t(f'props.order.{sort}', lang) + t('props.order.rest', lang))

# the open offer: picked in the table, sent from the Overview, or the one open before this refresh. It stays open
# when the data refreshes; if its line or odds changed since its decision was shown, the page says so
focus = st.session_state.get('props_focus')
opened = st.session_state.get('props_open')


def _find(key):
    match = table_all[(table_all['event_id'] == key[0]) & (table_all['name_ESPN'] == key[1])
                      & (table_all['bet_type'] == key[2])]
    return match.iloc[0] if len(match) else None


row = None
if picked is not None:
    st.session_state.pop('props_focus', None)
    row = shown.iloc[picked]
    if opened and opened.get('index') == picked and opened['key'] != offer_key(row):
        row = _find(opened['key']) if _find(opened['key']) is not None else row   # the rows moved under the pick
elif focus:
    row = _find(focus)
elif opened:
    row = _find(opened['key'])

if row is None:
    st.info(t('props.pick_row', lang), icon="👆")
elif pd.isna(row['player_id']):
    st.warning(t('props.no_logs', lang, name=row['name']))
elif not row['side']:
    st.info(t('props.no_odds', lang))
else:
    quote = {'line': row['line'], 'odds': row['side odds']}
    seen = opened if opened and opened['key'] == offer_key(row) else None
    changed = offer_changed(seen['quote'] if seen else None, quote)
    if not seen:
        st.session_state['props_open'] = {'key': offer_key(row), 'quote': quote, 'index': picked}
    with st.container(border=True):
        detail(row, changed)

with st.expander(t('props.checker_any', lang)):
    line_checker()
