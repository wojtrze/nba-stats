from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from components import decision_text, decision_times, no_offers, reasons_panel, slip_button
from decisions import OBSTAW, game_decisions, offer_changed, offer_decision, offer_key
from espn_scraper import CURRENT_SEASON
from glossary import column_config, source_legend, tinted
from i18n import t
from loaders import (fetch_rotowire, filtered_logs, games as all_games, player_logs, rotowire_lineups, sidebar_filters,
                     snapshot_history, superbet_fetch_controls, superbet_offers, today_game_odds, today_props)
from metrics import STATS, absence_adjustments, hit_rates, percentile_band
from models import calibration_warning, price_props, top_up_logs
from reasons import flag_props, offer_context, prop_reasons
from schedule import tip_label
from tracking import prop_movement

st.title("Today's props")
seasons, season_types = sidebar_filters()
logs = filtered_logs(seasons, season_types)

superbet_fetch_controls(key='props')
props = today_props()
lineups = rotowire_lineups()
by_player = {pid: g for pid, g in logs.groupby('player_id_ESPN')}
names = logs.groupby('player_id_ESPN')['player_display_name'].last()


@st.cache_data(show_spinner="Adjusting for tonight's absences...")
def cached_adjustments(part, players, out, stats):
    return absence_adjustments(part, players, out, stats)


@st.cache_data(ttl=600, show_spinner="Pricing today's lines...")
def priced(seasons, season_types, props, lineups, odds) -> pd.DataFrame:
    g = all_games()
    g = g[g['season_id'].isin(seasons) & g['season_type'].isin(season_types)]
    # players with few games in the newest chosen season get their latest of the season before
    logs_ = top_up_logs(filtered_logs(list(seasons), list(season_types)), player_logs(),
                        max(seasons, default=CURRENT_SEASON),
                        props['player_id_ESPN'].dropna().unique())
    table = price_props(props, logs_, lineups, odds, g, adjust=cached_adjustments)
    # 🔴 + 'red flag' for lines with a reason to pass whatever the numbers say
    return flag_props(prop_movement(snapshot_history('superbet_props'), table), logs_, lineups)


PROP_TIPS = {'side': "The side with the higher expected return after Superbet's 12% stake tax: the side the "
                     "decision looks at. Not a pick",
             'model %': "Chance the pick wins, calibrated on 2022/23: the model's own chance (raw model %) mapped "
                        "to how often such picks actually won against Unibet's lines. The model alone was "
                        "overconfident, so this sits close to the market's margin-free chance.",
             'raw model %': "The model's own chance before calibration: the hit rate pulled toward the market's "
                            "margin-free chance (worth 10 games), averaged with the chance from proj avg and the "
                            "player's usual spread of results (a count distribution around proj avg)"}


