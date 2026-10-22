"""Plotly charts shared by the v2 pages, in one consistent style: over the line = green, under = red, the line
dashed, averages orange."""
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

OVER, UNDER, PUSH, NEUTRAL, AVERAGE = '#16a34a', '#dc2626', '#9aa5b1', '#3b82f6', '#f59e0b'


def layout(fig: go.Figure, height: int, title: str = '', **kw):
    # the legend sits on the plot's top edge, below the title (which gets its own band of the margin)
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=70 if title else 30, b=10), title=title,
                      legend=dict(orientation='h', y=1.0, yanchor='bottom', x=0), **kw)
    return fig


def show(fig: go.Figure, key: Optional[str] = None):
    st.plotly_chart(fig, width='stretch', key=key, config={'displayModeBar': False})


def game_log(games: pd.DataFrame, stat: str, line: Optional[float] = None, last: Optional[int] = None,
             minutes: bool = False, title: str = '') -> go.Figure:
    """Bars per game (green over / red under the line; blue without a line, faded for preseason), with the
    5- and 10-game rolling averages and optionally minutes on a second axis."""
    g = games.tail(last) if last else games
    x = g['game_label'] + ' ' + g['Date'].dt.strftime('%y')
    if line is not None:
        colours = np.where(g[stat] > line, OVER, np.where(g[stat] < line, UNDER, PUSH))
    else:
        colours = np.where(g['season_type'] == 'pre', '#93c5fd', NEUTRAL)
    fig = go.Figure()
    fig.add_bar(x=x, y=g[stat], marker_color=colours, name=stat,
                customdata=np.stack([g['Result'], g['MIN'].round(0), g['season_type']], axis=1),
                hovertemplate=f"%{{x}}<br>{stat}: %{{y}}<br>%{{customdata[0]}} · %{{customdata[1]}} min · "
                              f"%{{customdata[2]}}<extra></extra>")
    for n, dash in ((5, 'solid'), (10, 'dot')):
        avg = games[stat].rolling(n, min_periods=1).mean().loc[g.index]
        fig.add_scatter(x=x, y=avg, mode='lines', name=f"{n}-game avg", line=dict(color=AVERAGE, dash=dash))
    if minutes:
        fig.add_scatter(x=x, y=g['MIN'], mode='lines+markers', name='minutes', yaxis='y2',
                        line=dict(color='#94a3b8', width=1), marker=dict(size=4))
        fig.update_layout(yaxis2=dict(overlaying='y', side='right', title='min', showgrid=False))
    if line is not None:
        fig.add_hline(y=line, line_dash='dash', line_color='#64748b', annotation_text=f"line {line:g}")
    return layout(fig, 360, title, xaxis=dict(type='category', tickangle=-50), yaxis=dict(title=stat))


def distribution(values: pd.Series, stat: str, line: Optional[float] = None, title: str = '') -> go.Figure:
    """How often each result happened, with the line and the average."""
    fig = go.Figure()
    counts = values.round(0).value_counts().sort_index()
    colours = [OVER if line is not None and v > line else UNDER if line is not None and v < line else NEUTRAL
               for v in counts.index]
    fig.add_bar(x=counts.index, y=counts.values, marker_color=colours, name='games',
                hovertemplate=f"{stat} %{{x}}: %{{y}} games<extra></extra>")
    fig.add_vline(x=values.mean(), line_color=AVERAGE, annotation_text=f"avg {values.mean():.1f}",
                  annotation_position='top left')
    if line is not None:
        fig.add_vline(x=line, line_dash='dash', line_color='#64748b', annotation_text=f"line {line:g}")
    return layout(fig, 300, title, xaxis=dict(title=stat), yaxis=dict(title='games'), bargap=0.15)


def change_bars(df: pd.DataFrame, label: str, value: str, highlight: Optional[str] = None, hover: str = '',
                title: str = '') -> go.Figure:
    """Horizontal bars of a change (+ green, − red); rows where `highlight` is true get a dark outline."""
    df = df.iloc[::-1]
    colours = np.where(df[value] > 0, OVER, UNDER)
    outline = np.where(df[highlight], 3, 0) if highlight else 0
    fig = go.Figure(go.Bar(x=df[value], y=df[label], orientation='h', marker_color=colours,
                           marker_line=dict(width=outline, color='#0f172a'), text=df[value].map('{:+.1f}'.format),
                           textposition='outside', hovertext=df[hover] if hover else None,
                           hoverinfo='text' if hover else None))
    fig.add_vline(x=0, line_color='#64748b')
    return layout(fig, 60 + 32 * len(df), title, xaxis=dict(title='change'))
