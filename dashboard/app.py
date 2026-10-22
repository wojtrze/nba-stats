"""NBA props dashboard. Run from the repository root:

    streamlit run dashboard/app.py
"""
import os
import sys

DASHBOARD = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DASHBOARD)
# the project's modules live in the repo root, and the data paths are relative to it
sys.path[:0] = [DASHBOARD, ROOT]
os.chdir(ROOT)

import streamlit as st  # noqa: E402

st.set_page_config(page_title="NBA props", page_icon="🏀", layout="wide")

pages = [
    st.Page(os.path.join(DASHBOARD, "views", "todays_props.py"), title="Today's props", icon="🎯", default=True),
    st.Page(os.path.join(DASHBOARD, "views", "games.py"), title="Games", icon="🏟️", url_path="games"),
    st.Page(os.path.join(DASHBOARD, "views", "player.py"), title="Player", icon="👤", url_path="player"),
    st.Page(os.path.join(DASHBOARD, "views", "lineup.py"), title="Lineup lab", icon="🧩", url_path="lineup"),
    st.Page(os.path.join(DASHBOARD, "views", "teams.py"), title="Teams & matchups", icon="🛡️", url_path="teams"),
    st.Page(os.path.join(DASHBOARD, "views", "results.py"), title="Bet slip & results", icon="🧾", url_path="results"),
    st.Page(os.path.join(DASHBOARD, "views", "backtest.py"), title="Rule backtest", icon="📈", url_path="backtest"),
    st.Page(os.path.join(DASHBOARD, "views", "data_status.py"), title="Data status", icon="🗂️", url_path="data"),
]
navigation = st.navigation(pages)
slip = st.session_state.get('slip', [])
if slip:
    st.sidebar.page_link(pages[5], label=f"Bet slip: {len(slip)} bet{'s' * (len(slip) > 1)}", icon="🧾")
navigation.run()
