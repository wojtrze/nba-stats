"""The building blocks every v2 page is made of, so the pages look and read the same way:
header (title, purpose, scope) -> filters -> KPIs -> one main table -> details of the selected row."""
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Sequence

import pandas as pd
import streamlit as st

from core import freshness
from core.data import LAST_FETCH
from core.state import scope, scope_label, scope_picker
from glossary import column_config, source_legend, tinted

# the app's pages by key, filled by app.py on every run, so pages can link to each other
PAGES: Dict = {}

SOURCE_NAMES = {'stats': "📊 ESPN stats", 'superbet': "💰 Superbet odds", 'rotowire': "📋 RotoWire lineups"}


def page_header(title: str, purpose: str, with_scope: bool = False):
    """Title and one line on what the page answers; with_scope adds the Scope popover (seasons, game types)."""
    left, right = st.columns([5, 2], vertical_alignment='bottom')
    left.title(title)
    left.caption(purpose)
    if with_scope:
        with right.popover(f"Scope: {scope_label()}", width='stretch',
                           help="Which seasons and game types the numbers on every page use"):
            scope_picker()
    return scope()


def sidebar_status():
    """The freshness strip under the navigation, on every page."""
    status = freshness.overview(LAST_FETCH)
    with st.sidebar:
        st.markdown("**Data freshness**")
        for key, s in status.items():
            st.markdown(f"{s['icon']} {SOURCE_NAMES[key]}  \n:gray[{s['label']}]", help=s['detail'])
        if any(s['level'] != 'ok' for s in status.values()) and 'data' in PAGES:
            st.page_link(PAGES['data'], label="Update in the Data center", icon="🔄")


def stop():
    """st.stop() for pages: draws the freshness strip first, which app.py would otherwise draw after the page."""
    sidebar_status()
    st.stop()


def go_to_data(message: str):
    """An empty state that says what to do, with a button to the Data center."""
    with st.container(border=True):
        st.markdown(message)
        if 'data' in PAGES:
            st.page_link(PAGES['data'], label="Open the Data center", icon="🔄")


def kpis(items: Sequence[Dict]):
    """One row of bordered metrics: dicts with label, value and optional help / delta / delta_color. A delta
    with delta_color 'off' is a note ("of 2170"), not a change, so it gets no arrow."""
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        colour = item.get('delta_color', 'normal')
        col.metric(item['label'], item['value'], item.get('delta'), delta_color=colour,
                   delta_arrow='off' if colour == 'off' else 'auto', help=item.get('help'), border=True)


def table(df: pd.DataFrame, columns: List[str], formats: Optional[Dict[str, str]] = None,
          tips: Optional[Dict[str, str]] = None, sources: Optional[Dict[str, Optional[str]]] = None,
          key: Optional[str] = None, select: bool = False, height='auto', legend: Iterable[str] = ()):
    """A dataframe with the old dashboard's source marks (icon + tint) and tooltips. select: single-row selection;
    returns the selected row's position in df, or None."""
    formats = {c: f for c, f in (formats or {}).items() if c in columns}
    if legend:
        st.caption(source_legend(list(legend)))
    kwargs = dict(on_select='rerun', selection_mode='single-row', key=key) if select else {}
    event = st.dataframe(tinted(df[columns], formats, sources), hide_index=True, width='stretch', height=height,
                         column_config=column_config(columns, formats, tips=tips, sources=sources), **kwargs)
    if select and event.selection.rows:
        return event.selection.rows[0]
    return None


def verdict_text(word: str, colour: str) -> str:
    return f":{colour}-badge[{word}]"


def pl_time(start_time) -> str:
    """'Wed 01:00': a tip-off time in Polish time."""
    return pd.to_datetime(start_time).tz_convert(freshness.PL).strftime('%a %H:%M')


def now_pl() -> datetime:
    return datetime.now(freshness.PL)
