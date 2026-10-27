import os
from datetime import date

import pandas as pd
import streamlit as st

from core import freshness, jobs
from core.data import LAST_FETCH, clear_live, game_odds, lineups, props, rotowire, superbet
from core.state import language
from core.ui import page_header
from espn_scraper import CURRENT_SEASON, SEASONS
from espn_scraper.storage import snapshot_file
from glossary import column_config
from i18n import t
from metrics import score_check
from loaders import (SUPERBET_COOLDOWN, clear_rotowire, fetch_superbet, games, player_logs, season_label,
                     season_status, snapshot_history, superbet_error, superbet_wait)

lang = language()
page_header(t('dc.title', lang), t('dc.purpose', lang))


def queue(job: str, **options):
    """Buttons only queue a job; it runs at the top of the next run, before the cards read the data, so the
    cards already show what it fetched."""
    st.session_state['data_job'] = (job, options)


# --- the usual daily run ---
with st.container(border=True):
    left, right = st.columns([4, 1], vertical_alignment='center')
    left.markdown(t('dc.routine', lang))
    right.button(t('dc.run_both', lang), type='primary', width='stretch', icon="▶️", on_click=queue,
                 args=('routine',))

job = st.session_state.pop('data_job', None)
if job:
    name, options = job
    if name in ('routine', 'snapshot', 'fetch_superbet') and superbet_wait():
        # Superbet blocks frequent requests: every job that contacts it waits out the cooldown
        st.warning(t('dc.cooldown', lang, min=SUPERBET_COOLDOWN.seconds // 60, wait=superbet_wait().seconds // 60 + 1)
                   + (t('dc.stats_only', lang) if name == 'routine' else ""))
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
        with st.spinner(t('dc.fetching', lang)):
            error = fetch_superbet()
        if error:
            st.error(t('dc.fetch_failed', lang, error=error[:200]))
        else:
            st.toast(t('dc.fetched', lang))

superbet()   # records which Superbet data the pages read, for the status line
rw = rotowire()
status = freshness.overview(LAST_FETCH, lang=lang)
last = jobs.last_runs()


def stats_run_caption():
    """The last stats update started from the dashboard (scheduled runs aren't logged)."""
    run = last.get('stats')
    if run:
        ok = "✅" if run['exit_code'] == 0 else "❌"
        when = pd.to_datetime(run['started_at'], utc=True).tz_convert(freshness.PL).strftime('%a %d %b %H:%M')
        st.caption(t('dc.last_stats', lang, ok=ok, when=when, summary=run['summary'] or t('dc.no_output', lang)))


HOW = {'fetch': t('dc.how.fetch', lang), 'snapshot': t('dc.how.snapshot', lang)}


def superbet_caption():
    """The last saved fetch: the same data the freshness strip and every page read, so they can't disagree. How
    it was made comes from the run log when it's there (a scheduled snapshot or an older fetch isn't logged); a
    failed attempt after it is shown too."""
    offers = superbet()
    when, s = offers['fetched_at'], offers['status']
    runs = [r for job, r in last.items() if job in HOW]
    if when is None:
        st.caption(t('dc.no_fetch', lang))
    else:
        made = [HOW[r['job']] for r in runs if r['exit_code'] == 0
                and abs((pd.to_datetime(r['started_at'], utc=True) - pd.Timestamp(when)).total_seconds()) < 180]
        st.caption(t('dc.last_fetch', lang, when=f"{pd.Timestamp(when).tz_convert(freshness.PL):%a %d %b %H:%M}",
                     lines=f"{s['lines']:,}", games=s['games']) + (f" ({made[0]})" if made else ""))
    failed = [r for r in runs if r['exit_code'] != 0
              and (when is None or pd.to_datetime(r['started_at'], utc=True) > pd.Timestamp(when))]
    for r in failed[:1]:
        st.caption(t('dc.later_failed', lang,
                     when=f"{pd.to_datetime(r['started_at'], utc=True).tz_convert(freshness.PL):%a %H:%M}",
                     how=HOW[r['job']], summary=r['summary']))


def lineups_caption():
    """The last saved RotoWire version (what a restart would show) and, when the run log has it, what changed."""
    history = snapshot_history('rotowire_lineups')
    if history.empty:
        st.caption(t('dc.no_lineups', lang))
        return
    newest = history['fetched_at'].max()
    last_saved = history[history['fetched_at'] == newest]
    when = pd.to_datetime(newest, utc=True)
    days = ', '.join(f"{pd.Timestamp(d):%b %d}" for d in sorted(last_saved['game_date'].astype(str).unique()))
    st.caption(t('dc.last_lineups', lang, when=f"{when.tz_convert(freshness.PL):%a %d %b %H:%M}",
                 n=len(last_saved), days=days))
    run = last.get('lineups')
    if run is not None and abs((pd.to_datetime(run['started_at'], utc=True) - when).total_seconds()) < 180:
        st.caption(run['summary'].replace('saved ', 'Saved ', 1))


stats_col, odds_col, lineup_col = st.columns(3)

# --- ESPN stats ---
with stats_col.container(border=True):
    s = status['stats']
    st.markdown(f"{t('dc.stats_card', lang)}\n{s['icon']} **{s['label']}** · {s['detail']}")
    seasons = season_status()
    current = seasons[seasons['season'] == season_label(CURRENT_SEASON)].iloc[0]
    m = st.columns(2)
    m[0].metric(t('dc.games_season', lang), int(current['games']), border=True)
    m[1].metric(t('dc.last_game', lang), f"{current['last game']:%b %d}" if current['last game'] else '–',
                border=True)
    st.button(t('dc.update', lang, season=season_label(CURRENT_SEASON)), type='primary', width='stretch',
              on_click=queue, args=('stats',), help=t('dc.update_help', lang))
    with st.expander(t('dc.other', lang)):
        season = st.selectbox(t('dc.season', lang), sorted(SEASONS, reverse=True), format_func=season_label)
        how = st.radio("What", ['new', 'range', 'one', 'rebuild'], horizontal=True, label_visibility='collapsed',
                       format_func=lambda k: t(f'dc.how.{k}', lang))
        options = {'season': season}
        if how == 'range':
            d = st.columns(2)
            options['since'] = d[0].date_input(t('dc.from', lang), date.fromisoformat(SEASONS[season][0]))
            options['until'] = d[1].date_input(t('dc.to', lang),
                                               min(date.today(), date.fromisoformat(SEASONS[season][1])))
        elif how == 'one':
            options = {'game': st.text_input(t('dc.game_id', lang), placeholder="401898398",
                                             help=t('dc.game_id_help', lang))}
        elif how == 'rebuild':
            options['rebuild'] = st.checkbox(t('dc.rebuild_confirm', lang, season=season_label(season)))
        ready = (how != 'one' or options.get('game')) and (how != 'rebuild' or options['rebuild'])
        st.button(t('dc.run', lang), disabled=not ready, width='stretch', on_click=queue, args=('stats',),
                  kwargs=options)
    stats_run_caption()

# --- Superbet ---
with odds_col.container(border=True):
    s = status['superbet']
    st.markdown(f"{t('dc.superbet_card', lang)}\n{s['icon']} **{s['label']}** · {s['detail']}")
    m = st.columns(2)
    m[0].metric(t('dc.lines', lang), len(props()), border=True, help=t('dc.lines_help', lang))
    m[1].metric(t('dc.games', lang), game_odds()['event_id'].nunique() if len(game_odds()) else 0, border=True,
                help=t('dc.games_help', lang))
    st.caption(t('dc.superbet_caption', lang, min=SUPERBET_COOLDOWN.seconds // 60))
    if superbet()['status']['state'] == 'all_started':
        st.info(t('dc.all_started', lang))
    if superbet_error():
        st.warning(t('dc.last_failed', lang, error=superbet_error()[:150]))
    wait = superbet_wait()
    again = t('dc.again_in', lang, n=wait.seconds // 60 + 1) if wait else None
    b = st.columns(2)
    b[0].button(t('dc.fetch', lang), key='fetch_superbet', type='primary', width='stretch', disabled=wait is not None,
                on_click=queue, args=('fetch_superbet',), help=again or t('dc.fetch_help', lang))
    b[1].button(t('dc.snapshot', lang), key='snap_superbet', width='stretch', disabled=wait is not None,
                on_click=queue, args=('snapshot',), help=again or t('dc.snapshot_help', lang))
    superbet_caption()

# --- RotoWire ---
with lineup_col.container(border=True):
    s = status['rotowire']
    st.markdown(f"{t('dc.rotowire_card', lang)}\n{s['icon']} **{s['label']}** · {s['detail']}")
    listed = lineups()
    confirmed = listed.drop_duplicates('team')['lineup_status'].eq('confirmed').sum() if len(listed) else 0
    m = st.columns(2)
    m[0].metric(t('dc.teams', lang), listed['team'].nunique() if len(listed) else 0,
                t('dc.confirmed', lang, n=confirmed), delta_color='off', delta_arrow='off', border=True,
                help=t('dc.teams_help', lang))
    m[1].metric(t('dc.may_not_play', lang), int((listed['role'] == 'may_not_play').sum()) if len(listed) else 0,
                border=True, help=t('dc.may_not_play_help', lang))
    if rw['error']:
        st.warning(t('dc.rw_error', lang, error=rw['error'][:150]))
    b = st.columns(2)
    if b[0].button(t('dc.fetch_live', lang), key='fetch_rotowire', width='stretch', help=t('dc.fetch_live_help', lang)):
        clear_rotowire()
        st.rerun()
    b[1].button(t('dc.tomorrow', lang), key='snap_tomorrow', width='stretch', on_click=queue, args=('snapshot',),
                disabled=superbet_wait() is not None, kwargs={'tomorrow': True}, help=t('dc.tomorrow_help', lang))
    lineups_caption()

st.caption(t('dc.rw_caption', lang))
if st.button(t('dc.reload', lang), help=t('dc.reload_help', lang)):
    clear_live()
    st.rerun()

# --- what's stored, runs, checks ---
stored_tab, runs_tab, names_tab, quality_tab = st.tabs([t(f'dc.tab.{k}', lang)
                                                        for k in ('stored', 'runs', 'names', 'quality')])

with stored_tab:
    st.dataframe(seasons, hide_index=True, width='stretch',
                 column_config=column_config(seasons.columns, lang=lang, context='data'))
    rows = []
    for name in ['superbet_props', 'superbet_game_odds', 'rotowire_lineups']:
        path = snapshot_file(CURRENT_SEASON, name)
        fetched = pd.read_csv(path, usecols=['fetched_at'])['fetched_at'] if os.path.exists(path) else pd.Series()
        rows.append({'file': path, 'rows': len(fetched), 'snapshots': fetched.nunique(),
                     'first': fetched.min() if len(fetched) else None, 'last': fetched.max() if len(fetched) else None})
    snapshots = pd.DataFrame(rows)
    st.dataframe(snapshots, hide_index=True, width='stretch',
                 column_config=column_config(snapshots.columns, lang=lang, context='data'))

with runs_tab:
    runs = jobs.recent_runs()
    if runs.empty:
        st.caption(t('dc.no_runs', lang, path=jobs.RUN_LOG))
    else:
        st.dataframe(runs, hide_index=True, width='stretch',
                     column_config=column_config(runs.columns, {'seconds': '%.0f'}, lang=lang, context='data'))

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
        st.warning(t('dc.unmatched', lang, n=len(unmatched)))
        unmatched = pd.DataFrame(unmatched)
        st.dataframe(unmatched, hide_index=True, width='stretch',
                     column_config=column_config(unmatched.columns, lang=lang, context='data'))
    else:
        st.success(t('dc.all_matched', lang))

with quality_tab:
    bad = score_check(games(), player_logs())
    if bad.empty:
        st.success(t('dc.points_ok', lang))
    else:
        st.warning(t('dc.points_bad', lang, n=len(bad)))
        st.dataframe(bad, width='stretch', column_config=column_config(bad.columns, lang=lang, context='data'))
