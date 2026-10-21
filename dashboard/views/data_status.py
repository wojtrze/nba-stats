import os
import subprocess
import sys

import pandas as pd
import streamlit as st

from loaders import (SUPERBET_COOLDOWN, games, name_resolver, note_superbet_contact, player_logs,
                     reload_superbet_snapshot, rotowire_lineups, season_label, season_status, snapshot_history,
                     superbet_wait, today_props)
from espn_scraper import CURRENT_SEASON, NBA_TEAM_ABBRS
from espn_scraper.storage import snapshot_file
from glossary import column_config

st.title("Data status")

status = season_status()
st.dataframe(status, hide_index=True, width='stretch', column_config=column_config(status.columns))

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
snapshots = pd.DataFrame(rows)
st.dataframe(snapshots, hide_index=True, width='stretch',
             column_config=column_config(snapshots.columns,
                                         tips={'last': "When the newest snapshot was fetched (UTC)"}))
wait = superbet_wait()
if st.button("Take snapshot now", disabled=wait is not None,
             help=f"Superbet was contacted recently; possible again in {wait.seconds // 60 + 1} min" if wait else
             "Runs daily_snapshot.py: appends today's RotoWire lineups and Superbet offers. Superbet blocks frequent "
             f"requests, so this is possible at most once every {SUPERBET_COOLDOWN.seconds // 60} minutes."):
    note_superbet_contact()
    with st.spinner("Fetching RotoWire and Superbet..."):
        result = subprocess.run([sys.executable, "daily_snapshot.py"], capture_output=True, text=True)
    st.code((result.stdout + result.stderr)[-5000:] or "(no output)")
    reload_superbet_snapshot()
    rotowire_lineups.clear()
    snapshot_history.clear()

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
    unmatched = pd.DataFrame(unmatched)
    st.dataframe(unmatched, hide_index=True, width='stretch',
                 column_config=column_config(unmatched.columns, tips={'team': "Team, or the game for Superbet names"}))
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
