import pandas as pd
import streamlit as st

from core.data import (absence_record, absence_window_tonight, game_odds, news_record, news_tonight, priced_props,
                       settled_lines, settled_props, superbet)
from core.analysis import last_game_lines, lookback_summary
from core.columns import OVERVIEW_LOOKBACK, OVERVIEW_NEAREST
from core.state import language
from core.ui import PAGES, no_offers, page_header, table
from insights import line_streaks, night_curiosities, spot_on_stats, tonight_streaks
from loaders import filtered_logs, player_logs
from models import load_calibration, top_up_logs
import absence_window
import news
import night_view
import whatif
from i18n import t, value

# the Overview's research blocks, moved here so the Overview reads as tonight's picks and last night: the lines
# nearest to break-even, tonight's players in their last game, the news window (H4), big chances (H10), last
# night's curiosities and tonight's streaks. Research only: nothing here changes a decision or a rating
lang = language()
seasons, season_types = page_header(t('research.title', lang), t('research.purpose', lang), with_scope=True)
STAT = lambda s: 'PRA' if s == 'ARP' else s
TOP_STREAKS = 10
NEAREST = 5
LOOKBACK_LIST = 10


def focus(event_id, name_espn, bet_type):
    """Open that line on Props."""
    st.session_state['props_focus'] = (event_id, name_espn, bet_type)
    st.switch_page(PAGES['props'])


props = pd.DataFrame()
if game_odds().empty:
    no_offers(superbet()['status'])
else:
    props = priced_props(seasons, season_types)

# --- tonight against break-even after tax: the lines nearest to it, and tonight's players in their last game ---
def breakeven_block(props: pd.DataFrame):
    rows = whatif.night_gaps(props)
    priced = rows[rows['side'].isin(['Over', 'Under']) & rows['distance pp'].notna()]
    st.markdown(f"**{t('overview.breakeven', lang)}**", help=t('overview.breakeven_help', lang))
    if priced.empty:
        return
    logs = filtered_logs(seasons, season_types)
    by_player = {pid: g for pid, g in logs.groupby('player_id_ESPN')}

    def values_of(r):
        # the games the line was priced from (priced_props tops a player with few games up with last season's)
        own = by_player.get(r['player_id'], logs.iloc[0:0])
        return top_up_logs(own, player_logs(), max(seasons), [r['player_id']]).sort_values('Date')[r['bet_type']]

    near = whatif.nearest(priced, values_of, load_calibration(), n=NEAREST)
    above = int((priced['distance pp'] > 0).sum())
    if above:
        st.markdown(t('overview.breakeven_some', lang, n=len(priced), above=above))
        st.caption(t('whatif.caveat', lang))
    else:
        r = near.iloc[0]
        needs = t('overview.breakeven_needs', lang, need=r['needed odds'], now=r['side odds']) \
            if pd.notna(r['needed odds']) else ''
        st.markdown(t('overview.breakeven_none', lang, n=len(priced), name=r['name'], stat=STAT(r['bet_type']),
                      side=value(r['side'], lang), line=r['line'], odds=r['side odds'], gap=-r['distance pp'],
                      needs=needs))
    st.caption(t('overview.breakeven_table', lang, n=len(near)))
    shown = near.assign(side=near['side'].map(lambda v: value(v, lang)))
    picked = table(shown, OVERVIEW_NEAREST, {'line': '%g', 'side odds': '%.2f', 'p win %': '%.1f',
                                             'break-even net %': '%.1f', 'edge net pp': '%+.1f',
                                             'needed odds': '%.2f', 'gap sd': '%+.1f'},
                   key='nearest_breakeven', select=True)
    if picked is not None:
        r = near.iloc[picked]
        focus(r['event_id'], r['name_ESPN'], r['bet_type'])

    # tonight's players in their last game: the side toward our expectation then, against its price
    st.markdown(f"**{t('overview.lookback', lang)}**", help=t('overview.lookback_help', lang))
    last = last_game_lines(settled_lines(tuple(seasons), tuple(season_types)),
                           props[props['player_id'].notna()][['event_id', 'name_ESPN', 'name', 'player_id', 'bet_type',
                                                             'start_time']])
    summary = lookback_summary(last)
    if not summary['all']['lines']:
        st.caption(t('overview.lookback_none', lang))
        return
    a = summary['all']
    text = t('overview.lookback_all', lang, lines=a['lines'], players=a['players'], won=a['won %'],
             price=a['price %'], diff=a['won − price pp'], ret=a['return 100'])
    w = summary['wide']
    if w['lines']:
        text += ' ' + t('overview.lookback_wide', lang, lines=w['lines'], won=w['won %'], price=w['price %'],
                        diff=w['won − price pp'], ret=w['return 100'])
    st.markdown(text)
    st.caption(t('overview.lookback_luck', lang))
    widest = last[last['last gap sd'].notna()].assign(_abs=last['last gap sd'].abs()) \
        .sort_values('_abs', ascending=False).head(LOOKBACK_LIST).reset_index(drop=True)
    if widest.empty:
        return
    with st.expander(t('overview.lookback_list', lang, n=len(widest))):
        listed = pd.DataFrame({
            'name': widest['name'], 'bet_type': widest['bet_type'].map(STAT),
            'game_date': pd.to_datetime(widest['last date']).dt.strftime('%d.%m'), 'line': widest['last line'],
            'proj_avg': widest['last proj'], 'gap sd': widest['last gap sd'],
            'side': widest['last side'].map(lambda v: value(v, lang)), 'actual': widest['last actual'],
            'result': widest['last result'].map(lambda v: value(v, lang) if isinstance(v, str) else v),
            'return 100': widest['last return 100']})
        picked = table(listed, OVERVIEW_LOOKBACK, {'line': '%g', 'proj_avg': '%.1f', 'gap sd': '%+.1f',
                                                   'actual': '%g', 'return 100': '%+.0f'},
                       key='lookback_list', select=True)
        if picked is not None:
            r = widest.iloc[picked]
            focus(r['event_id'], r['name_ESPN'], r['bet_type'])


