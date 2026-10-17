import pandas as pd
import plotly.express as px
import streamlit as st

from loaders import assessed_bets
from metrics import RULES, grouped_rates, rule_stats, vote_pattern

st.title("Rule backtest")
st.warning("This uses `assessed_bets.csv`: Unibet offers from Nov 2022 – Feb 2023, scored with bet_analyst.py's rules "
           "at the time. It shows whether the rules had an edge back then, not on today's Superbet lines.

"
           "Some rules show 70–85% hit rates at ~1.9 odds, which is too good to be true. That usually means the data "
           "leaks information from after the bet (e.g. lines offered close to or during the game, or `bets_hits` "
           "counting results that came later). Treat these numbers as an upper bound until offers are re-tested "
           "on clean data.", icon="⚠️")

bets = vote_pattern(assessed_bets())

# --- filters ---
f = st.columns(4)
dates = f[0].date_input("Closed between", (bets['closed_date'].min().date(), bets['closed_date'].max().date()))
types = f[1].multiselect("Bet types", sorted(bets['bet_type'].unique()))
side = f[2].multiselect("Side", ['Over', 'Under'])
odds = f[3].slider("Odds", 1.0, 4.5, (1.0, 4.5), 0.05)
mask = bets['odds'].between(*odds)
if len(dates) == 2:
    mask &= bets['closed_date'].dt.date.between(*dates)
if types:
    mask &= bets['bet_type'].isin(types)
if side:
    mask &= bets['over_under'].isin(side)
bets = bets[mask]
if bets.empty:
    st.info("No bets match the filters.")
    st.stop()

total = grouped_rates(bets.assign(all='all'), 'all').iloc[0]
breakeven = 100 / bets['odds'].mean()
m = st.columns(4)
m[0].metric("Bets", f"{int(total['bets']):,}")
m[1].metric("Hit rate (all)", f"{total['hit %']:.1f}%")
m[2].metric("Break-even at avg odds", f"{breakeven:.1f}%", help=f"100 / average odds ({bets['odds'].mean():.2f})")
m[3].metric("ROI betting everything", f"{total['ROI %']:+.1f}%")

# --- per rule ---
st.subheader("Each rule: following it vs going against it")
stats = rule_stats(bets)
fig = px.bar(stats, x='rule', y='hit %', color='vote', barmode='group', text=stats['bets'].map('{:,} bets'.format),
             error_y=stats['ci high %'] - stats['hit %'], error_y_minus=stats['hit %'] - stats['ci low %'],
             color_discrete_map={'agrees': '#2ca02c', 'disagrees': '#d62728'})
fig.add_hline(y=breakeven, line_dash='dash', annotation_text='break-even')
fig.update_layout(height=380, yaxis_range=[30, 70], margin=dict(t=20))
st.plotly_chart(fig, width='stretch')
st.caption("'agrees' = bets in the direction the rule voted. Error bars are 95% confidence intervals: "
           "if a bar's interval crosses the break-even line, the rule's edge isn't proven.")
st.dataframe(stats.round(1), hide_index=True, width='stretch')

# --- agreement ---
st.subheader("How many rules agree")
left, right = st.columns(2)
net = grouped_rates(bets, 'net')
fig = px.bar(net, x='net', y='hit %', text=net['bets'].map('{:,}'.format),
             labels={'net': 'rules agreeing minus rules against'})
fig.add_hline(y=breakeven, line_dash='dash')
fig.update_layout(height=320, yaxis_range=[30, 75], margin=dict(t=20))
left.plotly_chart(fig, width='stretch')
right.dataframe(grouped_rates(bets, ['agree', 'against']).round(1), hide_index=True, width='stretch', height=320)

# --- combinations ---
st.subheader("Rule combinations")
min_bets = st.slider("Minimum bets per combination", 10, 500, 50, 10)
combos = grouped_rates(bets, 'pattern', min_bets).sort_values('ci low %', ascending=False)
st.caption(f"{len(combos)} combinations with at least {min_bets} bets, sorted by the lower end of the 95% interval "
           f"(the most reliably good first). '+rule' = it voted for the bet's side, '-rule' = against.")
st.dataframe(combos.round(1), hide_index=True, width='stretch', height=400)

# --- bins ---
st.subheader("Hit rate by odds and by line vs actual")
b1, b2 = st.columns(2)
by_odds = grouped_rates(bets.assign(odds_bin=pd.cut(bets['odds'], [1, 1.6, 1.75, 1.85, 1.95, 2.05, 2.2, 2.5, 4.5]).astype(str)),
                        ['odds_bin', 'over_under'], 20)
fig = px.line(by_odds, x='odds_bin', y='hit %', color='over_under', markers=True)
breakeven_by_bin = by_odds.groupby('odds_bin', sort=False)['avg odds'].mean().rdiv(100)
fig.add_scatter(x=breakeven_by_bin.index, y=breakeven_by_bin.values, mode='lines', name='break-even',
                line=dict(dash='dash', color='grey'))
fig.update_layout(height=340, margin=dict(t=20), xaxis_title='odds')
b1.plotly_chart(fig, width='stretch')
by_type = grouped_rates(bets, ['bet_type', 'over_under'])
fig = px.bar(by_type, x='bet_type', y='hit %', color='over_under', barmode='group', text=by_type['bets'].map('{:,}'.format))
fig.add_hline(y=breakeven, line_dash='dash')
fig.update_layout(height=340, yaxis_range=[30, 70], margin=dict(t=20))
b2.plotly_chart(fig, width='stretch')
