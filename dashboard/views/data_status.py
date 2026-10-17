import subprocess
import sys

import streamlit as st

from loaders import games, player_logs, season_label, season_status
from espn_scraper import CURRENT_SEASON, NBA_TEAM_ABBRS

st.title("Data status")

st.dataframe(season_status(), hide_index=True, width='stretch')
st.caption("'checked through' = the last date up to which every game is stored; the next update starts the day after.")

if st.button(f"Update stats for {season_label(CURRENT_SEASON)}", type="primary"):
    with st.spinner("Scraping new games from ESPN..."):
        result = subprocess.run([sys.executable, "-m", "espn_scraper"], capture_output=True, text=True)
    st.code((result.stdout + result.stderr)[-5000:] or "(no output)")
    if result.returncode == 0:
        player_logs.clear()
        games.clear()
        st.success("Done. Reload the page to see the new numbers.")
    else:
        st.error(f"The scraper exited with code {result.returncode}.")

st.subheader("Data quality")
g = games()
p = player_logs()
points = p.groupby(['game_id', 'type'])['PTS'].sum().unstack().add_suffix(' pts (players)')
# the player logs hold NBA teams only, so skip All-Star games and exhibitions against foreign clubs
nba = g[g['home'].isin(NBA_TEAM_ABBRS) & g['away'].isin(NBA_TEAM_ABBRS)].set_index('game_id')
check = nba[['date', 'season_id', 'season_type', 'home', 'away', 'home_score', 'away_score']].join(points)
bad = check[(check['home pts (players)'] != check['home_score']) | (check['away pts (players)'] != check['away_score'])]
if bad.empty:
    st.success("In every game the players' points add up to the team score.")
else:
    st.warning(f"{len(bad)} games where the players' points don't add up to the score. Usually ESPN listed a player "
               f"without an id or name, so the scraper skipped their line.")
    st.dataframe(bad, width='stretch')