if len(props):
    breakeven_block(props)


# --- the news window (H4, a research hypothesis) and the place for big chances against Superbet ---
NEWS_COLUMNS = ['player', 'stat', 'before', 'first read', 'close', 'kind', 'minutes']


def _pl_clock(ts) -> str:
    return pd.Timestamp(ts).tz_convert('Europe/Warsaw').strftime('%H:%M')


def news_block():
    st.subheader(t('overview.news', lang), help=t('overview.news_help', lang))
    st.caption(t('overview.news_note', lang))
    rec = news_record().get('recognition')
    if rec and rec.get('signals'):
        st.caption(t('overview.news_record', lang, nights=rec['nights'], d=news_record()['d'],
                     reacted=rec.get('reacted by our read %') or 0, other=rec.get('other team moved %') or 0,
                     signals=rec['signals'], won=rec.get('won %') or 0, clv=rec.get('CLV after tax %') or 0,
                     closes=rec.get('with a close') or 0, n=news_record()['evaluation']['nights']))
    else:
        st.caption(t('overview.news_record_none', lang))
    found = news_tonight()
    if not found:
        st.caption(t('overview.news_none', lang))
        return
    for e in found:
        lines = e['lines']
        kinds = lines['kind'].value_counts() if len(lines) else pd.Series(dtype=int)
        st.markdown(t('overview.news_event' if len(lines) else 'overview.news_event_alone', lang,
                      name=e['name'], team=e['team'].upper(),
                      kind=t(f"news.{e['kind']}", lang), seen=_pl_clock(e['seen_at']),
                      own=t(f"news.own.{e['own']}", lang), early=int(kinds.get(news.MOVED_EARLY, 0)),
                      gone=int(kinds.get(news.WITHDRAWN, 0)), later=int(kinds.get(news.MOVED_LATER, 0)),
                      never=int(kinds.get(news.NEVER, 0))))
        if len(lines):
            with st.expander(t('overview.news_lines', lang)):
                shown = lines.assign(kind=lines['kind'].map(lambda k: t(f'news.kind.{k}', lang)),
                                     stat=lines['stat'].map(STAT),
                                     minutes=lines['minutes to move'].round())[NEWS_COLUMNS]
                st.dataframe(shown.rename(columns={c: t(f'news.col.{c}', lang) for c in NEWS_COLUMNS}),
                             hide_index=True, use_container_width=True)


news_block()


# --- big chances vs Superbet: the expert's recipe (H10, a research hypothesis) ---
BIG_COLUMNS = ['name', 'bet_type', 'line', 'side', 'odds', 'usual', 'without', 'change', 'share %', 'n without',
               'previous line', 'shift', 'new line', 'p side %', 'price %', 'gap pp', 'break-even net %']
BIG_FORMATS = {'line': '%g', 'odds': '%.2f', 'usual': '%.1f', 'without': '%.1f', 'change': '%+.1f',
               'share %': '%+.0f', 'previous line': '%g', 'shift': '%+g', 'p side %': '%.0f', 'price %': '%.0f',
               'gap pp': '%+.1f', 'break-even net %': '%.0f'}


