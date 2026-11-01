from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from components import decision_text, decision_times
from core.data import (game_odds, lineups as rotowire_lineups, player_decisions, priced_games, priced_props,
                       shortlist_record, superbet)
from decisions import CZEKAJ, actionable, offers_table, star_text, stars, team_decision
from tracking import star_scorecard
from core.columns import OVERVIEW_PROPS, SHORTLIST
from core.state import language
from core.ui import PAGES, kpis, no_offers, page_header, pl_time, stop, table
from espn_scraper import NBA_TEAM_NAMES
from models import calibration_warning
from schedule import minutes_to, starts_soon
from superbet_fetcher import main_lines
from core.labels import winner
from i18n import t, value

lang = language()
seasons, season_types = page_header(t('overview.title', lang), t('overview.purpose', lang), with_scope=True)

odds = game_odds()
if odds.empty:
    no_offers(superbet()['status'])
    stop()

lineups = rotowire_lineups()
props = priced_props(seasons, season_types)
if warning := calibration_warning(props['calibration'].iloc[0] if len(props) else None, lang):
    st.warning(warning, icon="⚠️")
games = priced_games()
by_event = {g['event_id']: g for g in games}
decided = player_decisions(props)
odds_at = superbet()['fetched_at']
main = pd.DataFrame(main_lines(odds.to_dict('records')))

kpis([{'label': t('overview.kpi.games', lang), 'value': odds['event_id'].nunique()},
      {'label': t('overview.kpi.lines', lang), 'value': len(props), 'help': t('overview.kpi.lines_help', lang)},
      {'label': t('overview.kpi.obstaw', lang), 'value': len(actionable(decided)),
       'help': t('overview.kpi.obstaw_help', lang)},
      {'label': t('overview.kpi.lineups', lang),
       'value': t('overview.kpi.lineups_value', lang, n=lineups['team'].nunique() if len(lineups) else 0),
       'help': t('overview.kpi.lineups_help', lang)},
      {'label': t('overview.kpi.out', lang),
       'value': int((lineups['role'] == 'may_not_play').sum()) if len(lineups) else 0}])

# --- the slate ---
st.subheader(t('overview.games', lang))


def lineup_line(team: str) -> str:
    listed = lineups[lineups['team'] == team]
    if listed.empty:
        return f"**{team.upper()}** · :gray[{t('overview.no_lineup', lang)}]"
    status = listed['lineup_status'].iloc[0] or 'listed'
    badge = f":green-badge[{t('overview.confirmed', lang)}]" if status == 'confirmed' else \
        f":orange-badge[{t('overview.expected', lang)}]"
    out = listed[listed['role'] == 'may_not_play']
    out = ", ".join(f"{r['name']} ({r['injury'] or '?'})" for _, r in out.iterrows())
    return f"**{team.upper()}** {badge}" + (f" · {t('overview.out', lang, names=out)}" if out else "")


