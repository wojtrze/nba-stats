import os
import subprocess
import sys

import pandas as pd
import streamlit as st

from loaders import (games, name_resolver, player_logs, rotowire_lineups, season_label, season_status,
                     superbet_offers, today_props)
from espn_scraper import CURRENT_SEASON, NBA_TEAM_ABBRS
from espn_scraper.storage import snapshot_file

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
        name_resolver.clear()
        st.success("Done. Reload the page to see the new numbers.")
    else:
        st.error(f"The scraper exited with code {result.returncode}.")

st.subheader("RotoWire & Superbet snapshots")
rows = []
for name in ['rotowire_lineups', 'superbet_props', 'superbet_game_odds']:
    path = snapshot_file(CURRENT_SEASON, name)
    if os.path.exists(path):
        fetched = pd.read_csv(path, usecols=['fetched_at'])['fetched_at']
        rows.append({'file': path, 'rows': len(fetched), 'snapshots': fetched.nunique(), 'last': fetched.max()})
    else:
        rows.append({'file': path, 'rows': 0, 'snapshots': 0, 'last': None})
st.dataframe(pd.DataFrame(rows), hide_index=True, width='stretch')
if st.button("Take snapshot now", help="Runs daily_snapshot.py: appends today's RotoWire lineups and Superbet offers"):
    with st.spinner("Fetching RotoWire and Superbet..."):
        result = subprocess.run([sys.executable, "daily_snapshot.py"], capture_output=True, text=True)
    st.code((result.stdout + result.stderr)[-5000:] or "(no output)")
    superbet_offers.clear()
    rotowire_lineups.clear()

unmatched = []
lineups = rotowire_lineups()
for _, r in lineups[lineups['player_id_ESPN'].isna()].iterrows():
    unmatched.append({'source': 'RotoWire', 'name': r['name'], 'team': r['team'], 'note': r['injury'] or r['role']})
props = today_props()
if not props.empty:
    for _, r in props[props['player_id_ESPN'].isna()].drop_duplicates('name').iterrows():
        unmatched.append({'source': 'Superbet', 'name': r['name'], 'team': f"{r['away']} @ {r['home']}", 'note': ''})
if unmatched:
    st.warning(f"{len(unmatched)} names from today's sources don't match a player in the game logs. Players without "
               f"a game yet (rookies, long injuries) are expected here; for others add an entry to OVERRIDES in "
               f"name_resolver.py.")
    st.dataframe(pd.DataFrame(unmatched), hide_index=True, width='stretch')
else:
    st.success("Every RotoWire and Superbet name matches a player in the game logs.")

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
               f"without an id or name and the play-by-play didn't have them either, so their line was skipped.")
    st.dataframe(bad, width='stretch')
