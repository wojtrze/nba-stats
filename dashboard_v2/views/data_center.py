import os
from datetime import date

import pandas as pd
import streamlit as st

from core import fetch_worker, freshness, jobs
from core.data import LAST_FETCH, clear_live, game_odds, lineups, props, rotowire, superbet
from core.state import language
from core.ui import page_header
from espn_scraper import CURRENT_SEASON, SEASONS
from espn_scraper.storage import snapshot_file
from glossary import column_config
from i18n import t
from metrics import score_check
import power_events
from tracking import CLOSE_MAX_AGE_MIN, close_coverage, collection_report
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


# --- the scheduled fetches (fetch_loop, a thread of this dashboard) ---
@st.fragment(run_every=30)
def schedule_card():
    import fetch_loop
    import superbet_fetcher
    from http_polite import DAILY_REQUEST_BUDGET, blocked_until, requests_today
    fetch_worker.follow_settings()           # also restarts a worker stopped to change keep_awake
    settings = fetch_loop.worker_settings()
    with st.container(border=True):
        st.markdown(t('dc.schedule_card', lang))
        st.caption(t('dc.schedule_how', lang))
        c = st.columns(2)
        enabled = c[0].toggle(t('dc.schedule_switch', lang), value=settings['enabled'], key='schedule_on')
        awake = c[1].toggle(t('dc.keep_awake', lang), value=settings['keep_awake'], key='schedule_awake',
                            help=t('dc.keep_awake_help', lang))
        if (enabled, awake) != (settings['enabled'], settings['keep_awake']):
            fetch_loop.save_worker_settings(enabled=enabled, keep_awake=awake)
            if awake != settings['keep_awake']:
                fetch_worker.stop()          # restarted with the new setting on the next page run
            fetch_worker.follow_settings()
        s = fetch_worker.status()
        raw = s.get('state', 'stopped') if s['running'] else 'stopped'
        if raw.startswith('another'):
            state = t('dc.state.other', lang)
        elif raw.startswith('fetching'):
            state = t('dc.state.fetching', lang) + raw[len('fetching'):]
        elif raw in ('waiting', 'starting', 'stopped'):
            state = t(f'dc.state.{raw}', lang)
        else:
            state = raw
        nxt = s.get('next')
        st.markdown(t('dc.schedule_state', lang, state=state, games=s.get('games', 0),
                      next=f"{pd.Timestamp(nxt).tz_convert(freshness.PL):%a %H:%M}" if nxt else '–'))
        last_run = s.get('last')
        if last_run:
            st.caption(t('dc.schedule_last', lang, ok="✅" if last_run['ok'] else "❌", summary=last_run['summary'],
                         when=f"{pd.Timestamp(last_run['at']).tz_convert(freshness.PL):%H:%M}"))
        if s.get('skipped'):
            st.warning(t('dc.schedule_skipped', lang, n=s['skipped']))
        until = blocked_until(superbet_fetcher.HOST)
        if until:
            st.warning(t('dc.schedule_blocked', lang, when=f"{pd.Timestamp(until).tz_convert(freshness.PL):%H:%M}"))
        st.caption(t('dc.schedule_budget', lang, n=requests_today(superbet_fetcher.HOST),
                     budget=DAILY_REQUEST_BUDGET))
        reads = snapshot_file(CURRENT_SEASON, 'superbet_event_fetches')
        cover = close_coverage(pd.read_csv(reads), pd.Timestamp.now(tz='UTC')) if os.path.exists(reads) else None
        if cover:
            st.caption(t('dc.schedule_closes', lang, night=f"{cover['night']:%d.%m}", n=cover['valid'],
                         games=cover['games'], minutes=CLOSE_MAX_AGE_MIN))
        power = power_events.power_status()
        if power and power['on_battery']:
            st.warning(t('dc.on_battery', lang, pct=power['percent'] if power['percent'] is not None else '?'))


def _pl(ts) -> str:
    return f"{pd.Timestamp(ts).tz_convert(freshness.PL):%H:%M}"


@st.cache_data(ttl=600, show_spinner=False)
def _collection(stamp: str):
    """Last night's collection report (tracking.collection_report) with the computer's sleeps in its gaps;
    `stamp` (the run log's size and the hour) refreshes it."""
    import fetch_loop
    from daily_snapshot import RUN_LOG
    reads_path = snapshot_file(CURRENT_SEASON, 'superbet_event_fetches')
    props_path = snapshot_file(CURRENT_SEASON, 'superbet_props')
    if not (os.path.exists(reads_path) and os.path.exists(RUN_LOG)):
        return None
    reads = pd.read_csv(reads_path)
    known = pd.read_csv(props_path, usecols=['event_id', 'start_time']).drop_duplicates() \
        if os.path.exists(props_path) else reads[['event_id', 'start_time']]
    report = collection_report(reads, known, pd.read_csv(RUN_LOG), pd.Timestamp.now(tz='UTC'))
    if report and report['gaps']:
        events = power_events.sleep_events(report['gaps'][0][0] - pd.Timedelta(hours=2))
        report['sleeps'] = power_events.sleeps_in(events, report['gaps'])
    return report


