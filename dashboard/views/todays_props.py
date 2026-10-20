import numpy as np
import pandas as pd
import streamlit as st

from glossary import column_config, source_legend, tinted
from loaders import filtered_logs, rotowire_lineups, sidebar_filters, superbet_offers, today_props
from metrics import STATS, absence_adjustments, hit_rates, line_percentile, percentile_band, rotowire_team

st.title("Today's props")
seasons, season_types = sidebar_filters()
logs = filtered_logs(seasons, season_types)

top = st.columns([1, 4])
if top[0].button("Refresh offers"):
    superbet_offers.clear()
    rotowire_lineups.clear()
props = today_props()
lineups = rotowire_lineups()
by_player = {pid: g for pid, g in logs.sort_values('Date').groupby('player_id_ESPN')}
current_team = logs.sort_values('Date').groupby('player_id_ESPN')['team'].last()


@st.cache_data(show_spinner="Adjusting for tonight's absences...")
def cached_adjustments(seasons, season_types, players, out):
    part = filtered_logs(list(seasons), list(season_types))
    return absence_adjustments(part[part['player_id_ESPN'].isin(set(players) | set(out))], players, out, STATS)


def lineup_adjustments(table: pd.DataFrame) -> pd.Series:
    """Each line's stat change from RotoWire's out players on the player's team (0 when nobody is out)."""
    change = pd.Series(0.0, index=table.index)
    for team, rows in table.groupby('team'):
        out = rotowire_team(lineups, team)['out']
        players = tuple(sorted(p for p in rows['player_id'].dropna().unique() if p not in out))
        if not out or not players:
            continue
        adj = cached_adjustments(tuple(seasons), tuple(season_types), players, tuple(sorted(out)))
        for i, row in rows.iterrows():
            if row['player_id'] in adj.index and row['bet_type'] in adj.columns:
                change[i] = adj.loc[row['player_id'], row['bet_type']]
    return change


def rotowire_status(player_id, team) -> str:
    """starter / Out 0% / Ques 50% / bench, from RotoWire; empty when RotoWire doesn't list the game."""
    if team not in set(lineups['team']):
        return ''
    listed = lineups[lineups['player_id_ESPN'] == player_id]
    if listed.empty:
        return 'bench'
    p = listed.iloc[0]
    if p['role'] == 'starter':
        return 'starter' + (' ✔' if p['lineup_status'] == 'confirmed' else '')
    return f"{p['injury'] or 'may not play'} {p['play_pct']:.0f}%"


def assess(row) -> pd.Series:
    """Compare one line with the player's game logs (the same idea as betfinder.check_bet, with more numbers)."""
    games = by_player.get(row['player_id_ESPN'], logs.iloc[0:0])
    values = games[row['bet_type']] if len(games) else pd.Series(dtype=float)
    season, last10 = hit_rates(values, row['line']), hit_rates(values.tail(10), row['line'])
    p30, p70 = percentile_band(values) if len(values) else (np.nan, np.nan)
    out = {'player_id': row['player_id_ESPN'], 'team': current_team.get(row['player_id_ESPN']),
           'games': len(values), 'avg': values.mean(), 'avg L5': values.tail(5).mean(),
           'over %': 100 * season['over'], 'under %': 100 * season['under'],
           'over % L10': 100 * last10['over'], 'under % L10': 100 * last10['under'],
           'percentile': line_percentile(values, row['line']), 'p30': p30, 'p70': p70,
           'min L5': games['MIN'].tail(5).mean() if len(games) else np.nan}
    # edge: hit rate minus the probability implied by the odds, for the better side
    edges = {'Over': out['over %'] - 100 / row['over_odds'] if pd.notna(row.get('over_odds')) else np.nan,
             'Under': out['under %'] - 100 / row['under_odds'] if pd.notna(row.get('under_odds')) else np.nan}
    best = max(edges, key=lambda k: -np.inf if pd.isna(edges[k]) else edges[k])
    out['best side'], out['edge pp'] = (best, edges[best]) if pd.notna(edges[best]) else (None, np.nan)
    return pd.Series(out)


if props.empty:
    st.info("Superbet has no NBA player props right now. During preseason it only offers game markets; "
            "props usually appear from the first regular-season games. Use the line checker below meanwhile.")
else:
    table = pd.concat([props.drop(columns='player_id_ESPN'), props.apply(assess, axis=1)], axis=1)
    table['game'] = table['away'].str.upper() + ' @ ' + table['home'].str.upper()
    table['RotoWire'] = [rotowire_status(p, t) for p, t in zip(table['player_id'], table['team'])]
    table['lineup adj'] = lineup_adjustments(table)
    table['adj avg'] = table['avg'] + table['lineup adj']
    table['in band'] = (table['p30'] <= table['line']) & (table['line'] <= table['p70'])

    f = st.columns(5)
    game_filter = f[0].multiselect("Games", sorted(table['game'].unique()))
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
    shown = table[table['games'] >= min_games]
    if game_filter:
        shown = shown[shown['game'].isin(game_filter)]
    if type_filter:
        shown = shown[shown['bet_type'].isin(type_filter)]
    if outside:
        shown = shown[~shown['in band']]
    if hide_out:
        shown = shown[~shown['RotoWire'].str.startswith(('Out', 'OFS'))]
    shown = shown.sort_values('edge pp', ascending=False).reset_index(drop=True)

    st.caption(f"{len(shown)} of {len(table)} lines, best edge first. Hover a column header for what it means. "
               f"The edge is a hint, not a prediction: with few games it swings a lot. Click a row to open the player.")
    st.caption(source_legend())
    # who/what -> the decision -> tonight's lineup -> the player's numbers -> both sides' odds
    columns = ['name', 'game', 'bet_type', 'line',
               'best side', 'signal', 'edge pp', 'pick odds',
               'RotoWire',
               'adj avg', 'avg', 'avg L5', 'percentile', 'in band',
               'over %', 'under %', 'over % L10', 'under % L10', 'games', 'min L5',
               'over_odds', 'under_odds']
    shown = shown.assign(signal=np.select([shown['edge pp'] >= 10, shown['edge pp'] <= -10], ['🟢', '🔴'], ''),
                         **{'pick odds': np.where(shown['best side'] == 'Over', shown['over_odds'],
                                                  np.where(shown['best side'] == 'Under', shown['under_odds'], np.nan))})
    formats = {'avg': '%.1f', 'adj avg': '%.1f', 'avg L5': '%.1f', 'min L5': '%.1f', 'over %': '%.0f',
               'under %': '%.0f', 'over % L10': '%.0f', 'under % L10': '%.0f', 'percentile': '%.0f',
               'over_odds': '%.2f', 'under_odds': '%.2f', 'pick odds': '%.2f', 'edge pp': '%+.1f', 'games': '%d',
               'line': '%g'}
    event = st.dataframe(tinted(shown[columns], formats), hide_index=True, width='stretch', height=600,
                         column_config=column_config(columns, formats), on_select='rerun',
                         selection_mode='single-row')
    if event.selection.rows:
        row = shown.iloc[event.selection.rows[0]]
        if row['player_id'] is not None and pd.notna(row['player_id']):
            st.session_state['player_preset'] = {'player_id': row['player_id'], 'stat': row['bet_type'], 'line': row['line']}
            st.switch_page("views/player.py")
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
