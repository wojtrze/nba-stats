import numpy as np
import pandas as pd
import streamlit as st

from components import reasons_panel
from core import charts
from core.analysis import teammate_impact
from core.data import lineups as rotowire_lineups, priced_props, superbet
from core.state import persist, remember
from core.ui import PAGES, go_to_data, kpis, no_offers, page_header, pl_time, stop, table
from glossary import column_config
from loaders import filtered_logs, player_logs, snapshot_history
from metrics import STATS, hit_rates, percentile_band, rotowire_team, splits
from reasons import prop_reasons
from tracking import PROP_KEY

seasons, season_types = page_header(
    "Props", "Superbet's player lines for the next 36 hours, priced against each player's games and adjusted for "
             "tonight's RotoWire lineups. Pick a row to see why to bet or pass.", with_scope=True)
logs = filtered_logs(seasons, season_types)
lineups = rotowire_lineups()
table_all = priced_props(seasons, season_types)

DEFAULT_TYPES = ['PTS', 'REB', 'AST', '3PM', 'PA', 'PR', 'RA', 'ARP']
SIGNALS = {'all': "All", 'positive': "🟢🟡 Edge", 'sure': "🟢 Holds"}
FORMATS = {'raw model %': '%.0f',
           'line': '%g', 'edge pp': '%+.1f', 'edge low': '%+.1f', 'pick odds': '%.2f', 'model %': '%.0f',
           'proj avg': '%.1f', 'pick % L10': '%.0f', 'pick %': '%.0f', 'break-even %': '%.0f', 'market %': '%.0f',
           'avg': '%.1f', 'adj avg': '%.1f', 'avg L5': '%.1f', 'min L5': '%.1f', 'percentile': '%.0f',
           'over_odds': '%.2f', 'under_odds': '%.2f', 'games': '%d', 'line move': '%+g', 'open line': '%g',
           'spread': '%+g', 'game total': '%g'}
TIPS = {'pick % L10': "How often the picked side won in the player's last 10 games",
        'pick %': "How often the picked side won in all the games shown",
        'model %': "Chance the pick wins, calibrated on 2022/23: the model's own chance (raw model %) mapped to how "
                   "often such picks actually won against Unibet's lines. The model alone was "
                   "overconfident, so this sits close to the market's margin-free chance.",
        'raw model %': "The model's own chance before calibration: the hit rate pulled toward the market's "
                       "margin-free chance (worth 10 games), averaged with the chance from proj avg and the player's "
                       "usual spread of results"}
MAIN_COLUMNS = ['name', 'game', 'tip-off', 'bet_type', 'line', 'best side', 'signal', 'edge pp', 'pick odds',
                'model %', 'proj avg', 'pick % L10', 'RotoWire']
MORE_COLUMNS = ['edge low', 'break-even %', 'market %', 'line move', 'open line', 'adj avg', 'avg', 'avg L5',
                'matchup', 'spread', 'game total', 'percentile', 'pick %', 'games', 'min L5', 'raw model %',
                'over_odds', 'under_odds']


def lineup_banner():
    """Says whether tonight's numbers include RotoWire's lineups, game by game."""
    games_ = table_all.drop_duplicates('event_id')[['game', 'home', 'away']]
    listed = lineups.drop_duplicates('team').set_index('team')['lineup_status'] if len(lineups) else pd.Series()
    confirmed = sum(listed.get(h) == 'confirmed' and listed.get(a) == 'confirmed'
                    for h, a in zip(games_['home'], games_['away']))
    known = [g for g, h, a in zip(games_['game'], games_['home'], games_['away']) if h in listed and a in listed]
    missing = [g for g in games_['game'] if g not in known]
    if not known:
        st.info("📋 RotoWire doesn't list tonight's lineups (yet), so the averages aren't adjusted for absences. "
                "Lineup lab can still show each player's numbers without a teammate.", icon="ℹ️")
    elif missing:
        st.caption(f"📋 Adjusted with RotoWire's lineups for {len(known)} of {len(games_)} games "
                   f"({confirmed} confirmed). Not listed yet: {', '.join(missing)}.")
    else:
        st.caption(f"📋 Every game adjusted with RotoWire's lineups ({confirmed} of {len(games_)} confirmed).")