def collection_card():
    from daily_snapshot import RUN_LOG
    stamp = f"{os.path.getsize(RUN_LOG) if os.path.exists(RUN_LOG) else 0}:{pd.Timestamp.now():%Y%m%d%H}"
    report = _collection(stamp)
    if not report:
        return
    with st.container(border=True):
        st.markdown(t('dc.cover', lang))
        night = f"{report['night']:%d.%m}"
        if report['valid'] == report['games']:
            st.markdown(t('dc.cover_ok', lang, night=night, games=report['games']))
        else:
            st.markdown(t('dc.cover_partial', lang, night=night, n=report['valid'], games=report['games'],
                          minutes=CLOSE_MAX_AGE_MIN))
        for gap in report.get('sleeps', []):
            if gap['sleep_at'] is not None:
                reason = gap['reason']
                reason = t(f'dc.reason.{reason}', lang) if reason in power_events.REASONS.values() else reason
                wake = t('dc.cover_wake', lang, wake=_pl(gap['wake_at'])) if gap['wake_at'] is not None else ''
                st.markdown('- ' + t('dc.cover_gap_sleep', lang, start=_pl(gap['from']), end=_pl(gap['to']),
                                     sleep=_pl(gap['sleep_at']), reason=reason, wake=wake))
            else:
                st.markdown('- ' + t('dc.cover_gap_off', lang, start=_pl(gap['from']), end=_pl(gap['to'])))
        for key in ('stuck', 'restarts', 'offline'):
            if report[key]:
                st.markdown('- ' + t(f'dc.cover_{key}', lang, n=report[key]))
        st.caption(t('dc.limits', lang))


def settings_card():
    import fetch_loop
    import fetch_schedule
    from http_polite import DAILY_REQUEST_BUDGET
    saved = fetch_loop.schedule_config()
    d = fetch_schedule.DEFAULT
    with st.expander(t('dc.settings', lang)):
        hours = lambda n: t('dc.set.off', lang) if n == 0 else t('dc.set.hours', lang, n=n)
        c = st.columns(2)
        hourly_every = c[0].selectbox(t('dc.set.hourly_every', lang), [0, 1, 2, 3, 4, 6],
                                      index=[0, 1, 2, 3, 4, 6].index(saved.hourly_every)
                                      if saved.hourly_every in (0, 1, 2, 3, 4, 6) else 1,
                                      format_func=hours, help=t('dc.set.hourly_every_help', lang), key='set_hourly')
        horizon = c[1].number_input(t('dc.set.hourly_horizon', lang), 1, 48, saved.hourly_horizon, key='set_horizon')
        options = sorted(set((120, 90, 60, 45, 40, 30, 20, 15, 10, 5, 2) + saved.last_hour), reverse=True)
        last_hour = st.multiselect(t('dc.set.last_hour', lang), options, default=list(saved.last_hour),
                                   format_func=lambda m: f"T-{m}", help=t('dc.set.last_hour_help', lang),
                                   key='set_last_hour')
        c = st.columns(2)
        priced_every = c[0].selectbox(t('dc.set.priced_every', lang), [0, 1, 2, 3, 4, 6, 12],
                                      index=[0, 1, 2, 3, 4, 6, 12].index(saved.priced_every)
                                      if saved.priced_every in (0, 1, 2, 3, 4, 6, 12) else 2,
                                      format_func=hours, help=t('dc.set.priced_every_help', lang), key='set_priced')
        rotowire = c[1].checkbox(t('dc.set.rotowire', lang), saved.rotowire, key='set_rotowire')
        c = st.columns(2)
        late = c[0].number_input(t('dc.set.late', lang), 1, 30, saved.late, key='set_late')
        slot_limit = c[1].number_input(t('dc.set.slot_limit', lang), 2, 30, saved.slot_limit,
                                       help=t('dc.set.slot_limit_help', lang), key='set_slot_limit')
        cfg = fetch_schedule.Config(hourly_every=int(hourly_every), hourly_horizon=int(horizon),
                                    last_hour=tuple(sorted({int(m) for m in last_hour}, reverse=True)),
                                    priced_every=int(priced_every), rotowire=bool(rotowire), late=int(late),
                                    slot_limit=int(slot_limit))
        problems = cfg.problems()
        tips = fetch_loop.known_tips()
        plan = fetch_loop.plan(tips, pd.Timestamp.now(tz='UTC').to_pydatetime(), cfg)
        requests = int(plan['requests'].sum()) if len(plan) else 0
        if len(plan):
            st.markdown(t('dc.set.preview', lang, runs=len(plan), n=requests, budget=DAILY_REQUEST_BUDGET))
            shown = plan.assign(at=plan['at'].map(lambda a: f"{pd.Timestamp(a).tz_convert(freshness.PL):%a %H:%M}"))
            st.dataframe(shown, hide_index=True, width='stretch', height=200)
        else:
            st.caption(t('dc.set.no_games', lang))
        over = requests > DAILY_REQUEST_BUDGET
        if problems:
            st.error(t('dc.set.invalid', lang, what=', '.join(problems)))
        elif over:
            st.error(t('dc.set.over_budget', lang))
        c = st.columns(2)
        if c[0].button(t('dc.set.save', lang), disabled=bool(problems) or over or cfg == saved, type='primary'):
            fetch_loop.save_worker_settings(schedule=cfg)
            st.success(t('dc.set.saved', lang))
        if c[1].button(t('dc.set.reset', lang), disabled=saved == d):
            fetch_loop.save_worker_settings(schedule=d)
            for key in ('set_hourly', 'set_horizon', 'set_last_hour', 'set_priced', 'set_rotowire', 'set_late',
                        'set_slot_limit'):
                st.session_state.pop(key, None)
            st.rerun()
        st.caption(t('dc.set.limits_fixed', lang, budget=DAILY_REQUEST_BUDGET))


schedule_card()
collection_card()
settings_card()
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