def prop_panel(row, decision, changed=None):
    """The decision for the selected line's game, the reasons behind it, and a link to the full Player page."""
    # the games the line was priced from (priced() tops a player with few games up with last season's)
    games = top_up_logs(by_player.get(row['player_id'], logs.iloc[0:0]), player_logs(),
                        max(seasons, default=CURRENT_SEASON), [row['player_id']])
    every = player_logs()
    history = every[(every['player_id_ESPN'] == row['player_id']) & every['season_type'].isin(season_types)
                    & (every['OPP'].str.lower() == (row['opp'] or ''))]
    bet = offer_context(row, games, logs, lineups, names, superbet_offers()['fetched_at'],
                        fetch_rotowire()['fetched_at'])
    if bet['side'] is None:
        st.info("Superbet has no odds for this line.")
        return
    side = f"{bet['side']} {row['line']:g} {row['bet_type']} @ {row['side odds']:.2f}"
    # only an OBSTAW offer is named as one; any other line shows its evaluated side and what it returns
    title = f"{row['name']} {side}" if decision['status'] == OBSTAW else \
        f"{row['name']} · {side} (evaluated side, {row['ev net 100']:+.1f} per 100 after tax)"
    reasons_panel(title, decision, prop_reasons(bet, games, history), games, row['bet_type'], row['line'],
                  changed=changed)
    b = st.columns([1, 1, 4])
    slip_button({'kind': 'prop', 'event_id': row['event_id'], 'start_time': row['start_time'], 'home': row['home'],
                 'away': row['away'], 'name': row['name'], 'name_ESPN': row['name_ESPN'],
                 'player_id_ESPN': row['player_id'], 'bet_type': row['bet_type'], 'side': row['side'],
                 'line': row['line'], 'odds': row['side odds'], 'model_pct': row['p win %'],
                 'edge_pp': row['edge net pp'], 'edge_low': row['edge low'], 'decision': decision['status']},
                key='slip_prop', where=b[0])
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
    if warning := calibration_warning(table['calibration'].iloc[0] if len(table) else None):
        st.warning(warning, icon="⚠️")
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
    sort = f[5].radio("Sort by", ["Tip-off", "Expected return"], horizontal=True,
                      help="For research: neither order says what to bet, the decision per game does")
    shown = table[table['games'] >= min_games]
    if game_filter:
        shown = shown[shown['game'].isin(game_filter)]
    if type_filter:
        shown = shown[shown['bet_type'].isin(type_filter)]
    if outside:
        shown = shown[~shown['in band']]
    if hide_out:
        shown = shown[~shown['RotoWire'].str.startswith(('Out', 'OFS'))]
    # the one decision for each game's players (decisions.py), shown above the table
    rotowire = fetch_rotowire()
    decided = game_decisions(table, table['calibration'].iloc[0],
                             lineups.assign(fetched_at=rotowire['fetched_at']) if len(lineups) else lineups,
                             superbet_offers()['fetched_at'], datetime.now(timezone.utc))
    with st.container(border=True):
        st.markdown("**Tonight's decisions · players**")
        for event_id in table.sort_values('tip_at').drop_duplicates('event_id')['event_id']:
            d = decided[event_id]
            game = table.loc[table['event_id'] == event_id, 'game'].iloc[0]
            st.markdown(f"- **{game}**: {decision_text(d)}  \n  :gray[{decision_times(d)}]")
    if not any(d['status'] == OBSTAW for d in decided.values()):
        st.info("No offer meets the condition for 'Bet' (no threshold has been recorded on an independent period), "
                "so every game's decision is Don't bet, Wait or Unavailable. The table is for research, not a list "
                "of bets.", icon="⚖️")
    # warned lines after the others, within each game when sorted by tip-off
    shown = shown.assign(red=shown['red flag'].fillna('') != '',
                         decision=[t(f"decision.{offer_decision(decided[r['event_id']], r)['status']}", 'en')
                                   for _, r in shown.iterrows()])
    order = (['tip_at', 'game', 'red'] if sort == "Tip-off" else ['red']) + ['ev net 100']
    shown = shown.sort_values(order, ascending=[True] * (len(order) - 1) + [False]).reset_index(drop=True)

    sorted_by = "earliest tip-off first" if sort == "Tip-off" else "highest expected return after tax first"
    st.caption(f"{len(shown)} of {len(table)} lines, {sorted_by}, warnings last. ⏰ = tip-off within the hour; lines "
               f"leave the list at tip-off. Hover a column header for what it means. side = the side with the "
               f"higher expected return after Superbet's 12% stake tax; every price below includes the tax. Click a "
               f"row for the decision and the reasons behind it.")
    st.caption(source_legend())
    # who/what -> the decision -> tonight's lineup -> the player's numbers -> both sides' odds
    columns = ['name', 'game', 'tip-off', 'bet_type', 'line',
               'decision', 'side', 'side odds', 'p win %', 'break-even net %', 'edge net pp', 'ev net 100',
               'RotoWire', 'red flag', 'line move', 'open line',
               'proj avg', 'adj avg', 'avg', 'avg L5', 'matchup', 'spread', 'game total', 'percentile', 'in band',
               'over %', 'under %', 'over % L10', 'under % L10', 'games', 'min L5',
               'raw model %', 'over_odds', 'under_odds']
    formats = {'raw model %': '%.0f',
               'avg': '%.1f', 'adj avg': '%.1f', 'avg L5': '%.1f', 'min L5': '%.1f', 'over %': '%.0f',
               'under %': '%.0f', 'over % L10': '%.0f', 'under % L10': '%.0f', 'percentile': '%.0f',
               'over_odds': '%.2f', 'under_odds': '%.2f', 'side odds': '%.2f', 'edge net pp': '%+.1f',
               'ev net 100': '%+.1f', 'p win %': '%.0f', 'break-even net %': '%.1f', 'games': '%d', 'proj avg': '%.1f',
               'spread': '%+g', 'line move': '%+g', 'open line': '%g', 'game total': '%g', 'line': '%g'}
    event = st.dataframe(tinted(shown[columns], formats), hide_index=True, width='stretch', height=600,
                         column_config=column_config(columns, formats, tips=PROP_TIPS), on_select='rerun',
                         selection_mode='single-row', key='props_table')
    # the open line stays open across refreshes; a changed line or odds is said out loud
    opened = st.session_state.get('v1_props_open')
    row = None
    if event.selection.rows:
        row = shown.iloc[event.selection.rows[0]]
        if opened and opened['index'] == event.selection.rows[0] and opened['key'] != offer_key(row):
            moved = shown[[offer_key(r) == opened['key'] for _, r in shown.iterrows()]]
            row = moved.iloc[0] if len(moved) else row
        elif not opened or opened['key'] != offer_key(row):
            opened = None
    elif opened:
        moved = shown[[offer_key(r) == opened['key'] for _, r in shown.iterrows()]]
        row = moved.iloc[0] if len(moved) else None
    if row is not None:
        quote = {'line': row['line'], 'odds': row['side odds']}
        changed = offer_changed(opened['quote'] if opened else None, quote)
        if not opened:
            st.session_state['v1_props_open'] = {'key': offer_key(row), 'quote': quote,
                                                 'index': event.selection.rows[0] if event.selection.rows else None}
        if row['player_id'] is not None and pd.notna(row['player_id']):
            prop_panel(row, offer_decision(decided[row['event_id']], row), changed)
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
