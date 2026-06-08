"""Stockpeers-style **Dimensions** view (iteration 5).

Replaces the previous `st.tabs` layout with a 3×2 thumbnail grid (one cell
per macro dimension: Debt, Energy, Taxation, FDI, Household savings, Health
spending). Each thumbnail shows a bolded title, a one-line "Leader" stat, a
compact Plotly sparkline, and a *View details* button.

Clicking a button stores the dimension key in ``st.session_state["dim_open"]``
and triggers a rerun; the expanded detail view (KPI row, full-size line +
bar charts, pivot table) then renders below the grid with a *← Back to grid*
control.

Public API (must remain stable — ``frontend/app.py`` calls this signature):

    render_dimension_tabs(chosen: list[str], year_range: tuple[int, int] | None = None) -> None
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from charts import COUNTRY_COLORS, bar_chart, line_chart  # noqa: E402
from data_client import (  # noqa: E402
    COUNTRY_META,
    INDICATORS,
    get_indicator_timeseries,
    latest_value_per_country,
    rank_countries,
)

# Dimension key → (emoji + title shown in the thumbnail header).
# Order is the visual order in the 3×2 grid (row-major).
DIMENSIONS: list[tuple[str, str]] = [
    ("debt", "💰 Debt"),
    ("energy", "⚡ Energy"),
    ("tax", "🧾 Taxation"),
    ("fdi", "🌍 FDI"),
    ("savings", "🏠 Household savings"),
    ("health", "🩺 Health spending"),
]

DEFAULT_YEAR_RANGE: tuple[int, int] = (2015, 2024)


# ---------------------------------------------------------------------------
# Mini chart for thumbnail cells
# ---------------------------------------------------------------------------

def _mini_line_chart(df: pd.DataFrame) -> go.Figure:
    """Compact sparkline used inside thumbnail cells (height=180, chromeless).

    Keeps hover but hides axes, legend, and the Plotly toolbar so the cell
    reads as a thumbnail rather than a full chart.
    """
    if df is None or df.empty:
        fig = go.Figure()
        fig.update_layout(
            height=180,
            margin=dict(l=8, r=8, t=8, b=8),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis_visible=False,
            yaxis_visible=False,
            showlegend=False,
        )
        return fig

    fig = px.line(
        df,
        x="year",
        y="value",
        color="iso3",
        color_discrete_map=COUNTRY_COLORS,
    )
    fig.update_traces(line=dict(width=2.0), hovertemplate="%{x}: %{y:.2f}<extra>%{fullData.name}</extra>")
    fig.update_layout(
        height=180,
        margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(248, 250, 252, 0.4)",
        xaxis_visible=False,
        yaxis_visible=False,
        showlegend=False,
        hovermode="x unified",
    )
    return fig


# ---------------------------------------------------------------------------
# Leader stat ("Leader: 🇺🇸 USA 28.8 T$")
# ---------------------------------------------------------------------------

def _leader_caption(ranked: pd.DataFrame, unit: str) -> str:
    if ranked is None or ranked.empty:
        return "Leader: —"
    top = ranked.iloc[0]
    iso3 = str(top["iso3"])
    flag = COUNTRY_META.get(iso3, {}).get("flag", "")
    try:
        value_str = f"{float(top['value']):.2f} {unit}"
    except (TypeError, ValueError):
        value_str = "—"
    return f"Leader: {flag} {iso3} {value_str}".strip()


# ---------------------------------------------------------------------------
# Thumbnail cell
# ---------------------------------------------------------------------------

def _render_thumbnail(dim_key: str, title: str, chosen: list[str], year_range: tuple[int, int]) -> None:
    meta = INDICATORS[dim_key]
    df = get_indicator_timeseries(
        chosen, dim_key, year_start=year_range[0], year_end=year_range[1]
    )

    with st.container(border=True):
        st.markdown(f"**{title}**")

        if df is None or df.empty:
            st.caption("No data")
            st.markdown(
                "<div style='height:180px;display:flex;align-items:center;"
                "justify-content:center;color:#94a3b8;font-size:0.85rem;'>"
                "No data for this dimension</div>",
                unsafe_allow_html=True,
            )
        else:
            latest = latest_value_per_country(df)
            ranked = rank_countries(latest, ascending=False)
            st.caption(_leader_caption(ranked, meta["unit"]))
            st.plotly_chart(
                _mini_line_chart(df),
                use_container_width=True,
                config={"displayModeBar": False},
                key=f"mini_{dim_key}",
            )

        if st.button("View details", key=f"open_{dim_key}", use_container_width=True):
            st.session_state["dim_open"] = dim_key
            st.rerun()


# ---------------------------------------------------------------------------
# Expanded detail view (rendered below the grid when a thumbnail is opened)
# ---------------------------------------------------------------------------

def _render_detail(dim_key: str, chosen: list[str], year_range: tuple[int, int]) -> None:
    meta = INDICATORS[dim_key]
    title = next((t for k, t in DIMENSIONS if k == dim_key), meta["label"])

    df = get_indicator_timeseries(
        chosen, dim_key, year_start=year_range[0], year_end=year_range[1]
    )

    st.markdown("---")
    header_col, back_col = st.columns([5, 1])
    with header_col:
        st.markdown(f"## {title}")
    with back_col:
        if st.button("← Back to grid", key="dim_back", use_container_width=True):
            st.session_state.pop("dim_open", None)
            st.rerun()

    if df is None or df.empty:
        st.info(f"No data available for {meta['label']}.")
        return

    source_tag = df["source"].mode().iloc[0] if "source" in df.columns else "—"
    st.caption(
        f"source: `{source_tag}` · unit: `{meta['unit']}` · "
        f"countries: {len(chosen)} · years: {year_range[0]}–{year_range[1]}"
    )

    # KPI row: latest value + YoY + rank per country.
    latest = latest_value_per_country(df)
    ranked = rank_countries(latest, ascending=False)
    if not ranked.empty:
        cols = st.columns(len(ranked))
        for col, (_, row) in zip(cols, ranked.iterrows()):
            yoy = row["yoy_pct"]
            delta_str = f"{yoy:+.2f}% YoY" if yoy is not None else "—"
            with col:
                st.metric(
                    label=f"{row['country']}  ·  #{int(row['rank'])}",
                    value=f"{row['value']:.2f} {meta['unit']}",
                    delta=delta_str,
                )

    # Full-size charts side-by-side.
    line_fig = line_chart(df, meta["label"], meta["unit"])
    line_fig.update_layout(height=420)
    bar_fig = bar_chart(df, f"Latest {meta['label']}", meta["unit"])
    bar_fig.update_layout(height=420)

    line_col, bar_col = st.columns([2, 1])
    with line_col:
        st.plotly_chart(line_fig, use_container_width=True, key=f"detail_line_{dim_key}")
    with bar_col:
        st.plotly_chart(bar_fig, use_container_width=True, key=f"detail_bar_{dim_key}")

    # Pivot data table (year × country).
    pivot = (
        df.pivot_table(index="year", columns="iso3", values="value", aggfunc="first")
        .sort_index()
    )
    st.markdown("**Year × country values**")
    st.dataframe(pivot, use_container_width=True)


# ---------------------------------------------------------------------------
# Public API — DO NOT change the signature; app.py calls this exact shape.
# ---------------------------------------------------------------------------

def render_dimension_tabs(chosen: list[str], year_range: tuple[int, int] | None = None) -> None:
    """Render the stockpeers-style thumbnail grid + optional detail view.

    Parameters
    ----------
    chosen
        ISO3 country codes selected in the sidebar.
    year_range
        Inclusive (start, end) year filter. Defaults to ``(2015, 2024)``.
    """
    if not chosen:
        st.warning("Select at least one country in the sidebar.")
        return

    years = year_range if year_range else DEFAULT_YEAR_RANGE

    st.markdown(
        "### Dimensions overview\n"
        "_Click any thumbnail to drill into a full-size detail view._"
    )

    # 3 columns × 2 rows = 6 dimension cells (row-major from ``DIMENSIONS``).
    for row_start in range(0, len(DIMENSIONS), 3):
        cols = st.columns(3)
        for col, (dim_key, title) in zip(cols, DIMENSIONS[row_start : row_start + 3]):
            with col:
                _render_thumbnail(dim_key, title, chosen, years)

    # Detail view (only when a thumbnail was opened).
    open_key = st.session_state.get("dim_open")
    if open_key and any(k == open_key for k, _ in DIMENSIONS):
        _render_detail(open_key, chosen, years)
