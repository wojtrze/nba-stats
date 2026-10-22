import os
from datetime import date

import pandas as pd
import streamlit as st

from core import freshness, jobs
from core.data import LAST_FETCH, clear_live, game_odds, lineups, props, rotowire, superbet
from core.ui import page_header
from espn_scraper import CURRENT_SEASON, NBA_TEAM_ABBRS, SEASONS
from espn_scraper.storage import snapshot_file
from glossary import column_config
from loaders import (SUPERBET_COOLDOWN, clear_rotowire, fetch_superbet, games, player_logs, season_label,
                     season_status, snapshot_history, superbet_error, superbet_wait)

page_header("Data center", "Fetch fresh stats, odds and lineups, and check that the stored data is complete. "
                           "Every other page reads what's here.")


def queue(job: str, **options):
    """Buttons only queue a job; it runs at the top of the next run, before the cards read the data, so the
    cards already show what it fetched."""
    st.session_state['data_job'] = (job, options)


# --- the usual daily run ---
with st.container(border=True):
    left, right = st.columns([4, 1], vertical_alignment='center')
    left.markdown("**Morning routine** · stores last night's games from ESPN, then saves a snapshot of Superbet's "
                  "lines and RotoWire's lineups (needed for line movement and the Results page). About a minute.")
    right.button("Run both", type='primary', width='stretch', icon="▶️", on_click=queue, args=('routine',))

job = st.session_state.pop('data_job', None)
if job:
    name, options = job
    if name in ('routine', 'snapshot', 'fetch_superbet') and superbet_wait():
        # Superbet blocks frequent requests: every job that contacts it waits out the cooldown
        st.warning(f"Superbet was contacted less than {SUPERBET_COOLDOWN.seconds // 60} minutes ago; try again "
                   f"in {superbet_wait().seconds // 60 + 1} min." + (" Updating the stats only." if name == 'routine'
                                                                    else ""))
        if name == 'routine':
            jobs.update_stats()
    elif name == 'routine':
        if jobs.update_stats() == 0:
            jobs.save_snapshot()
    elif name == 'stats':
        jobs.update_stats(**options)
    elif name == 'snapshot':
        jobs.save_snapshot(**options)
    elif name == 'fetch_superbet':
        with st.spinner("Fetching and saving Superbet's offers..."):
            error = fetch_superbet()
        if error:
            st.error(f"Superbet couldn't be fetched: {error[:200]}. The pages keep using the previous fetch.")
        else:
            st.toast("Fetched and saved Superbet's offers")

superbet()   # records which Superbet data the pages read, for the status line
rw = rotowire()
status = freshness.overview(LAST_FETCH)
last = jobs.last_runs()


def stats_run_caption():
    """The last stats update started from the dashboard (scheduled runs aren't logged)."""
    run = last.get('stats')
    if run:
        ok = "✅" if run['exit_code'] == 0 else "❌"
        when = pd.to_datetime(run['started_at'], utc=True).tz_convert(freshness.PL).strftime('%a %d %b %H:%M')
        st.caption(f"{ok} Last stats update from the dashboard {when}: {run['summary'] or '(no output)'}")


HOW = {'fetch': "Fetch & save / Fetch from Superbet", 'snapshot': "snapshot run"}


def superbet_caption():
    """The last saved fetch: the same data the freshness strip and every page read, so they can't disagree. How
    it was made comes from the run log when it's there (a scheduled snapshot or an older fetch isn't logged); a
    failed attempt after it is shown too."""
    offers = superbet()
    when, s = offers['fetched_at'], offers['status']
    runs = [r for job, r in last.items() if job in HOW]
    if when is None:
        st.caption("No Superbet fetch saved yet.")
    else:
        made = [HOW[r['job']] for r in runs if r['exit_code'] == 0
                and abs((pd.to_datetime(r['started_at'], utc=True) - pd.Timestamp(when)).total_seconds()) < 180]
        st.caption(f"✅ Last saved fetch {pd.Timestamp(when).tz_convert(freshness.PL):%a %d %b %H:%M}: "
                   f"{s['lines']:,} player lines, {s['games']} games" + (f" ({made[0]})" if made else ""))
    failed = [r for r in runs if r['exit_code'] != 0
              and (when is None or pd.to_datetime(r['started_at'], utc=True) > pd.Timestamp(when))]
    for r in failed[:1]:
        st.caption(f"❌ Later attempt {pd.to_datetime(r['started_at'], utc=True).tz_convert(freshness.PL):%a %H:%M} "
                   f"({HOW[r['job']]}) failed: {r['summary']}")


