from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from core.data import game_odds, lineups as rotowire_lineups, priced_games, priced_props, superbet
from core.ui import PAGES, kpis, no_offers, page_header, pl_time, stop, table
from espn_scraper import NBA_TEAM_NAMES
from models import calibration_warning
from schedule import minutes_to, starts_soon
from superbet_fetcher import main_lines
from core.labels import MARKET_LABELS, describe_outcome, winner

seasons, season_types = page_header(
    "Overview", "The games in the next 36 hours, who's missing, and the best-priced bets. Pick a bet to open its "
               "full analysis.", with_scope=True)

odds = game_odds()
if odds.empty:
    no_offers(superbet()['status'])
    stop()

lineups = rotowire_lineups()
props = priced_props(seasons, season_types)
if warning := calibration_warning(props['calibration'].iloc[0] if len(props) else None):
    st.warning(warning, icon="⚠️")
games = priced_games()
by_event = {g['event_id']: g for g in games}
main = pd.DataFrame(main_lines(odds.to_dict('records')))

kpis([{'label': "Games", 'value': odds['event_id'].nunique()},
      {'label': "Player lines", 'value': len(props), 'help': "Superbet's over/under props on these games"},
      {'label': "🟢 Strong props", 'value': int((props['signal'] == '🟢').sum()) if len(props) else 0,
       'help': "Props whose edge reaches the threshold whose picks paid on unseen Superbet lines"},
      {'label': "Lineups listed", 'value': f"{lineups['team'].nunique() if len(lineups) else 0} teams",
       'help': "Teams whose expected or confirmed lineup RotoWire lists"},
      {'label': "Out or doubtful", 'value': int((lineups['role'] == 'may_not_play').sum()) if len(lineups)
       else 0}])

# --- the slate ---
st.subheader("Games")


def lineup_line(team: str) -> str:
    listed = lineups[lineups['team'] == team]
    if listed.empty:
        return f"**{team.upper()}** · :gray[no lineup yet]"
    status = listed['lineup_status'].iloc[0] or 'listed'
    badge = ":green-badge[confirmed]" if status == 'confirmed' else ":orange-badge[expected]"
    out = listed[listed['role'] == 'may_not_play']
    out = ", ".join(f"{r['name']} ({r['injury'] or '?'})" for _, r in out.iterrows())
    return f"**{team.upper()}** {badge}" + (f" · out/doubtful: {out}" if out else "")


# earliest tip-off first
events = odds.drop_duplicates('event_id').sort_values('start_time', key=lambda s: pd.to_datetime(s, utc=True))
now = datetime.now(timezone.utc)
for start in range(0, len(events), 3):
    cols = st.columns(3)
    for col, (_, e) in zip(cols, events.iloc[start:start + 3].iterrows()):
        m = main[main['event_id'] == e['event_id']]
        ml = m[m['market'] == 'ML'].set_index('side')['odds']
        spread = m[(m['market'] == 'SPREAD') & (m['side'] == 'home')]['line']
        total = m[m['market'] == 'TOTAL']['line']
        with col.container(border=True):
            st.markdown(f"#### {e['away'].upper()} @ {e['home'].upper()}")
            if starts_soon(e['start_time'], now):
                st.markdown(f":orange-badge[⏰ tip-off in {max(1, round(minutes_to(e['start_time'], now)))} min]")
            st.caption(f"{pl_time(e['start_time'])} · {NBA_TEAM_NAMES.get(e['away'], '')} at "
                       f"{NBA_TEAM_NAMES.get(e['home'], '')}")
            odds_text = " · ".join(filter(None, [
                f"ML **{ml['away']:.2f}** / **{ml['home']:.2f}**" if {'away', 'home'} <= set(ml.index) else '',
                f"{e['home'].upper()} **{spread.iloc[0]:+g}**" if len(spread) else '',
                f"total **{total.iloc[0]:g}**" if len(total) else '']))
            st.markdown(f"💰 {odds_text or 'no main lines'}",
                        help="Superbet: moneyline odds away / home, the home team's main handicap (− = favourite) "
                             "and the main points total")
            g = by_event.get(e['event_id'])
            if g:
                p = g['projection']
                best = g['edges'].loc[g['edges']['edge pp'].idxmax()]
                st.markdown(f"📊 Projected **{winner(p, g['home'], g['away'])}**, total {p['total']:.0f}  \n"
                            f"Best price: {describe_outcome(best)} @ {best['odds']:.2f} "
                            f"(edge {best['edge pp']:+.1f} pp)")
            st.markdown(lineup_line(e['away']) + "  \n" + lineup_line(e['home']))

# --- the best bets ---
left, right = st.columns([3, 2])
with left:
    st.subheader("Best player lines")
    if props.empty:
        st.caption("Superbet has no player props on these games yet.")
    else:
        top = props[props['signal'].isin(['🟢', '🟡'])].sort_values(['signal', 'edge pp'], ascending=[True, False],
                                                       key=lambda c: c.map({'🟢': 0, '🟡': 1}) if c.name == 'signal'
                                                       else c).head(10).reset_index(drop=True)
        picked = table(top, ['name', 'bet_type', 'line', 'bet', 'signal', 'edge pp', 'pick odds', 'RotoWire'],
                       {'line': '%g', 'edge pp': '%+.1f', 'pick odds': '%.2f'}, key='top_props', select=True)
        st.caption("Only lines with a positive edge (every other line is a pass): 🟢 first, then by edge. "
                   "Pick one to open it on the Props page.")
        if picked is not None:
            r = top.iloc[picked]
            st.session_state['props_focus'] = (r['event_id'], r['name_ESPN'], r['bet_type'])
            st.switch_page(PAGES['props'])
with right:
    st.subheader("Biggest game edges")
    if not games:
        st.caption("No game could be priced.")
    else:
        edges = pd.concat([g['edges'].assign(game=f"{g['away'].upper()} @ {g['home'].upper()}") for g in games])
        top = edges.sort_values('edge pp', ascending=False).head(5).reset_index(drop=True)
        top['bet'] = [describe_outcome(r) for _, r in top.iterrows()]
        picked = table(top, ['game', 'bet', 'odds', 'edge pp'], {'odds': '%.2f', 'edge pp': '%+.1f'},
                       sources={'bet': None, 'odds': 'superbet'}, key='top_games', select=True)
        st.caption(f"Main lines of {', '.join(MARKET_LABELS.values()).lower()}. Estimates for research, not "
                   f"bets: the game model isn't calibrated yet. Pick one to open the game.")
        if picked is not None:
            st.session_state['games_focus'] = top.iloc[picked]['event_id']
            st.switch_page(PAGES['games'])
