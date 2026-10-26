import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from bets import (as_snapshot_rows, bets_file, describe, kelly_stake, load_bets, save_bets, slip_warnings,
                  staking_chance)
from glossary import column_config, tinted
from loaders import games, player_logs, snapshot_history
import night_view
from models import FITTED, calibration_status, calibration_warning, load_green_edge
from tracking import calibration, edge_bucket, results_table, settle_games, settle_props, threshold_table

st.title("Bet slip & results")
st.caption("Collect bets from Today's props and Games, size them, and see how both your bets and the dashboard's "
           "own picks turned out. Results need the game in the stored stats: run the scraper (Data status page) "
           "the morning after.")

RESULT_FORMATS = {'bets': '%d', 'expected %': '%.0f', 'hit %': '%.0f', 'ci low %': '%.0f', 'ci high %': '%.0f',
                  'ROI %': '%+.1f', 'avg odds': '%.2f', 'avg CLV %': '%+.1f', 'edge ≥ pp': '%d'}
RESULT_TIPS = {'bets': "Won and lost bets (pushes and voids left out)",
               'expected %': "How often the model expected these picks to win (its average chance). An accurate "
                             "signal's hit % lands close to it",
               'edge ≥ pp': "Every pick whose saved edge reached this many points (0 = any positive edge), so the rows "
                            "overlap",
               'avg CLV %': "Average closing line value: your odds vs the last snapshot before tip-off for the same "
                            "line, in %. Beating the close consistently is the best early sign of real edge."}


@st.cache_data(ttl=600, show_spinner="Settling the snapshots...")
def settled_props() -> pd.DataFrame:
    return settle_props(snapshot_history('superbet_props'), player_logs(), games())


@st.cache_data(ttl=600, show_spinner=False)
def settled_games() -> pd.DataFrame:
    return settle_games(snapshot_history('superbet_game_odds'), games())


def results_tables(settled: pd.DataFrame, groups: dict):
    """One results_table per grouping, side by side in pairs."""
    items = list(groups.items())
    for i in range(0, len(items), 2):
        cols = st.columns(2)
        for col, (title, by) in zip(cols, items[i:i + 2]):
            table = results_table(settled, by)
            col.markdown(f"**{title}**")
            if table.empty:
                col.caption("Nothing settled yet.")
                continue
            col.dataframe(tinted(table, RESULT_FORMATS), hide_index=True, width='stretch',
                          column_config=column_config(table.columns, RESULT_FORMATS, tips=RESULT_TIPS))


def calibration_chart(settled: pd.DataFrame, title: str):
    cal = calibration(settled)
    if cal.empty:
        return
    fig = go.Figure()
    fig.add_scatter(x=[0, 100], y=[0, 100], mode='lines', line=dict(dash='dot', color='grey'), name='calibrated')
    fig.add_scatter(x=cal['model %'], y=cal['actual %'], mode='markers+text', text=cal['bets'],
                    textposition='top center', marker=dict(size=10), name='bets',
                    hovertemplate="model %{x:.0f}% → won %{y:.0f}%<br>%{text} bets<extra></extra>")
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=30, b=10), title=title,
                      xaxis=dict(title="Model's chance (%)", range=[0, 100]),
                      yaxis=dict(title="Actually won (%)", range=[0, 100]))
    st.plotly_chart(fig, width='stretch')
    st.caption("Each dot: the bets whose model chance fell in one 10-point bin, labelled with how many. Dots below "
               "the dotted line = the model is too optimistic there.")


def kpis(settled: pd.DataFrame, stake_col=None):
    decided = settled[settled['result'].isin(['win', 'loss'])]
    stake = settled[stake_col] if stake_col else pd.Series(1.0, index=settled.index)
    profit = (settled['profit'] * stake).sum()
    staked = stake[settled['result'].isin(['win', 'loss', 'push'])].sum()
    m = st.columns(5)
    m[0].metric("Settled", f"{len(decided)}", f"{(settled['status'] == 'pending').sum()} pending", delta_color='off',
                help="Won or lost; pending = the game isn't in the stored stats yet")
    m[1].metric("Hit rate", f"{100 * (decided['result'] == 'win').mean():.0f}%" if len(decided) else "–")
    m[2].metric("Profit" if stake_col else "Profit (1 unit each)", f"{profit:+.2f}")
    m[3].metric("ROI", f"{100 * profit / staked:+.1f}%" if staked else "–", help="Profit per 100 staked")
    m[4].metric("Avg CLV", f"{decided['clv odds %'].mean():+.1f}%" if decided['clv odds %'].notna().any() else "–",
                help=RESULT_TIPS['avg CLV %'])