def lineups_caption():
    """The last saved RotoWire version (what a restart would show) and, when the run log has it, what changed."""
    history = snapshot_history('rotowire_lineups')
    if history.empty:
        st.caption("No RotoWire lineups saved yet.")
        return
    newest = history['fetched_at'].max()
    last_saved = history[history['fetched_at'] == newest]
    when = pd.to_datetime(newest, utc=True)
    days = ', '.join(f"{pd.Timestamp(d):%b %d}" for d in sorted(last_saved['game_date'].astype(str).unique()))
    st.caption(f"✅ Last saved lineups {when.tz_convert(freshness.PL):%a %d %b %H:%M}: {len(last_saved)} players "
               f"({days}). Every fetch that changed something is saved.")
    run = last.get('lineups')
    if run is not None and abs((pd.to_datetime(run['started_at'], utc=True) - when).total_seconds()) < 180:
        st.caption(run['summary'].replace('saved ', 'Saved ', 1))


stats_col, odds_col, lineup_col = st.columns(3)

# --- ESPN stats ---
with stats_col.container(border=True):
    s = status['stats']
    st.markdown(f"#### 📊 ESPN stats\n{s['icon']} **{s['label']}** · {s['detail']}")
    seasons = season_status()
    current = seasons[seasons['season'] == season_label(CURRENT_SEASON)].iloc[0]
    m = st.columns(2)
    m[0].metric("Games this season", int(current['games']), border=True)
    m[1].metric("Last game", f"{current['last game']:%b %d}" if current['last game'] else '–', border=True)
    st.button(f"Update {season_label(CURRENT_SEASON)}", type='primary', width='stretch', on_click=queue,
              args=('stats',), help="python -m espn_scraper: adds every finished game that isn't stored yet. "
                                    "Safe to run often.")
    with st.expander("Other seasons, dates or one game"):
        season = st.selectbox("Season", sorted(SEASONS, reverse=True), format_func=season_label)
        how = st.radio("What", ["New games", "A date range", "One game", "Rebuild the season"], horizontal=True,
                       label_visibility='collapsed')
        options = {'season': season}
        if how == "A date range":
            d = st.columns(2)
            options['since'] = d[0].date_input("From", date.fromisoformat(SEASONS[season][0]))
            options['until'] = d[1].date_input("To", min(date.today(), date.fromisoformat(SEASONS[season][1])))
        elif how == "One game":
            options = {'game': st.text_input("ESPN game id", placeholder="401898398",
                                             help="Re-scrapes the game and replaces what's stored for it")}
        elif how == "Rebuild the season":
            options['rebuild'] = st.checkbox(f"Yes, delete {season_label(season)} and scrape it again "
                                             f"(takes long)")
        ready = (how != "One game" or options.get('game')) and (how != "Rebuild the season" or options['rebuild'])
        st.button("Run", disabled=not ready, width='stretch', on_click=queue, args=('stats',), kwargs=options)
    stats_run_caption()

# --- Superbet ---
with odds_col.container(border=True):
    s = status['superbet']
    st.markdown(f"#### 💰 Superbet odds\n{s['icon']} **{s['label']}** · {s['detail']}")
    m = st.columns(2)
    m[0].metric("Player lines", len(props()), border=True,
                help="Over/under player props in the next 36 hours (none in preseason)")
    m[1].metric("Games", game_odds()['event_id'].nunique() if len(game_odds()) else 0, border=True,
                help="Games with moneyline / handicap / total markets in the next 36 hours")
    st.caption("Superbet blocks frequent requests, so it's only contacted when you press a button here (at most "
               f"once per {SUPERBET_COOLDOWN.seconds // 60} minutes). Every fetch is saved; the pages use the newest "
               "one until its games tip off.")
    if superbet()['status']['state'] == 'all_started':
        st.info("Every game of the last fetch has tipped off: fetch again for new offers.")
    if superbet_error():
        st.warning(f"The last fetch failed: {superbet_error()[:150]}")
    wait = superbet_wait()
    b = st.columns(2)
    b[0].button("Fetch & save", key='fetch_superbet', type='primary', width='stretch', disabled=wait is not None,
                on_click=queue, args=('fetch_superbet',),
                help=f"Possible again in {wait.seconds // 60 + 1} min" if wait else
                "Fetch Superbet's offers and save them with the dashboard's pick for every line (kept after a "
                "restart; used for line movement and the Results page)")
    b[1].button("Snapshot with lineups", key='snap_superbet', width='stretch', disabled=wait is not None,
                on_click=queue, args=('snapshot',),
                help=f"Possible again in {wait.seconds // 60 + 1} min" if wait else
                "python daily_snapshot.py: the same as Fetch & save, plus RotoWire's lineups saved with it")
    superbet_caption()

