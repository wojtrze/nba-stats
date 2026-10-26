from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from core.data import game_odds, lineups as rotowire_lineups, priced_games, priced_props, superbet
from core.columns import OVERVIEW_PROPS
from core.state import language
from core.ui import PAGES, kpis, no_offers, page_header, pl_time, stop, table
from espn_scraper import NBA_TEAM_NAMES
from models import calibration_warning
from schedule import minutes_to, starts_soon
from superbet_fetcher import main_lines
from core.labels import describe_outcome, winner
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
main = pd.DataFrame(main_lines(odds.to_dict('records')))

kpis([{'label': t('overview.kpi.games', lang), 'value': odds['event_id'].nunique()},
      {'label': t('overview.kpi.lines', lang), 'value': len(props), 'help': t('overview.kpi.lines_help', lang)},
      {'label': t('overview.kpi.green', lang), 'value': int((props['signal'] == '🟢').sum()) if len(props) else 0,
       'help': t('overview.kpi.green_help', lang)},
      {'label': t('overview.kpi.yellow', lang), 'value': int((props['signal'] == '🟡').sum()) if len(props) else 0,
       'help': t('overview.kpi.yellow_help', lang)},
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
            st.caption(f"{pl_time(e['start_time'])} · " + t('overview.at', lang, away=NBA_TEAM_NAMES.get(e['away'], ''),
                                                            home=NBA_TEAM_NAMES.get(e['home'], '')))
            odds_text = " · ".join(filter(None, [
                f"{t('overview.ml', lang)} **{ml['away']:.2f}** / **{ml['home']:.2f}**"
                if {'away', 'home'} <= set(ml.index) else '',
                f"{e['home'].upper()} **{spread.iloc[0]:+g}**" if len(spread) else '',
                f"{t('overview.total', lang)} **{total.iloc[0]:g}**" if len(total) else '']))
            st.markdown(f"💰 {odds_text or t('overview.no_main', lang)}", help=t('overview.odds_help', lang))
            g = by_event.get(e['event_id'])
            if g:
                p = g['projection']
                best = g['edges'].loc[g['edges']['edge pp'].idxmax()]
                st.markdown(t('overview.projected', lang, winner=winner(p, g['home'], g['away']), total=p['total'])
                            + "  \n" + t('overview.best_price', lang, bet=describe_outcome(best), odds=best['odds'],
                                         edge=best['edge pp']))
            st.markdown(lineup_line(e['away']) + "  \n" + lineup_line(e['home']))

# --- the best bets ---
left, right = st.columns([3, 2])
with left:
    st.subheader(t('overview.best_props', lang))
    top = props[props['signal'].isin(['🟢', '🟡'])] if len(props) else props
    if props.empty:
        st.caption(t('overview.no_props', lang))
    elif top.empty:
        st.info(t('overview.no_edge', lang), icon="⚖️")
    else:
        top = top.sort_values(['signal', 'edge pp'], ascending=[True, False],
                              key=lambda c: c.map({'🟢': 0, '🟡': 1}) if c.name == 'signal' else c) \
            .head(10).reset_index(drop=True)
        shown = top.assign(**{col: top[col].map(lambda v: value(v, lang)) for col in ('bet', 'RotoWire')})
        picked = table(shown, OVERVIEW_PROPS, {'line': '%g', 'edge pp': '%+.1f', 'pick odds': '%.2f'},
                       key='top_props', select=True)
        st.caption(t('overview.best_props_caption', lang))
        if picked is not None:
            r = top.iloc[picked]
            st.session_state['props_focus'] = (r['event_id'], r['name_ESPN'], r['bet_type'])
            st.switch_page(PAGES['props'])
with right:
    st.subheader(t('overview.game_edges', lang))
    if not games:
        st.caption(t('overview.no_games', lang))
    else:
        edges = pd.concat([g['edges'].assign(game=f"{g['away'].upper()} @ {g['home'].upper()}") for g in games])
        top = edges.sort_values('edge pp', ascending=False).head(5).reset_index(drop=True)
        top['bet'] = [describe_outcome(r) for _, r in top.iterrows()]
        picked = table(top, ['game', 'bet', 'odds', 'edge pp'], {'odds': '%.2f', 'edge pp': '%+.1f'},
                       sources={'bet': None, 'odds': 'superbet'}, key='top_games', select=True, context='games')
        st.caption(t('overview.game_edges_caption', lang))
        if picked is not None:
            st.session_state['games_focus'] = top.iloc[picked]['event_id']
            st.switch_page(PAGES['games'])
