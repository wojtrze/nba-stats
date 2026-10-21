from datetime import datetime, timezone

import numpy as np
import pandas as pd
import streamlit as st

from components import no_offers, reasons_panel, slip_button
from glossary import column_config, source_legend, tinted
from loaders import (filtered_logs, games as all_games, player_logs, rotowire_lineups, sidebar_filters, snapshot_history,
                     superbet_fetch_controls, superbet_offers, today_game_odds, today_props)
from metrics import STATS, absence_adjustments, hit_rates, percentile_band, rotowire_team
from models import price_props
from reasons import prop_reasons
from schedule import tip_label
from tracking import prop_movement

st.title("Today's props")
seasons, season_types = sidebar_filters()
logs = filtered_logs(seasons, season_types)

superbet_fetch_controls(key='props')
props = today_props()
lineups = rotowire_lineups()
by_player = {pid: g for pid, g in logs.groupby('player_id_ESPN')}
position = logs.groupby('player_id_ESPN')['position_group'].last()
names = logs.groupby('player_id_ESPN')['player_display_name'].last()


@st.cache_data(show_spinner="Adjusting for tonight's absences...")
def cached_adjustments(part, players, out, stats):
    return absence_adjustments(part, players, out, stats)


@st.cache_data(ttl=600, show_spinner="Pricing today's lines...")
def priced(seasons, season_types, props, lineups, odds) -> pd.DataFrame:
    g = all_games()
    g = g[g['season_id'].isin(seasons) & g['season_type'].isin(season_types)]
    table = price_props(props, filtered_logs(list(seasons), list(season_types)), lineups, odds, g,
                        adjust=cached_adjustments)
    return prop_movement(snapshot_history('superbet_props'), table)


def rotowire_entry(player_id) -> dict:
    listed = lineups[lineups['player_id_ESPN'] == player_id]
    return listed.iloc[0].to_dict() if len(listed) else {}


PROP_TIPS = {'model %': "Chance the pick wins: the hit rate pulled toward the market's margin-free chance (worth "
                        "10 games), averaged with the chance from proj avg and the player's usual spread of results"}


def prop_panel(row):
    """The reasons for and against the selected line, and a link to the full Player page."""
    games = by_player.get(row['player_id'], logs.iloc[0:0])
    every = player_logs()
    history = every[(every['player_id_ESPN'] == row['player_id']) & every['season_type'].isin(season_types)
                    & (every['OPP'].str.lower() == (row['opp'] or ''))]
    entry = rotowire_entry(row['player_id'])
    tip = pd.to_datetime(row['start_time']).tz_convert('US/Eastern').tz_localize(None).normalize()
    rest = (tip - games['Date'].iloc[-1]).days if len(games) else np.nan
    starter = row['RotoWire'].startswith('starter') if row['RotoWire'] else \
        bool(len(games) and games['starter'].tail(10).mean() > 0.5)
    bet = {'name': row['name'], 'stat': row['bet_type'], 'side': row['best side'], 'line': row['line'],
           'odds': row['pick odds'], 'model %': row['model %'], 'break-even %': row['break-even %'],
           'edge pp': row['edge pp'], 'edge low': row['edge low'], 'avg': row['avg'], 'proj avg': row['proj avg'],
           'lineup adj': row['lineup adj'], 'status': row['RotoWire'], 'play_pct': entry.get('play_pct', np.nan),
           'out_names': [str(names.get(p, p)) for p in rotowire_team(lineups, row['team'])['out']],
           'home': row['is_home'], 'rest_days': rest, 'opp': row['opp'] or '', 'team': row['team'] or '',
           'matchup': row['matchup_info'], 'position': position.get(row['player_id']), 'implied': row['implied'],
           'team_pts': row['team_pts'], 'spread': row['spread'], 'starter': starter,
           'line_move': row.get('line move', np.nan)}
    if bet['side'] is None:
        st.info("Superbet has no odds for this line.")
        return
    reasons_panel(f"{row['name']} {bet['side']} {row['line']:g} {row['bet_type']} @ {row['pick odds']:.2f}",
                  prop_reasons(bet, games, history), row['edge pp'], row['edge low'], games, row['bet_type'],
                  row['line'])
    b = st.columns([1, 1, 4])
    slip_button({'kind': 'prop', 'event_id': row['event_id'], 'start_time': row['start_time'], 'home': row['home'],
                 'away': row['away'], 'name': row['name'], 'name_ESPN': row['name_ESPN'],
                 'player_id_ESPN': row['player_id'], 'bet_type': row['bet_type'], 'side': row['best side'],
                 'line': row['line'], 'odds': row['pick odds'], 'model_pct': row['model %'], 'edge_pp': row['edge pp'],
                 'edge_low': row['edge low']}, key='slip_prop', where=b[0])
    if b[1].button("Open player page", key='open_player'):
        st.session_state['player_preset'] = {'player_id': row['player_id'], 'stat': row['bet_type'],
                                             'line': row['line']}
        st.switch_page("views/player.py")


