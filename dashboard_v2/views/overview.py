import pandas as pd
import streamlit as st

from core.data import (game_odds, player_decisions, priced_props, settled_lines, settled_props, shortlist_record,
                       superbet)
from core.analysis import last_game_lines, lookback_summary
from decisions import CZEKAJ, actionable, offers_table, star_text, stars
from tracking import star_scorecard
from core.columns import OVERVIEW_LOOKBACK, OVERVIEW_NEAREST, OVERVIEW_PROPS, SHORTLIST
from core.state import language
from core.ui import PAGES, kpis, no_offers, page_header, pl_time, table
from insights import line_streaks, night_curiosities, tonight_streaks
from loaders import filtered_logs, player_logs
from models import calibration_warning, load_calibration, top_up_logs
import night_view
import whatif
from i18n import t, value

lang = language()
seasons, season_types = page_header(t('overview.title', lang), t('overview.purpose', lang), with_scope=True)
STAT = lambda s: 'PRA' if s == 'ARP' else s
TOP_STREAKS = 10
NEAREST = 5
LOOKBACK_LIST = 10


def focus(event_id, name_espn, bet_type):
    """Open that line on Props."""
    st.session_state['props_focus'] = (event_id, name_espn, bet_type)
    st.switch_page(PAGES['props'])


# --- tonight: the decisions in numbers, the offers and the best rated lines ---
st.subheader(t('overview.tonight', lang))
odds = game_odds()
props = pd.DataFrame()
if odds.empty:
    no_offers(superbet()['status'])
else:
    props = priced_props(seasons, season_types)
    if warning := calibration_warning(props['calibration'].iloc[0] if len(props) else None, lang):
        st.warning(warning, icon="⚠️")
    decided = player_decisions(props)
    kpis([{'label': t('overview.kpi.games', lang), 'value': odds['event_id'].nunique()},
          {'label': t('overview.kpi.lines', lang), 'value': len(props), 'help': t('overview.kpi.lines_help', lang)},
          {'label': t('overview.kpi.obstaw', lang), 'value': len(actionable(decided)),
           'help': t('overview.kpi.obstaw_help', lang)}])
    st.page_link(PAGES['slate'], label=t('overview.all_games_link', lang), icon="🏟️")

    offers = offers_table(decided)
    if offers.empty:
        st.info(t('decision.none', lang), icon="⚖️")
    else:
        st.markdown(f"**{t('overview.offers', lang)}**")
        shown = offers.assign(**{col: offers[col].map(lambda v: value(v, lang)) for col in ('side', 'RotoWire')})
        picked = table(shown, OVERVIEW_PROPS, {'line': '%g', 'side odds': '%.2f', 'p win %': '%.0f',
                                               'edge net pp': '%+.1f', 'ev net 100': '%+.1f'},
                       key='top_props', select=True)
        if picked is not None:
            r = offers.iloc[picked]
            focus(r['event_id'], r['name_ESPN'], r['bet_type'])

    # tonight's ratings: the 4★ (and 3★) lines, shown with what they cost
    st.markdown(f"**{t('overview.shortlist', lang)}**", help=t('overview.shortlist_help', lang))
    best = stars(props, decided)
    best = best[best['stars'].fillna(0) >= 3]
    if best.empty:
        st.caption(t('overview.shortlist_empty', lang))
    else:
        def wait_text(event_id) -> str:
            d = decided.get(event_id)
            return t(d['reason'], lang, **d.get('values', {})) if d and d['status'] == CZEKAJ else ''

        best = best.assign(**{'star count': best['stars'], 'stars': best['stars'].map(star_text),
                              'side': best['side'].map(lambda v: value(v, lang)),
                              'tip-off': [pl_time(s) for s in best['start_time']],
                              'wait': best['event_id'].map(wait_text)})
        top = best[best['star count'] >= 4].reset_index(drop=True)
        formats = {'line': '%g', 'side odds': '%.2f', 'p win %': '%.0f', 'side market %': '%.0f',
                   'above price pp': '%+.1f', 'ev net 100': '%+.1f'}
        picked = table(top, SHORTLIST, formats, key='shortlist_top', select=True)
        st.caption(t('overview.shortlist_cost', lang, top=top['ev net 100'].mean(),
                     every=props['ev net 100'].mean()))
        if len(top) and (top['ev net 100'] < 0).all():
            st.caption(t('overview.shortlist_negative', lang))
        record = star_scorecard(shortlist_record()).set_index('stars') if len(shortlist_record()) else None
        if record is not None and record.loc[4, 'bets']:
            top_record = record.loc[4]
            st.caption(t('overview.shortlist_record', lang, nights=int(top_record['nights']),
                         bets=int(top_record['bets']), hit=top_record['hit %'], price=top_record['price said %'],
                         roi=top_record['ROI % std'], every=record.loc['every line', 'ROI % std']))
        rest = best[best['star count'] == 3].reset_index(drop=True)
        picked_row = None
        if len(rest):
            with st.expander(t('overview.shortlist_more', lang, n=len(rest))):
                more = table(rest, SHORTLIST, formats, key='shortlist_look', select=True)
            picked_row = rest.iloc[more] if more is not None else None
        if picked is not None:
            picked_row = top.iloc[picked]
        if picked_row is not None:
            focus(picked_row['event_id'], picked_row['name_ESPN'], picked_row['bet_type'])

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

# --- last night: how the lines, the rated bets and the games resolved ---
latest = night_view.latest_night()
if latest['pending']:
    st.info(t('night.pending', lang, nights=pd.Timestamp(latest['pending']).strftime('%a %b %d')))
    st.page_link(PAGES['data'], label=t('results.update', lang), icon="🔄")
night = latest['settled']
if night is None:
    st.caption(t('night.none', lang))
else:
    day = pd.Timestamp(night).strftime('%a %b %d')
    st.subheader(t('overview.last_night', lang, night=day))
    night_props, game_part, rated, s = night_view.night_data([night])
    night_view.summary_kpis(s, lang)
    if s.get('games scored'):
        st.caption(t('overview.games_note', lang, n=s['winners called'], total=s['games scored'],
                     miss=s['mean total miss']))
    if st.button(t('overview.night_link', lang), icon="📈", type='tertiary'):
        st.session_state['results_night'] = [night]
        st.switch_page(PAGES['results'])

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
            text = t('overview.streak', lang, name=r['name'], n=int(r['n']), stat=STAT(r['bet_type']),
                     side=t(f"overview.side.{r['side']}", lang), line=r['tonight line'])
            if st.button(text, key=f'streak_{i}', type='tertiary'):
                focus(r['event_id'], r['name_ESPN'], r['bet_type'])

        for i, r in streaks.head(TOP_STREAKS).iterrows():
            streak_button(r, i)
        if len(streaks) > TOP_STREAKS:
            with st.expander(t('overview.streaks_more', lang, n=len(streaks) - TOP_STREAKS)):
                for i, r in streaks.iloc[TOP_STREAKS:].iterrows():
                    streak_button(r, i)