# --- RotoWire ---
with lineup_col.container(border=True):
    s = status['rotowire']
    st.markdown(f"#### 📋 RotoWire lineups\n{s['icon']} **{s['label']}** · {s['detail']}")
    listed = lineups()
    confirmed = listed.drop_duplicates('team')['lineup_status'].eq('confirmed').sum() if len(listed) else 0
    m = st.columns(2)
    m[0].metric("Teams listed", listed['team'].nunique() if len(listed) else 0, f"{confirmed} confirmed",
                delta_color='off', delta_arrow='off', border=True, help="Teams on RotoWire's lineups page today")
    m[1].metric("May not play", int((listed['role'] == 'may_not_play').sum()) if len(listed) else 0, border=True,
                help="Players listed as out, doubtful or questionable")
    if rw['error']:
        st.warning(f"RotoWire couldn't be read, showing the last snapshot. {rw['error'][:150]}")
    b = st.columns(2)
    if b[0].button("Fetch live", key='fetch_rotowire', width='stretch',
                   help="Read RotoWire's lineups page again; saved when something changed"):
        clear_rotowire()
        st.rerun()
    b[1].button("Snapshot for tomorrow", key='snap_tomorrow', width='stretch', on_click=queue, args=('snapshot',),
                disabled=superbet_wait() is not None,
                kwargs={'tomorrow': True},
                help="python daily_snapshot.py --tomorrow: RotoWire's lineups for tomorrow's games")
    lineups_caption()

st.caption("RotoWire's lineups are kept for 30 minutes, then fetched again when a page needs them, and saved "
           "whenever they changed. To run the morning routine automatically, see the scheduled tasks in the README.")
if st.button("Reload snapshots and lineups", help="Re-read the saved snapshots and fetch RotoWire again (doesn't "
                                                   "contact Superbet)"):
    clear_live()
    st.rerun()

# --- what's stored, runs, checks ---
stored_tab, runs_tab, names_tab, quality_tab = st.tabs(["Stored data", "Recent runs", "Name matching", "Data quality"])

with stored_tab:
    st.dataframe(seasons, hide_index=True, width='stretch', column_config=column_config(seasons.columns))
    rows = []
    for name in ['superbet_props', 'superbet_game_odds', 'rotowire_lineups']:
        path = snapshot_file(CURRENT_SEASON, name)
        fetched = pd.read_csv(path, usecols=['fetched_at'])['fetched_at'] if os.path.exists(path) else pd.Series()
        rows.append({'file': path, 'rows': len(fetched), 'snapshots': fetched.nunique(),
                     'first': fetched.min() if len(fetched) else None, 'last': fetched.max() if len(fetched) else None})
    snapshots = pd.DataFrame(rows)
    st.dataframe(snapshots, hide_index=True, width='stretch',
                 column_config=column_config(snapshots.columns, tips={
                     'snapshots': "Separate fetches saved", 'first': "Oldest snapshot (UTC)",
                     'last': "Newest snapshot (UTC)"}))

with runs_tab:
    runs = jobs.recent_runs()
    if runs.empty:
        st.caption(f"No runs from the dashboard yet. They're logged to {jobs.RUN_LOG}.")
    else:
        st.dataframe(runs, hide_index=True, width='stretch',
                     column_config={'exit_code': st.column_config.NumberColumn("exit", help="0 = success"),
                                    'seconds': st.column_config.NumberColumn("seconds", format='%.0f'),
                                    'started_at': st.column_config.Column("started (UTC)")})

with names_tab:
    unmatched = []
    for _, r in listed[listed['player_id_ESPN'].isna()].iterrows():
        unmatched.append({'source': 'RotoWire', 'name': r['name'], 'team': r['team'],
                          'note': r['injury'] or r['role']})
    if not props().empty:
        for _, r in props()[props()['player_id_ESPN'].isna()].drop_duplicates('name').iterrows():
            unmatched.append({'source': 'Superbet', 'name': r['name'], 'team': f"{r['away']} @ {r['home']}",
                              'note': ''})
    if unmatched:
        st.warning(f"{len(unmatched)} names from today's sources don't match a player in the game logs. Players "
                   f"without a game yet (rookies, long injuries) are expected; for others add an entry to "
                   f"OVERRIDES in name_resolver.py.")
        st.dataframe(pd.DataFrame(unmatched), hide_index=True, width='stretch')
    else:
        st.success("Every RotoWire and Superbet name matches a player in the game logs.")

with quality_tab:
    g, p = games(), player_logs()
    points = p.groupby(['game_id', 'type'])['PTS'].sum().unstack().add_suffix(' pts (players)')
    # the player logs hold NBA teams only, so skip All-Star games and exhibitions against foreign clubs
    nba = g[g['home'].isin(NBA_TEAM_ABBRS) & g['away'].isin(NBA_TEAM_ABBRS)].set_index('game_id')
    check = nba[['date', 'season_id', 'season_type', 'home', 'away', 'home_score', 'away_score']].join(points)
    bad = check[(check['home pts (players)'] != check['home_score'])
                | (check['away pts (players)'] != check['away_score'])]
    if bad.empty:
        st.success("In every stored game the players' points add up to the team score.")
    else:
        st.warning(f"{len(bad)} games where the players' points don't add up to the score. Usually ESPN listed a "
                   f"player without an id or name and the play-by-play didn't have them either.")
        st.dataframe(bad, width='stretch')