def detail(row: pd.Series):
    """The selected line: verdict, teammates, history and line movement in tabs."""
    pid = row['player_id']
    games = logs[logs['player_id_ESPN'] == pid].sort_values('Date')
    stat, line = row['bet_type'], row['line']
    st.markdown(f"### {row['name']} · {row['best side']} {line:g} {stat} @ {row['pick odds']:.2f}")
    st.caption(f"{row['game']} · {pl_time(row['start_time'])} · {row['RotoWire'] or 'not on RotoWire yet'}")
    verdict_tab, mates_tab, history_tab, move_tab = st.tabs(
        ["Verdict", "Teammates (with / without)", "History", "Line movement"])

    with verdict_tab:
        every = player_logs()
        history = every[(every['player_id_ESPN'] == pid) & every['season_type'].isin(season_types)
                        & (every['OPP'].str.lower() == (row['opp'] or ''))]
        listed = lineups[lineups['player_id_ESPN'] == pid]
        tip = pd.to_datetime(row['start_time']).tz_convert('US/Eastern').tz_localize(None).normalize()
        names = logs.groupby('player_id_ESPN')['player_display_name'].last()
        bet = {'name': row['name'], 'stat': stat, 'side': row['best side'], 'line': line, 'odds': row['pick odds'],
               'model %': row['model %'], 'break-even %': row['break-even %'], 'edge pp': row['edge pp'],
               'edge low': row['edge low'], 'avg': row['avg'], 'proj avg': row['proj avg'],
               'lineup adj': row['lineup adj'], 'status': row['RotoWire'],
               'play_pct': listed['play_pct'].iloc[0] if len(listed) else np.nan,
               'out_names': [str(names.get(p, p)) for p in rotowire_team(lineups, row['team'])['out']],
               'home': row['is_home'], 'rest_days': (tip - games['Date'].iloc[-1]).days if len(games) else np.nan,
               'opp': row['opp'] or '', 'team': row['team'] or '', 'matchup': row['matchup_info'],
               'position': games['position_group'].iloc[-1] if len(games) else None, 'implied': row['implied'],
               'team_pts': row['team_pts'], 'spread': row['spread'],
               'starter': row['RotoWire'].startswith('starter') if row['RotoWire'] else
               bool(len(games) and games['starter'].tail(10).mean() > 0.5),
               'line_move': row.get('line move', np.nan)}
        reasons_panel(f"{row['best side']} {line:g} {stat}", prop_reasons(bet, games, history), row['edge pp'],
                      row['edge low'], games, stat, line)
        st.markdown("**How the expected number was built**")
        kpis([{'label': "Average", 'value': f"{row['avg']:.1f}", 'help': f"{row['games']} games in the scope"},
              {'label': "+ teammates out", 'value': f"{row['adj avg']:.1f}", 'delta': f"{row['lineup adj']:+.1f}",
               'delta_color': 'off', 'help': "The player's usual change when RotoWire's out players miss games"},
              {'label': "+ game & matchup", 'value': f"{row['proj avg']:.1f}",
               'delta': f"{row['proj avg'] - row['adj avg']:+.1f}", 'delta_color': 'off',
               'help': f"Superbet's implied team total vs the team's usual points (×{row['pace factor']:.2f}) and "
                       f"what the opponent allows to the position (×{row['matchup factor']:.2f}, "
                       f"{row['matchup'] or 'unknown'})"},
              {'label': "Line", 'value': f"{line:g}", 'delta': f"{line - row['proj avg']:+.1f} vs expected",
               'delta_color': 'off'}])
        b = st.columns(3)
        if b[0].button("Open in Player history", width='stretch'):
            st.session_state['player_preset'] = {'player_id': pid, 'stat': stat, 'line': float(line)}
            st.switch_page(PAGES['player'])
        if row['team'] and b[1].button(f"Open {row['team'].upper()} in Lineup lab", width='stretch'):
            st.session_state['lineup_team'] = row['team']
            st.switch_page(PAGES['lineup'])

    with mates_tab:
        if not row['team']:
            st.caption("The player's team isn't known from the stored games.")
        else:
            out = rotowire_team(lineups, row['team'])['out']
            every_season = st.toggle("Use every stored season", value=True, key='mates_all_seasons',
                                     help="Early in the season the current season has too few games without "
                                          "anyone; earlier seasons only count while both were on the team")
            source = player_logs()[player_logs()['season_type'].isin(season_types)] if every_season else logs
            impact = teammate_impact(source, pid, row['team'], stat, out)
            shown = impact[impact['n_without'] > 0]
            if row['team'] not in set(lineups['team']):
                st.caption("📋 RotoWire doesn't list this team tonight, so nobody is marked out.")
            elif out:
                st.caption(f"📋 Out tonight (outlined): {', '.join(impact.loc[impact['out tonight'], 'teammate'])}. "
                           f"Their changes are already in the average above ({row['lineup adj']:+.1f}).")
            if shown.empty:
                st.caption("No teammate missed a game this player played, so there's nothing to compare yet.")
            else:
                shown = shown.assign(hover=[f"{r['teammate']} out: {r['without']:.1f} in {r['n_without']:.0f} games"
                                            f"<br>playing: {r['with']:.1f} in {r['n_with']:.0f} games"
                                            for _, r in shown.iterrows()])
                charts.show(charts.change_bars(shown.head(12), 'teammate', 'change', 'out tonight', 'hover',
                                               f"{row['name']}'s {stat} when each teammate doesn't play"),
                            key='mates_chart')
                st.dataframe(impact, hide_index=True, width='stretch', column_order=[
                    'teammate', 'out tonight', 'change', 'without', 'n_without', 'with', 'n_with'],
                    column_config={'change': st.column_config.NumberColumn(
                        "change", format='%+.1f', help=f"{stat} without the teammate minus with"),
                        'with': st.column_config.NumberColumn(f"{stat} with", format='%.1f'),
                        'without': st.column_config.NumberColumn(f"{stat} without", format='%.1f'),
                        'n_with': st.column_config.NumberColumn("games with", format='%d'),
                        'n_without': st.column_config.NumberColumn("games without", format='%d')})
                st.caption("Few games without a teammate make a change unreliable: 3 games is a hint, 10+ is "
                           "evidence. Only games inside the teammate's time on the team count.")

    with history_tab:
        if games.empty:
            st.caption("No games in the scope.")
        else:
            charts.show(charts.game_log(games, stat, line, last=20, minutes=True,
                                        title=f"Last {min(20, len(games))} games vs the line"), key='hist_log')
            left, right = st.columns(2)
            with left:
                charts.show(charts.distribution(games[stat], stat, line, "Every game in the scope"), key='hist_dist')
            with right:
                st.markdown("**Splits**")
                sp = splits(games, stat, line)
                st.dataframe(sp, hide_index=True, width='stretch',
                             column_config=column_config(sp.columns, {'avg': '%.1f', 'median': '%.1f',
                                                                      'over %': '%.0f'}))
                if len(history):
                    st.markdown(f"**Against {row['opp'].upper()}** (every stored season): "
                                f"{history[stat].mean():.1f} avg in {len(history)} games, "
                                f"over {line:g} in {(history[stat] > line).sum()}")

    with move_tab:
        snaps = snapshot_history('superbet_props')
        if snaps.empty:
            st.caption("No snapshots saved yet, so there's no history of this line.")
        else:
            key = dict(zip(PROP_KEY, [row['event_id'], row['name_ESPN'], stat]))
            mine = snaps[(snaps['event_id'] == key['event_id']) & (snaps['name_ESPN'] == key['name_ESPN'])
                         & (snaps['bet_type'] == stat)]
            if mine.empty:
                st.caption("This line isn't in any saved snapshot yet.")
            else:
                mine = mine.assign(time=pd.to_datetime(mine['fetched_at'], utc=True)
                                   .dt.tz_convert('Europe/Warsaw').dt.strftime('%a %H:%M'))
                st.dataframe(mine[['time', 'line', 'over_odds', 'under_odds']], hide_index=True, width='stretch',
                             column_config=column_config(['line', 'over_odds', 'under_odds'],
                                                         {'over_odds': '%.2f', 'under_odds': '%.2f', 'line': '%g'}))
                st.caption(f"Now: line {line:g}, over {row['over_odds']:.2f} / under {row['under_odds']:.2f}. "
                           f"A line moving with the pick (up for an Over) means the market agrees.")


