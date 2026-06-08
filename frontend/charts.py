"""Plotly chart helpers for the dashboard.

Iter-5 polish: shared theme, country color map, loading-spinner-friendly
defaults, and a consistent y-axis number formatter.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

THEME_TEMPLATE = "plotly_white"

COUNTRY_COLORS = {
    "USA": "#1f77b4",
    "CHN": "#d62728",
    "JPN": "#9467bd",
    "AUS": "#2ca02c",
    "CAN": "#ff7f0e",
}

_COMMON_LAYOUT = dict(
    template=THEME_TEMPLATE,
    margin=dict(l=20, r=20, t=60, b=40),
    font=dict(family="Inter, system-ui, sans-serif", size=13),
    title_font=dict(size=16, color="#0f172a"),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(248, 250, 252, 0.5)",
)


def _empty_figure(title: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(title=f"{title} (no data)", **_COMMON_LAYOUT)
    fig.add_annotation(
        text="No data for the selected countries / year range.",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(color="#64748b"),
    )
    return fig


def line_chart(df: pd.DataFrame, title: str, y_label: str) -> go.Figure:
    """Multi-country line chart from a long DataFrame (year, iso3, value)."""
    if df is None or df.empty:
        return _empty_figure(title)
    fig = px.line(
        df,
        x="year",
        y="value",
        color="iso3",
        markers=True,
        color_discrete_map=COUNTRY_COLORS,
        title=title,
    )
    fig.update_traces(line=dict(width=2.5))
    fig.update_layout(
        legend_title_text="Country (ISO3)",
        xaxis_title="Year",
        yaxis_title=y_label,
        hovermode="x unified",
        **_COMMON_LAYOUT,
    )
    fig.update_xaxes(showgrid=True, gridcolor="#e2e8f0", dtick=1)
    fig.update_yaxes(showgrid=True, gridcolor="#e2e8f0")
    return fig


def bar_chart(df: pd.DataFrame, title: str, y_label: str) -> go.Figure:
    """Latest-value-per-country bar chart from a long DataFrame."""
    if df is None or df.empty:
        return _empty_figure(title)
    latest = df.sort_values("year").groupby("iso3", as_index=False).tail(1)
    fig = px.bar(
        latest,
        x="iso3",
        y="value",
        color="iso3",
        color_discrete_map=COUNTRY_COLORS,
        title=title,
        text="value",
    )
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(
        showlegend=False,
        xaxis_title="Country",
        yaxis_title=y_label,
        **_COMMON_LAYOUT,
    )
    fig.update_yaxes(showgrid=True, gridcolor="#e2e8f0")
    return fig