def big_record_caption():
    rec = absence_record()
    every, first, old = rec.get('recognition · all'), rec.get('recognition · first game'), rec.get('2022')
    if not every or not every.get('signals'):
        st.caption(t('overview.big_record_none', lang))
        return
    num = lambda v: v if v is not None else float('nan')
    st.caption(t('overview.big_record', lang, nights=every['nights'], d=rec['d'], signals=every['signals'],
                 won=num(every['won %']), diff=num(every['won − price pp']), roi=num(every['ROI after tax %']),
                 clv=num(every['CLV after tax %']), f_signals=(first or {}).get('signals') or 0,
                 f_diff=num((first or {}).get('won − price pp')), f_roi=num((first or {}).get('ROI after tax %')),
                 h_diff=num((old or {}).get('won − price pp')), h_lines=(old or {}).get('lines') or 0,
                 n=rec.get('evaluation · all', {}).get('nights') or 0))


def _entry(r) -> str:
    """'**Name** PTS +3.1 (+24%, 14 g., line 9.5)'."""
    line = t('overview.big_line', lang, line=r['line']) if r['line'] is not None else t('overview.big_no_line', lang)
    return t('overview.big_entry', lang, name=r['name'], stat=r['stat'], change=r['change'], share=r['share %'],
             n=r['n_without'], line=line)


def gains_text(gains) -> list:
    """The lines under an absence: his likely replacements at his position, then whom the with/without moves most."""
    if not gains:
        return []
    if gains['too_few']:
        return [t('overview.big_too_few', lang)]
    out = []
    if gains['replacements']:
        names = [f"**{r['name']}**" + (', ' + t('overview.big_promoted', lang) if r['promoted'] else '')
                 + ', ' + t('overview.big_minutes', lang, minutes=r['min_change'], n=r['n_without'])
                 for r in gains['replacements']]
        out.append(t('overview.big_replacements', lang, position=t(f"position.{gains['position']}", lang),
                     names='; '.join(names)))
    if gains['affected']:
        out.append(t('overview.big_affected', lang, names=', '.join(_entry(r) for r in gains['affected'])))
    return out


def big_block(props: pd.DataFrame):
    st.subheader(t('overview.big', lang))
    st.caption(t('overview.big_note', lang))
    big_record_caption()
    found = absence_window_tonight(seasons, season_types, props)
    out = absence_window.fresh(found['out']) if len(found['out']) else found['out']
    if out.empty:
        st.caption(t('overview.big_none', lang))
        return
    lines = found['lines']
    for _, o in out.sort_values(['game_no', 'since']).iterrows():
        game = t('overview.big_first', lang) if o['game_no'] == 1 else t('overview.big_nth', lang, n=int(o['game_no']))
        text = t('overview.big_out', lang, name=o['name'], team=o['team'].upper(), since=_pl_clock(o['since']),
                 game=game, ques=t('overview.big_ques', lang) if o['now_ques'] else '')
        gains = found.get('gains', {}).get(int(o['player_id_ESPN']))
        st.markdown("  \n".join([text] + gains_text(gains)))
    if lines.empty:
        st.caption(t('overview.big_no_lines', lang))
        return
    above = int((lines['p side %'] > lines['break-even net %']).sum())
    if above:
        st.caption(t('overview.big_above', lang, n=above))
    for team, part in lines.groupby('team', sort=False):
        part = part.reset_index(drop=True)
        with st.expander(f"{team.upper()} · {part['out'].iloc[0]} · " + t('overview.big_lines', lang, n=len(part))):
            shown = part.assign(bet_type=part['bet_type'].map(STAT), side=part['side'].map(lambda v: value(v, lang)),
                                **{'new line': part['new line'].map({True: '✓', False: ''})})
            picked = table(shown, BIG_COLUMNS, BIG_FORMATS, key=f'big_{team}', select=True, context='absence')
            if picked is not None:
                r = part.iloc[picked]
                focus(r['event_id'], r['name_ESPN'], r['bet_type'])


if len(props):
    big_block(props)
else:
    st.subheader(t('overview.big', lang))
    st.caption(t('overview.big_note', lang))