def line_checker():
    if logs.empty:
        st.caption("No games in the scope.")
        return
    players = logs.groupby('player_id_ESPN')['player_display_name'].last().sort_values()
    c = st.columns([3, 1, 1])
    pid = c[0].selectbox("Player", players.index, format_func=players.get, index=None, placeholder="Type a name...",
                         key='checker_player')
    stat = c[1].selectbox("Bet type", [s for s in STATS if s != 'MIN'], key='checker_stat')
    line = c[2].number_input("Line", 0.0, 100.0, 10.5, 0.5, key='checker_line')
    if pid is None:
        return
    values = logs[logs['player_id_ESPN'] == pid].sort_values('Date')[stat]
    rates, last10 = hit_rates(values, line), hit_rates(values.tail(10), line)
    p30, p70 = percentile_band(values)
    kpis([{'label': "Games", 'value': len(values)},
          {'label': "Over / Under (all)", 'value': f"{100 * rates['over']:.0f}% / {100 * rates['under']:.0f}%"},
          {'label': "Over / Under (last 10)", 'value': f"{100 * last10['over']:.0f}% / {100 * last10['under']:.0f}%"},
          {'label': "30–70% band", 'value': f"{p30:.1f} – {p70:.1f}",
           'delta': "line inside" if p30 <= line <= p70 else "line outside", 'delta_color': 'off'}])