status = superbet_offers()['status']
if status['state'] != 'available':
    no_offers(status, key='props_no_offers')
elif props.empty:
    st.info("No Superbet player props for upcoming games. Press Fetch from Superbet (or save a snapshot on Data "
            "status) to get today's. During preseason Superbet only offers game markets; props usually appear from "
            "the first regular-season games. Use the line checker below meanwhile.")
else:
    table = priced(tuple(seasons), tuple(season_types), props, lineups, today_game_odds())
    # the tip-off label changes as the game nears, so it's computed on every run, not cached
    now = datetime.now(timezone.utc)
    table = table.assign(**{'tip-off': [tip_label(t, now) for t in table['start_time']],
                            'tip_at': pd.to_datetime(table['start_time'], utc=True)})

    f = st.columns([2, 2, 1, 2, 2, 2])
    game_filter = f[0].multiselect("Games", table.sort_values('tip_at').drop_duplicates('game')['game'].tolist(),
                                   help="In tip-off order")
    type_filter = f[1].multiselect("Bet types", sorted(table['bet_type'].unique()),
                                   default=[t for t in ['PTS', 'REB', 'AST', '3PM', 'PA', 'PR', 'RA', 'ARP']
                                            if t in set(table['bet_type'])],
                                   help="PA = points+assists, PR = points+rebounds, RA = rebounds+assists, "
                                        "ARP = points+rebounds+assists. Shooting, fouls, steals, blocks and "
                                        "turnovers are left out by default.")
    min_games = f[2].number_input("Min games", 0, 100, 5, help="Hide players with fewer games in the data")
    outside = f[3].toggle("Only lines outside the 30–70% band",
                          help="Lines below the player's 30th or above their 70th percentile")
    hide_out = f[4].toggle("Hide players RotoWire lists as out", value=True)
    sort = f[5].radio("Sort by", ["Tip-off, then edge", "Edge"], horizontal=True,
                      help="Tip-off: the earliest game first, the biggest edges first within a game")
    shown = table[table['games'] >= min_games]
    if game_filter:
        shown = shown[shown['game'].isin(game_filter)]
    if type_filter:
        shown = shown[shown['bet_type'].isin(type_filter)]
    if outside:
        shown = shown[~shown['in band']]
    if hide_out:
        shown = shown[~shown['RotoWire'].str.startswith(('Out', 'OFS'))]
    order = (['tip_at', 'game'] if sort.startswith("Tip-off") else []) + ['edge pp']
    shown = shown.sort_values(order, ascending=[True] * (len(order) - 1) + [False]).reset_index(drop=True)

    sorted_by = "earliest tip-off first, best edge first within a game" if order[0] == 'tip_at' else \
        "best edge first"
    st.caption(f"{len(shown)} of {len(table)} lines, {sorted_by}. ⏰ = tip-off within the hour; lines leave the "
               f"list at tip-off. Hover a column header for what it means. "
               f"🟢 = even the low end of the model's range beats the price; 🟡 = positive edge, but too little data "
               f"to be sure. Click a row for the reasons to bet or pass.")
    st.caption(source_legend())
    # who/what -> the decision -> tonight's lineup -> the player's numbers -> both sides' odds
    columns = ['name', 'game', 'tip-off', 'bet_type', 'line',
               'best side', 'signal', 'edge pp', 'edge low', 'pick odds', 'model %', 'break-even %', 'market %',
               'RotoWire', 'line move', 'open line',
               'proj avg', 'adj avg', 'avg', 'avg L5', 'matchup', 'spread', 'game total', 'percentile', 'in band',
               'over %', 'under %', 'over % L10', 'under % L10', 'games', 'min L5',
               'over_odds', 'under_odds']
    formats = {'avg': '%.1f', 'adj avg': '%.1f', 'avg L5': '%.1f', 'min L5': '%.1f', 'over %': '%.0f',
               'under %': '%.0f', 'over % L10': '%.0f', 'under % L10': '%.0f', 'percentile': '%.0f',
               'over_odds': '%.2f', 'under_odds': '%.2f', 'pick odds': '%.2f', 'edge pp': '%+.1f', 'edge low': '%+.1f',
               'model %': '%.0f', 'break-even %': '%.0f', 'market %': '%.0f', 'games': '%d', 'proj avg': '%.1f',
               'spread': '%+g', 'line move': '%+g', 'open line': '%g', 'game total': '%g', 'line': '%g'}
    event = st.dataframe(tinted(shown[columns], formats), hide_index=True, width='stretch', height=600,
                         column_config=column_config(columns, formats, tips=PROP_TIPS), on_select='rerun',
                         selection_mode='single-row', key='props_table')
    if event.selection.rows:
        row = shown.iloc[event.selection.rows[0]]
        if row['player_id'] is not None and pd.notna(row['player_id']):
            prop_panel(row)
        else:
            st.warning(f"No game logs for {row['name']}: the Superbet name didn't match an ESPN player. "
                       f"Add it to OVERRIDES in name_resolver.py.")