NIGHT_TAB = "🌙 Previous night"
# "See how the last night's lines resolved" on Today's props / Games opens that night's tab
night = st.session_state.pop('results_night', None)
if night:
    st.session_state['results_tab'] = NIGHT_TAB
    st.session_state['night_pick'] = str(night[-1])
slip_tab, mine_tab, model_tab, night_tab = st.tabs(["🧾 Slip", "📒 My bets", "📈 Dashboard's picks", NIGHT_TAB],
                                                    default=st.session_state.get('results_tab'))

# --- the slip ---
with slip_tab:
    slip = st.session_state.get('slip', [])
    c = st.columns([1, 1, 2])
    st.session_state.setdefault('bankroll', 1000.0)
    bankroll = c[0].number_input("Bankroll", 0.0, 1e7, key='bankroll', step=50.0,
                                 help="What you're prepared to bet over the season; stakes are a share of it")
    fraction = c[1].selectbox("Staking", [0.25, 0.5, 0.1], format_func=lambda f: f"{f:g} Kelly",
                              help="Kelly = the stake that grows the bankroll fastest if the model's chances are "
                                   "right. They're not that reliable, so a quarter is the default; every stake is "
                                   "capped at 5% of the bankroll.")
    calibrated = calibration_status() == FITTED
    if not calibrated and any(b.get('edge_low') is not None and pd.notna(b.get('edge_low')) for b in slip):
        st.warning(calibration_warning() + " Props on the slip get no suggested stake.", icon="⚠️")
    if not slip:
        st.info("The slip is empty. Open a prop on Today's props or a game on Games and press 🧾 Add to slip.")
    else:
        rows = pd.DataFrame([{'bet': describe(b), 'odds': b['odds'], 'model %': b['model_pct'],
                              'edge pp': b['edge_pp'],
                              'suggested': kelly_stake(staking_chance(b, calibrated), b['odds'], bankroll, fraction),
                              'stake': b.get('stake') if b.get('stake') is not None else
                              kelly_stake(staking_chance(b, calibrated), b['odds'], bankroll, fraction),
                              'remove': False} for b in slip])
        edited = st.data_editor(
            rows, hide_index=True, width='stretch', key='slip_editor',
            disabled=['bet', 'odds', 'model %', 'edge pp', 'suggested'],
            column_config={'bet': st.column_config.Column("bet"),
                           'odds': st.column_config.NumberColumn("💰 odds", format='%.2f'),
                           'model %': st.column_config.NumberColumn("📊 model %", format='%.0f'),
                           'edge pp': st.column_config.NumberColumn("📊 edge pp", format='%+.1f'),
                           'suggested': st.column_config.NumberColumn(
                               "suggested stake", format='%.2f',
                               help="Kelly stake at the chosen fraction. Props are sized on the low end of the "
                                    "model's range, so 0 = the edge isn't sure enough; games on the model's "
                                    "chance"),
                           'stake': st.column_config.NumberColumn("stake", min_value=0.0, step=1.0, format='%.2f',
                                                                  help="What you actually bet; edit it"),
                           'remove': st.column_config.CheckboxColumn("remove")})
        for bet, stake in zip(slip, edited['stake']):
            bet['stake'] = float(stake or 0)
        keep = [b for b, gone in zip(slip, edited['remove']) if not gone]
        if len(keep) < len(slip):
            st.session_state['slip'] = keep
            st.rerun()
        total = sum(b['stake'] for b in slip)
        st.caption(f"Total stake {total:.2f} ({100 * total / bankroll:.1f}% of the bankroll)" if bankroll else "")
        for warning in slip_warnings(slip, bankroll):
            st.warning(warning, icon="⚠️")
        b = st.columns([1, 1, 3])
        if b[0].button("✅ Save as placed", type='primary',
                       help=f"Adds the bets with a stake above 0 to {bets_file()}, then empties the slip"):
            placed = [bt for bt in slip if bt['stake'] > 0]
            n = save_bets(placed)
            st.session_state['slip'] = []
            st.toast(f"Saved {n} bet{'s' * (n != 1)}")
            st.rerun()
        if b[1].button("Empty the slip"):
            st.session_state['slip'] = []
            st.rerun()