if superbet()['status']['state'] != 'available':
    no_offers(superbet()['status'])
    with st.expander("Line checker: any player, any line"):
        line_checker()
    stop()
if table_all.empty:
    go_to_data("**Superbet has no player props right now.** In preseason it only offers game markets; props appear "
               "with the regular season. If games are on tonight, fetch the offers again in the Data center. "
               "Meanwhile, check any line by hand below.")
    with st.container(border=True):
        st.markdown("**Line checker**")
        line_checker()
    stop()

lineup_banner()

# --- filters ---
for key, default in (('props_games', []), ('props_types', DEFAULT_TYPES), ('props_signal', 'all'),
                     ('props_hide_out', True), ('props_min_games', 5), ('props_more', False),
                     ('props_sort', 'tip-off')):
    persist(key, default)
f = st.columns([2, 4, 2, 1], vertical_alignment='bottom')
# tip-off times change their label as the game nears, so they're computed on every run, not cached
table_all = table_all.assign(**{'tip-off': [pl_time(t) for t in table_all['start_time']],
                                'tip_at': pd.to_datetime(table_all['start_time'], utc=True)})
games_by_tip = table_all.sort_values('tip_at').drop_duplicates('game')['game'].tolist()
game_filter = f[0].multiselect("Games", games_by_tip, key='props_games', on_change=remember,
                               args=('props_games',), placeholder="All games")
available = sorted(table_all['bet_type'].unique(), key=lambda t: (t not in DEFAULT_TYPES, t))
st.session_state['props_types'] = [t for t in st.session_state['props_types'] if t in available]
type_filter = f[1].pills("Bet types", available, key='props_types', selection_mode='multi', on_change=remember,
                         args=('props_types',), format_func=lambda t: 'PRA' if t == 'ARP' else t,
                         help="PA = points+assists, PR = points+rebounds, RA = rebounds+assists, PRA = all three")
signal = f[2].segmented_control("Signal", list(SIGNALS), format_func=SIGNALS.get, key='props_signal',
                                on_change=remember, args=('props_signal',),
                                help="🟢 = even the low end of the model's range beats the price; 🟡 = positive edge "
                                     "but too little data to be sure")