def spot_lines(s, season):
    """The Spot on numbers: last night's (s) and the season's, from insights.spot_on_stats."""
    out = []
    if s:
        out.append(t('overview.spot.hit', lang, n=s['lines'], ours=s['our spot %'], line=s['line spot %']))
        out.append(t('overview.spot.closer', lang, ours=s['closer %'], line=s['line closer %'], tie=s['tie %']))
        sides = [t(key, lang, stats=', '.join(map(STAT, s[part])))
                 for key, part in (('overview.spot.we_in', 'we closer'), ('overview.spot.line_in', 'line closer'))
                 if s[part]]
        if sides:
            out.append('; '.join(sides))
        bias = 'none' if abs(s['bias']) < 0.05 else 'low' if s['bias'] > 0 else 'high'   # rounds to 0.0
        out.append(t(f'overview.spot.bias_{bias}', lang, bias=abs(s['bias']), over=s['over %']))
    if season:
        out.append(t('overview.spot.season', lang, nights=season['nights'], n=season['lines'],
                     ours=season['our spot %'], line=season['line spot %'], closer=season['closer %'],
                     line_closer=season['line closer %']))
    return out



# --- last night's curiosities: where we were furthest off, where we were spot on, the line's worst miss ---
night = night_view.latest_night()['settled']
if night is not None:
    day = pd.Timestamp(night).strftime('%a %b %d')
    night_props, game_part, rated, s = night_view.night_data([night])
    # curiosities: where we were furthest off, where we were spot on, the line's worst miss
    c = night_curiosities(night_props, game_part['games'])
    # ESPN's "Bam Adebayo" reads better than Superbet's "Adebayo, Bam"
    display = player_logs().groupby('player_id_ESPN')['player_display_name'].last()
    name = lambda r: display.get(r['player_id'], r['name']) if pd.notna(r['player_id']) else r['name']
    said = lambda r: t('overview.said', lang, name=name(r), stat=STAT(r['bet_type']), actual=r['actual'],
                       proj=r['proj_avg'], line=r['line'])
    if len(c['surprises']) or len(c['spot_on']):
        st.subheader(t('overview.curiosities', lang, night=day))
        left, right = st.columns(2)
        with left:
            st.markdown(f"**{t('overview.surprises', lang)}**", help=t('overview.surprises_help', lang))
            st.markdown("\n".join(f"- {said(r)}" for _, r in c['surprises'].iterrows()))
            if c['line_miss'] is not None:
                r = c['line_miss']
                st.caption(t('overview.line_miss', lang, name=name(r), stat=STAT(r['bet_type']), actual=r['actual'],
                             line=r['line']))
        with right:
            st.markdown(f"**{t('overview.spot_on', lang)}**", help=t('overview.spot_on_help', lang))
            st.caption("  \n".join(spot_lines(spot_on_stats(night_props), night_view.season_spot_on())))
            lines = [f"- {said(r)}" for _, r in c['spot_on'].iterrows()]
            if c['best_total'] is not None:
                g = c['best_total']
                lines.append("- " + t('overview.best_total', lang, game=g['game'],
                                      actual=g['home score'] + g['away score'], proj=g['proj home'] + g['proj away']))
            if c['best_margin'] is not None:
                g = c['best_margin']
                lines.append("- " + t('overview.best_margin', lang, game=g['game'], home=g['home'].upper(),
                                      actual=g['home score'] - g['away score'], proj=g['proj home'] - g['proj away']))
            st.markdown("\n".join(lines))


# --- streaks: tonight's players whose latest Superbet lines in a stat all went the same way ---
if len(props):
    streaks = tonight_streaks(line_streaks(settled_props()), props)
    st.subheader(t('overview.streaks', lang), help=t('overview.streaks_help', lang))
    if streaks.empty:
        st.caption(t('overview.streaks_none', lang))
    else:
        def streak_button(r, i):
            words = dict(name=r['name'], n=int(r['n']), stat=STAT(r['bet_type']),
                         side=t(f"overview.side.{r['side']}", lang), line=r['tonight line'])
            m = r.get('matchup_info')
            if isinstance(m, dict) and m and pd.notna(r.get('opp')):
                text = t('overview.streak_vs', lang, **words, opp=str(r['opp']).upper(),
                         pct=100 * (m['ratio'] - 1), position=t(f"reason.position.{m.get('group', '')}", lang))
            else:
                text = t('overview.streak', lang, **words)
            if st.button(text, key=f'streak_{i}', type='tertiary'):
                focus(r['event_id'], r['name_ESPN'], r['bet_type'])

        for i, r in streaks.head(TOP_STREAKS).iterrows():
            streak_button(r, i)
        if len(streaks) > TOP_STREAKS:
            with st.expander(t('overview.streaks_more', lang, n=len(streaks) - TOP_STREAKS)):
                for i, r in streaks.iloc[TOP_STREAKS:].iterrows():
                    streak_button(r, i)