# earliest tip-off first
events = odds.drop_duplicates('event_id').sort_values('start_time', key=lambda s: pd.to_datetime(s, utc=True))
now = datetime.now(timezone.utc)
for start in range(0, len(events), 3):
    cols = st.columns(3)
    for col, (_, e) in zip(cols, events.iloc[start:start + 3].iterrows()):
        m = main[main['event_id'] == e['event_id']]
        ml = m[m['market'] == 'ML'].set_index('side')['odds']
        spread = m[(m['market'] == 'SPREAD') & (m['side'] == 'home')]['line']
        total = m[m['market'] == 'TOTAL']['line']
        with col.container(border=True):
            st.markdown(f"#### {e['away'].upper()} @ {e['home'].upper()}")
            if starts_soon(e['start_time'], now):
                minutes = max(1, round(minutes_to(e['start_time'], now)))
                st.markdown(f":orange-badge[{t('overview.soon', lang, minutes=minutes)}]")
            teams = t('overview.at', lang, away=NBA_TEAM_NAMES.get(e['away'], ''),
                      home=NBA_TEAM_NAMES.get(e['home'], ''))
            st.caption(f"{pl_time(e['start_time'])} · {teams}")
            odds_text = " · ".join(filter(None, [
                f"{t('overview.ml', lang)} **{ml['away']:.2f}** / **{ml['home']:.2f}**"
                if {'away', 'home'} <= set(ml.index) else '',
                f"{e['home'].upper()} **{spread.iloc[0]:+g}**" if len(spread) else '',
                f"{t('overview.total', lang)} **{total.iloc[0]:g}**" if len(total) else '']))
            st.markdown(f"💰 {odds_text or t('overview.no_main', lang)}", help=t('overview.odds_help', lang))
            # one decision for the team markets and one for the players; the projection is context
            team = team_decision(by_event.get(e['event_id']), odds_at)
            st.markdown(f"**{t('decision.teams', lang)}:** {decision_text(team, lang)}")
            players = decided.get(e['event_id'])
            if players:
                d = players
                offer = f" · {d['offer']['name']} {value(d['offer']['side'], lang)} {d['offer']['line']:g} " \
                        f"{d['offer']['bet_type']} @ {d['offer']['side odds']:.2f}" if d['offer'] is not None else ''
                st.markdown(f"**{t('decision.players', lang)}:** {decision_text(d, lang)}{offer}")
                st.caption(decision_times(d, lang))
            else:
                st.caption(t('overview.no_props', lang))
            g = by_event.get(e['event_id'])
            if g:
                p = g['projection']
                st.markdown(t('overview.projected', lang, winner=winner(p, g['home'], g['away'], lang),
                              total=p['total']))
            st.markdown(lineup_line(e['away']) + "  \n" + lineup_line(e['home']))

# --- the offers to bet: only those of a 'Bet' decision ---
st.subheader(t('overview.offers', lang))
offers = offers_table(decided)
if offers.empty:
    st.info(t('decision.none', lang), icon="⚖️")
else:
    shown = offers.assign(**{col: offers[col].map(lambda v: value(v, lang)) for col in ('side', 'RotoWire')})
    picked = table(shown, OVERVIEW_PROPS, {'line': '%g', 'side odds': '%.2f', 'p win %': '%.0f',
                                           'edge net pp': '%+.1f', 'ev net 100': '%+.1f'},
                   key='top_props', select=True)
    if picked is not None:
        r = offers.iloc[picked]
        st.session_state['props_focus'] = (r['event_id'], r['name_ESPN'], r['bet_type'])
        st.switch_page(PAGES['props'])

# --- tonight's ratings: the 4★ (and 3★) lines, shown with what they cost ---
st.subheader(t('overview.shortlist', lang), help=t('overview.shortlist_help', lang))
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
    st.caption(t('overview.shortlist_cost', lang, top=top['ev net 100'].mean(), every=props['ev net 100'].mean()))
    if len(top) and (top['ev net 100'] < 0).all():
        st.caption(t('overview.shortlist_negative', lang))
    record = star_scorecard(shortlist_record()).set_index('stars') if len(shortlist_record()) else None
    if record is not None and record.loc[4, 'bets']:
        top_record = record.loc[4]
        st.caption(t('overview.shortlist_record', lang, nights=int(top_record['nights']), bets=int(top_record['bets']),
                     hit=top_record['hit %'], price=top_record['price said %'], roi=top_record['ROI % std'],
                     every=record.loc['every line', 'ROI % std']))
    rest = best[best['star count'] == 3].reset_index(drop=True)
    if len(rest):
        with st.expander(t('overview.shortlist_more', lang, n=len(rest))):
            more = table(rest, SHORTLIST, formats, key='shortlist_look', select=True)
        picked_row = rest.iloc[more] if more is not None else None
    else:
        picked_row = None
    if picked is not None:
        picked_row = top.iloc[picked]
    if picked_row is not None:
        st.session_state['props_focus'] = (picked_row['event_id'], picked_row['name_ESPN'], picked_row['bet_type'])
        st.switch_page(PAGES['props'])
