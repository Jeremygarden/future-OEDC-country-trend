"""Plotly chart helpers for the dashboard."""
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


def line_chart(df: pd.DataFrame, title: str, y_label: str) -> go.Figure:
    """Multi-country line chart from a long DataFrame (year, iso3, value)."""
    if df is None or df.empty:
        fig = go.Figure()
        fig.update_layout(template=THEME_TEMPLATE, title=f"{title} (no data)")
        return fig
    fig = px.line(
        df,
        x="year",
        y="value",
        color="iso3",
        markers=True,
        color_discrete_map=COUNTRY_COLORS,
        template=THEME_TEMPLATE,
        title=title,
    )
    fig.update_layout(
        legend_title_text="Country (ISO3)",
        xaxis_title="Year",
        yaxis_title=y_label,
        hovermode="x unified",
        margin=dict(l=20, r=20, t=60, b=40),
    )
    return fig


def bar_chart(df: pd.DataFrame, title: str, y_label: str) -> go.Figure:
    """Latest-value-per-country bar chart from a long DataFrame."""
    if df is None or df.empty:
        fig = go.Figure()
        fig.update_layout(template=THEME_TEMPLATE, title=f"{title} (no data)")
        return fig
    latest = df.sort_values("year").groupby("iso3", as_index=False).tail(1)
    fig = px.bar(
        latest,
        x="iso3",
        y="value",
        color="iso3",
        color_discrete_map=COUNTRY_COLORS,
        template=THEME_TEMPLATE,
        title=title,
        text="value",
    )
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(
        showlegend=False,
        xaxis_title="Country",
        yaxis_title=y_label,
        margin=dict(l=20, r=20, t=60, b=40),
    )
    return fig