with f[3].popover("More", width='stretch'):
    hide_out = st.toggle("Hide players RotoWire lists as out", key='props_hide_out', on_change=remember,
                         args=('props_hide_out',))
    min_games = st.number_input("Min games", 0, 100, key='props_min_games', on_change=remember,
                                args=('props_min_games',), help="Hide players with fewer games in the scope")
    more = st.toggle("Show every column", key='props_more', on_change=remember, args=('props_more',))
    sort = st.segmented_control("Sort by", ['tip-off', 'edge'], key='props_sort', on_change=remember,
                                args=('props_sort',), format_func={'tip-off': "Tip-off, then edge",
                                                                   'edge': "Edge only"}.get) or 'tip-off'

shown = table_all[table_all['games'] >= min_games]
if game_filter:
    shown = shown[shown['game'].isin(game_filter)]
if type_filter:
    shown = shown[shown['bet_type'].isin(type_filter)]
if signal == 'positive':
    shown = shown[shown['signal'] != '']
elif signal == 'sure':
    shown = shown[shown['signal'] == '🟢']
if hide_out:
    shown = shown[~shown['RotoWire'].str.startswith(('Out', 'OFS'))]
# earliest game first, greens and the biggest edges first within a game; or edge only
order = (['tip_at', 'game'] if sort == 'tip-off' else []) + ['signal', 'edge pp']
shown = shown.sort_values(order, ascending=[True] * (len(order) - 1) + [False],
                          key=lambda c: c.map({'🟢': 0, '🟡': 1, '': 2}) if c.name == 'signal' else c)
shown = shown.reset_index(drop=True)

kpis([{'label': "Lines shown", 'value': f"{len(shown)} / {len(table_all)}",
       'help': "Lines that pass the filters, of every line Superbet offers"},
      {'label': "🟢 Edge holds", 'value': int((shown['signal'] == '🟢').sum()),
       'help': "The edge stays positive even at the low end of the model's range"},
      {'label': "🟡 Positive edge", 'value': int((shown['signal'] == '🟡').sum())},
      {'label': "Games", 'value': shown['event_id'].nunique()},
      {'label': "Players out", 'value': int(lineups['role'].eq('may_not_play').sum()) if len(lineups) else 0,
       'help': "Players RotoWire lists under may not play"}])

columns = MAIN_COLUMNS + (MORE_COLUMNS if more else [])
picked = table(shown, columns, FORMATS, TIPS, key='props_table', select=True, height=420,
               legend=['superbet', 'rotowire', 'stats'])
st.caption(("Earliest tip-off first; within a game greens first, then by edge" if sort == 'tip-off' else
            "Greens first, then by edge") + ". ⏰ = tip-off within the hour; lines leave the list at tip-off. Hover "
           "a header for what it means; pick a row for the details. model % is calibrated on 2022/23, where the "
           "model's own opinion proved worth little beyond the price, so few lines show an edge.")

# a line sent from the Overview opens here until a row is picked
focus = st.session_state.get('props_focus')
if picked is not None:
    st.session_state.pop('props_focus', None)
    row = shown.iloc[picked]
elif focus:
    match = table_all[(table_all['event_id'] == focus[0]) & (table_all['name_ESPN'] == focus[1])
                      & (table_all['bet_type'] == focus[2])]
    row = match.iloc[0] if len(match) else None
else:
    row = None

if row is None:
    st.info("Pick a row in the table to see the reasons to bet or pass, the teammates' effect and the history.",
            icon="👆")
elif pd.isna(row['player_id']):
    st.warning(f"No game logs for {row['name']}: the Superbet name didn't match an ESPN player. Add it to "
               f"OVERRIDES in name_resolver.py.")
elif pd.isna(row['best side']):
    st.info("Superbet has no odds for this line.")
else:
    with st.container(border=True):
        detail(row)

with st.expander("Line checker: any player, any line"):
    line_checker()
