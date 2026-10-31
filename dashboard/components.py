"""Streamlit pieces shared by several pages."""
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from bets import describe
from i18n import t
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


# how each decision status is shown (decisions.py); the words are i18n's 'decision.<status>'
STATUS_COLOURS = {'OBSTAW': 'green', 'NIE_OBSTAWIAJ': 'gray', 'CZEKAJ': 'orange', 'NIEDOSTEPNE': 'gray'}


def local_time(when) -> str:
    """A time in Polish local time ('30.10 22:23'), or the date alone for a date without a time ('29.10')."""
    if when is None or pd.isna(when):
        return ''
    ts = pd.Timestamp(when)
    if ts.tzinfo is None and ts == ts.normalize():
        return ts.strftime('%d.%m')
    ts = ts.tz_localize('UTC') if ts.tzinfo is None else ts
    return ts.tz_convert('Europe/Warsaw').strftime('%d.%m %H:%M')


def decision_text(decision: Dict, lang: str = 'en') -> str:
    """'**Don't bet** · why' for a decision (decisions.py), coloured by its status."""
    word = t(f"decision.{decision['status']}", lang)
    why = t(decision['reason'], lang, **decision.get('values', {}))
    return f":{STATUS_COLOURS[decision['status']]}[**{word}**] · {why}"


def decision_times(decision: Dict, lang: str = 'en') -> str:
    """When the odds and the lineup the decision rests on were fetched."""
    odds = t('decision.odds_at', lang, time=local_time(decision.get('odds_at'))) if decision.get('odds_at') else ''
    lineup = t('decision.lineup_at', lang, time=local_time(decision['lineup_at'])) if decision.get('lineup_at') \
        else t('decision.lineup_unknown', lang)
    return " · ".join(filter(None, [odds, lineup]))


def change_notice(changed: Optional[Dict], lang: str = 'en'):
    """Says out loud that an open offer's line or odds changed since its decision was shown (decisions.offer_changed),
    so a new decision never silently replaces the old one."""
    if not changed or not changed['changed']:
        return
    for what in ('line', 'odds'):
        if changed[what]:
            was, now = changed[what]
            st.warning(t('decision.changed', lang, what=t(f'decision.what.{what}', lang), was=f"{was:g}",
                         now=f"{now:g}"), icon="🔄")


def _meta(r: Dict, lang: str) -> str:
    return t('panel.meta', lang, n=r['n'], source=r['source'], as_of=local_time(r['as_of']))


def reasons_panel(title: str, decision: Dict, reasons: List[Dict], games: Optional[pd.DataFrame] = None,
                  stat: Optional[str] = None, line: Optional[float] = None, lang: str = 'en',
                  changed: Optional[Dict] = None):
    """The decision (decisions.py) with when its odds and lineup were fetched, then why: the reasons for and
    against side by side with their numbers, observations, source and time, the context and the warnings; with
    games, a chart of the last 10 games against the line. The reasons explain the decision and don't change it.
    Worded in `lang` (the reasons come worded already)."""
    with st.container(border=True):
        st.markdown(f"#### {title}")
        st.markdown(decision_text(decision, lang))
        st.caption(decision_times(decision, lang))
        change_notice(changed, lang)
        flags = [r for r in reasons if r['flag']]
        pros = [r for r in reasons if r['supports'] is True and not r['flag']]
        cons = [r for r in reasons if r['supports'] is False and not r['flag']]
        context = [r for r in reasons if r['supports'] is None]
        st.markdown(f"**{t('panel.why', lang)}** · _{t('panel.why_note', lang)}_")
        left, right = st.columns(2)
        nothing = f"_{t('panel.nothing', lang)}_"
        item = lambda icon, r: f"- {icon} {r['text']}  \n  :gray[{_meta(r, lang)}]"
        left.markdown(f"**{t('panel.for', lang)}**\n\n" + ("\n".join(item('✅', r) for r in pros) or nothing))
        right.markdown(f"**{t('panel.against', lang)}**\n\n" + ("\n".join(item('❌', r) for r in cons) or nothing))
        if context:
            st.markdown(f"**{t('panel.context', lang)}**\n\n" + "\n".join(item('➖', r) for r in context))
        if flags:
            st.markdown(f"**{t('panel.flags', lang)}**\n\n" + "\n".join(f"- ⚠️ {r['text']}" for r in flags))
        if games is not None and len(games) and stat:
            last = games.tail(10)
            colours = np.where(last[stat] > line, '#2ca02c', np.where(last[stat] < line, '#d62728', '#9aa5b1'))
            fig = go.Figure(go.Bar(x=last['game_label'], y=last[stat], marker_color=colours,
                                   hovertemplate=f"%{{x}}<br>{stat}: %{{y}}<extra></extra>"))
            fig.add_hline(y=line, line_dash='dash', annotation_text=t('panel.line', lang, line=line))
            fig.update_layout(height=220, margin=dict(l=10, r=10, t=30, b=10), xaxis=dict(type='category'),
                              title=t('panel.chart', lang, n=len(last), stat=stat))
            st.plotly_chart(fig, width='stretch')
