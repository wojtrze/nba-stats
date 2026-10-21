"""NBA props dashboard, version 2: the same data and models as dashboard/, organised by task. Run from the
repository root (the old dashboard can run next to it on the default port):

    streamlit run dashboard_v2/app.py --server.port 8502
"""
import os
import sys

V2 = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(V2)
# v2's own package (core), the old dashboard's logic modules (metrics, models, ...) and the project's modules;
# the data paths are relative to the repository root
sys.path[:0] = [V2, os.path.join(ROOT, 'dashboard'), ROOT]
os.chdir(ROOT)

import streamlit as st  # noqa: E402

from core.ui import PAGES, sidebar_status  # noqa: E402

st.set_page_config(page_title="NBA props v2", page_icon="🏀", layout="wide")


def page(file, title, icon, key, default=False):
    PAGES[key] = st.Page(os.path.join(V2, "views", file), title=title, icon=icon, url_path=None if default else key,
                         default=default)
    return PAGES[key]


navigation = st.navigation({
    "Tonight": [page("overview.py", "Overview", "🏠", 'overview', default=True),
                page("props.py", "Props", "🎯", 'props'),
                page("games.py", "Games", "🏟️", 'games')],
    "Research": [page("player_history.py", "Player history", "👤", 'player'),
                 page("team_history.py", "Team history", "🛡️", 'team'),
                 page("lineup_lab.py", "Lineup lab", "🧩", 'lineup')],
    "Review": [page("results.py", "Results", "📈", 'results')],
    "Data": [page("data_center.py", "Data center", "🔄", 'data')],
})
navigation.run()
# drawn after the page, so it already knows what the page fetched (pages that stop early use core.ui.stop)
sidebar_status()
