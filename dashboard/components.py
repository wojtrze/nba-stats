"""Streamlit pieces shared by several pages."""
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from bets import describe
from reasons import verdict
from schedule import no_offers_text


def night_stored(status: Dict) -> bool:
    """The stored stats already hold every night of the last fetch, so its lines can be settled."""
    from loaders import games
    stored = set(games()['date'].dt.date)
    return bool(status['nights']) and all(night in stored for night in status['nights'])


def no_offers(status: Dict, key: str):
    """In place of the betting tables when the last Superbet fetch has nothing left to bet: what was fetched, that
    new offers are fetched by hand (the Fetch from Superbet button above), and a link to that night's results."""
    with st.container(border=True):
        st.markdown(no_offers_text(status, night_stored(status)))
        if status['state'] == 'all_started' and st.button("See how the last night's lines resolved", key=key,
                                                          icon="📈"):
            st.session_state['results_night'] = status['nights']
            st.switch_page("views/results.py")


def _add_to_slip(bet: Dict):
    slip = st.session_state.setdefault('slip', [])
    if describe(bet) not in {describe(b) for b in slip}:
        slip.append(bet)
        st.toast(f"Added to the slip: {describe(bet)}")


def slip_button(bet: Dict, key: str, where=st):
    """'Add to slip' for one bet (a bets.BET_FIELDS dict without id, time and stake). A callback, so the sidebar's
    slip count is already up to date in the rerun the click starts."""
    where.button("🧾 Add to slip", key=key, on_click=_add_to_slip, args=(bet,),
              help="Collect bets on the Bet slip & results page: it suggests stakes and warns about bets that "
                   "win or lose together")


def reasons_panel(title: str, reasons: List[Dict], edge_pp: float, edge_low: float = np.nan,
                  games: Optional[pd.DataFrame] = None, stat: Optional[str] = None, line: Optional[float] = None):
    """Verdict, then the reasons for and against side by side, then the flags; with games, a chart of the last 10
    games against the line."""
    word, colour, why = verdict(reasons, edge_pp, edge_low)
    with st.container(border=True):
        st.markdown(f"#### {title} · :{colour}[**{word}**]")
        st.caption(why)
        flags = [r for r in reasons if r['flag']]
        pros = [r for r in reasons if r['supports'] is True and not r['flag']]
        cons = [r for r in reasons if r['supports'] is False and not r['flag']]
        context = [r for r in reasons if r['supports'] is None]
        left, right = st.columns(2)
        left.markdown("**For**\n\n" + ("\n".join(f"- ✅ {r['text']}" for r in pros) or "_nothing_"))
        right.markdown("**Against**\n\n" + ("\n".join(f"- ❌ {r['text']}" for r in cons) or "_nothing_"))
        if context:
            st.markdown("\n".join(f"- ➖ {r['text']}" for r in context))
        if flags:
            st.markdown("**Reasons to pass**\n\n" + "\n".join(f"- ⚠️ {r['text']}" for r in flags))
        if games is not None and len(games) and stat:
            last = games.tail(10)
            colours = np.where(last[stat] > line, '#2ca02c', np.where(last[stat] < line, '#d62728', '#9aa5b1'))
            fig = go.Figure(go.Bar(x=last['game_label'], y=last[stat], marker_color=colours,
                                   hovertemplate=f"%{{x}}<br>{stat}: %{{y}}<extra></extra>"))
            fig.add_hline(y=line, line_dash='dash', annotation_text=f"line {line:g}")
            fig.update_layout(height=220, margin=dict(l=10, r=10, t=30, b=10), xaxis=dict(type='category'),
                              title=f"Last {len(last)} games: {stat} (green = over the line)")
            st.plotly_chart(fig, width='stretch')