st.divider()
st.subheader("Line checker")
if logs.empty:
    st.info("No game logs for the chosen seasons and game types.")
    st.stop()
players = logs.groupby('player_id_ESPN')['player_display_name'].last().sort_values()
c = st.columns([3, 1, 1, 1])
pid = c[0].selectbox("Player", players.index, format_func=players.get, index=None, placeholder="Type a name...", key='checker_player')
stat = c[1].selectbox("Bet type", [s for s in STATS if s != 'MIN'], key='checker_stat')
line = c[2].number_input("Line", 0.0, 100.0, 10.5, 0.5, key='checker_line')
if pid is not None:
    values = logs[logs['player_id_ESPN'] == pid].sort_values('Date')[stat]
    rates, last10 = hit_rates(values, line), hit_rates(values.tail(10), line)
    p30, p70 = percentile_band(values)
    m = st.columns(4)
    m[0].metric("Games", len(values), help="Games in the sidebar's seasons and game types")
    m[1].metric("Over / Under (all)", f"{100 * rates['over']:.0f}% / {100 * rates['under']:.0f}%",
                help="Share of games above / below the line. Games exactly on a whole-number line count for neither.")
    m[2].metric("Over / Under (last 10)", f"{100 * last10['over']:.0f}% / {100 * last10['under']:.0f}%",
                help="The same for the last 10 games")
    m[3].metric("30–70% band", f"{p30:.1f} – {p70:.1f}", "line inside" if p30 <= line <= p70 else "line outside",
                delta_color="off", help="The player's 30th to 70th percentile. A line outside it looks unusually "
                                        "low or high for this player.")
    if c[3].button("Open player page"):
        st.session_state['player_preset'] = {'player_id': pid, 'stat': stat, 'line': line}
        st.switch_page("views/player.py")
