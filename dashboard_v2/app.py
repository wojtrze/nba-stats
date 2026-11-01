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

from core import fetch_worker  # noqa: E402
from core.state import language, language_picker, no_tax_switch  # noqa: E402
from core.ui import PAGES, sidebar_status  # noqa: E402
from i18n import t  # noqa: E402

st.set_page_config(page_title="NBA props v2", page_icon="🏀", layout="wide")
lang = language()
fetch_worker.follow_settings()   # the scheduled fetches run while this dashboard does (switch in the Data center)


def page(file, key, icon, default=False, title=None):
    """A page under PAGES[key] (its URL too), titled with i18n's 'nav.<title or key>'."""
    PAGES[key] = st.Page(os.path.join(V2, "views", file), title=t(f'nav.{title or key}', lang), icon=icon,
                         url_path=None if default else key, default=default)
    return PAGES[key]


navigation = st.navigation({
    t('nav.tonight', lang): [page("overview.py", 'overview', "🏠", default=True),
                             page("props.py", 'props', "🎯"),
                             page("games.py", 'games', "🏟️"),
                             page("help.py", 'help', "❓")],
    t('nav.research', lang): [page("player_history.py", 'player', "👤"),
                              page("team_history.py", 'team', "🛡️"),
                              page("lineup_lab.py", 'lineup', "🧩")],
    t('nav.review', lang): [page("results.py", 'results', "📈"),
                            page("backtest.py", 'backtest', "🧪")],
    t('nav.data', lang): [page("data_center.py", 'data', "🔄", title='data_center')],
})
with st.sidebar:
    language_picker()
    no_tax_switch()
navigation.run()
# drawn after the page, so it already knows what the page fetched (pages that stop early use core.ui.stop)
sidebar_status()
