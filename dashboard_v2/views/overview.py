import pandas as pd
import streamlit as st

from core.data import game_odds, player_decisions, priced_props, shortlist_record, superbet
from decisions import CZEKAJ, actionable, offers_table, star_text, stars
from tracking import star_scorecard
from core.columns import OVERVIEW_PROPS, SHORTLIST
from core.state import language
from core import cards
from core.ui import PAGES, kpis, no_offers, page_header, pl_time, table
from models import calibration_warning
import night_view
from i18n import t, value

# tonight's picks and last night; the research blocks (break-even, look-back, news window, big chances,
# curiosities, streaks) are on the Research page (research.py)
lang = language()
seasons, season_types = page_header(t('overview.title', lang), t('overview.purpose', lang), with_scope=True)


def focus(event_id, name_espn, bet_type):
    """Open that line on Props."""
    st.session_state['props_focus'] = (event_id, name_espn, bet_type)
    st.switch_page(PAGES['props'])


CARD_COLUMNS = 2


def pick_cards(top: pd.DataFrame):
    """The 4★ lines as bordered cards (core.cards), CARD_COLUMNS a row; returns the position of the card whose
    button was pressed, or None."""
    picked = None
    for start in range(0, len(top), CARD_COLUMNS):
        cols = st.columns(CARD_COLUMNS)
        for col, (i, r) in zip(cols, top.iloc[start:start + CARD_COLUMNS].iterrows()):
            c = cards.card(r, lang, tip=r['tip-off'])
            with col.container(border=True):
                st.markdown(f"{r['stars']} **{c['title']}**")
                for line in c['lines']:
                    st.caption(line)
                if st.button(t('card.open', lang), key=f"card_{i}", icon="🎯"):
                    picked = i
    return picked


def last_night_stars(record: pd.DataFrame):
    """The newest fully settled night's 4★ lines: {'won', 'n', 'price'} (price = the wins the margin-free price
    expected), or None."""
    if record is None or record.empty:
        return None
    top = record[record['stars'] == 4]
    nights = top.groupby('game_date')['status'].apply(lambda s: not s.eq('pending').any())
    nights = nights[nights]
    if nights.empty:
        return None
    last = top[top['game_date'] == nights.index.max()]
    decided = last[last['result'].isin(['win', 'loss'])]
    if decided.empty:
        return None
    return {'won': int((decided['result'] == 'win').sum()), 'n': len(decided),
            'price': decided['side market %'].sum() / 100}


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

    # tonight's ratings: the 4★ lines as cards, then what they cost and their record; the 3★ in a table
    st.markdown(f"**{t('overview.picks', lang)}**", help=t('overview.shortlist_help', lang))
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
        picked = pick_cards(top)
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
        if (last := last_night_stars(shortlist_record())) is not None:
            st.caption(t('overview.last_night_stars', lang, **last))
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


st.page_link(PAGES['research'], label=t('overview.research_link', lang), icon="🔬")