# --- my bets ---
with mine_tab:
    mine = load_bets()
    if mine.empty:
        st.info(f"No saved bets yet. Bets saved from the slip go to {bets_file()}.")
    else:
        rows = as_snapshot_rows(mine)
        labels = {r['bet_id']: describe(r) for r in mine.to_dict('records')}
        parts = []
        if len(rows['prop']):
            parts.append(settle_props(snapshot_history('superbet_props'), player_logs(), games(), bets=rows['prop']))
        if len(rows['game']):
            parts.append(settle_games(snapshot_history('superbet_game_odds'), games(), bets=rows['game']))
        settled = pd.concat(parts, ignore_index=True).sort_values('placed_at', ascending=False)
        settled['bet'] = settled['bet_id'].map(labels)
        settled['P&L'] = settled['profit'] * settled['stake']
        kpis(settled, stake_col='stake')
        cols = ['game_date', 'bet', 'odds', 'stake', 'model_pct', 'edge_pp', 'status', 'result', 'P&L', 'clv odds %']
        formats = {'odds': '%.2f', 'stake': '%.2f', 'model_pct': '%.0f', 'edge_pp': '%+.1f', 'P&L': '%+.2f',
                   'clv odds %': '%+.1f'}
        st.dataframe(tinted(settled[cols], formats), hide_index=True, width='stretch',
                     column_config=column_config(cols, formats, tips={
                         'model_pct': "Model's chance when you added the bet", 'edge_pp': "Edge when you added it",
                         'P&L': "Profit or loss at your stake", 'clv odds %': RESULT_TIPS['avg CLV %'],
                         'status': "settled, pending (game not in the stored stats yet) or void (didn't play)",
                         'game_date': "Game date (US Eastern)"})
                     | {'game_date': st.column_config.DateColumn("date", format='YYYY-MM-DD')})

# --- the dashboard's own picks ---
with model_tab:
    st.caption("Every line daily_snapshot.py saved, as first offered before tip-off, with the pick and edge the "
               "dashboard showed at that moment, settled against the stored stats: is the model any good? Snapshots "
               "from before picks were saved have results but no pick, so they don't count here.")
    props_settled = settled_props()
    picks = props_settled[props_settled['pick'].notna()]
    st.subheader("Props")
    if picks.empty:
        st.info("No settled picks yet: take snapshots (Data status page or `python daily_snapshot.py`) before the "
                "games and update the stats after them.")
    else:
        kpis(picks)
        picks = picks.assign(**{'edge bucket': edge_bucket(picks['edge_pp']),
                                'signal': picks['signal'].replace('', 'none')})
        st.markdown("**Signal efficiency**")
        efficiency = threshold_table(picks)
        if efficiency.empty:
            st.caption("No settled pick has had a positive edge yet.")
        else:
            st.dataframe(tinted(efficiency, RESULT_FORMATS), hide_index=True, width='stretch',
                         column_config=column_config(efficiency.columns, RESULT_FORMATS, tips=RESULT_TIPS))
        green = load_green_edge()
        st.caption((f"🟢 = an edge of +{green:g} pp or more" if green is not None else "No 🟢 at the moment")
                   + ": the threshold is the smallest whose picks paid on unseen Superbet lines (refitted as nights "
                     "settle; see the calibration report). 🟡 = any other positive edge. Lines without one are a "
                     "pass; their pick below is only the less bad side.")
        results_tables(picks, {"By signal (🟢 = the validated edge threshold)": 'signal',
                               "By edge (pp)": 'edge bucket', "By bet type": 'bet_type', "By side": 'pick'})
        calibration_chart(picks, "Props: model chance vs actual")
    st.subheader("Games")
    games_settled = settled_games()
    games_settled = games_settled[games_settled['model_pct'].notna()]
    main_only = st.toggle("Main lines only", value=True,
                          help="Superbet offers many alternative handicaps and totals; they win and lose together, "
                               "so counting all of them overstates how much evidence there is")
    if main_only:
        games_settled = games_settled[games_settled['main']]
    if games_settled.empty:
        st.info("No settled game picks yet.")
    else:
        kpis(games_settled)
        games_settled = games_settled.assign(**{'edge bucket': edge_bucket(games_settled['edge_pp'])})
        results_tables(games_settled, {"By edge (pp)": 'edge bucket', "By market": 'market'})
        calibration_chart(games_settled, "Games: model chance vs actual")

# --- the previous night: every line and game against our last projection before tip-off ---
with night_tab:
    night_view.render(update_stats=lambda: st.page_link("views/data_status.py", label="Update the stats on Data status",
                                                         icon="🗂️"), key='night')
