"""Stockpeers-style Overview tab for the country-comparison dashboard.

Layout:
  1. Peer cards grid     — one card per selected country (flag, name, latest GDP, YoY delta)
  2. Indicator pill bar  — st.radio to switch which indicator drives the hero chart
  3. Hero chart          — full-width line chart for the selected primary indicator
  4. 2x2 mini grid       — fixed secondary indicators (CPI, Unemployment, FDI, Health)

Public API:
    render_overview(chosen: list[str], year_range: tuple[int, int]) -> None

This is the only module that should be touched by the overview subagent;
``app.py`` swaps its current ``render_country_overview`` + ``render_comparison_charts``
calls for a single ``render_overview(chosen, year_range)``.
"""
from __future__ import annotations

from typing import Iterable

import pandas as pd
import streamlit as st

from charts import bar_chart, line_chart, mini_line_chart
from data_client import (
    COUNTRY_META,
    INDICATORS,
    get_indicator_timeseries,
    latest_value_per_country,
    rank_countries,
)

# Indicators surfaced by the indicator pill bar (the "hero" candidates).
HERO_INDICATOR_KEYS: list[str] = ["gdp", "cpi", "unemployment", "debt"]

# Fixed 2x2 grid of secondary indicators — independent of the hero choice.
MINI_GRID_KEYS: list[str] = ["cpi", "unemployment", "fdi", "health"]


# ---------------------------------------------------------------------------
# Pure helpers (covered by frontend/tests/test_overview_page.py)
# ---------------------------------------------------------------------------

def format_value(value: float | None, unit: str) -> str:
    """Format a KPI numeric value for a metric card.

    - GDP (``unit == "T$"``) is shown to two decimals with the unit suffix.
    - Other units are shown to two decimals with a leading unit/percent.
    - ``None`` collapses to an em-dash.
    """
    if value is None:
        return "—"
    if unit == "T$":
        return f"${value:.2f}T"
    if unit == "%":
        return f"{value:.2f}%"
    return f"{value:.2f} {unit}".strip()


def format_delta(yoy_pct: float | None) -> str:
    """Format a YoY% delta for ``st.metric``'s ``delta`` argument."""
    if yoy_pct is None:
        return "—"
    return f"{yoy_pct:+.2f}% YoY"


def leader_caption(df_latest: pd.DataFrame, unit: str) -> str:
    """Return a short ``'🇺🇸 USA leads · $24.50T'``-style caption.

    Picks the row with the highest ``value`` from a ranked-latest DataFrame.
    Returns an empty string if no data is available.
    """
    if df_latest is None or df_latest.empty:
        return ""
    # Sort defensively in case the caller did not.
    sorted_df = df_latest.sort_values("value", ascending=False)
    top = sorted_df.iloc[0]
    iso3 = str(top["iso3"])
    cmeta = COUNTRY_META.get(iso3, {"flag": "", "name": iso3})
    return f"{cmeta['flag']} {iso3} leads · {format_value(float(top['value']), unit)}"


def safe_indicator_label(indicator_key: str) -> str:
    """Return the human-readable label for an indicator key, with a fallback."""
    meta = INDICATORS.get(indicator_key)
    if meta is None:
        return indicator_key.upper()
    return meta["label"]


# ---------------------------------------------------------------------------
# Internal render helpers
# ---------------------------------------------------------------------------

def _render_peer_card(iso3: str, gdp_latest: pd.DataFrame) -> None:
    """Render one country card with flag, name, latest GDP, YoY delta."""
    cmeta = COUNTRY_META.get(iso3, {"name": iso3, "flag": "", "region": "—"})
    row = gdp_latest[gdp_latest["iso3"] == iso3]
    if row.empty:
        value = None
        yoy = None
        year = None
    else:
        r = row.iloc[0]
        value = float(r["value"])
        yoy = float(r["yoy_pct"]) if pd.notna(r["yoy_pct"]) else None
        year = int(r["year"]) if pd.notna(r["year"]) else None

    with st.container(border=True):
        st.markdown(
            f"<div style='font-size:0.95rem; color:#475569; margin-bottom:2px;'>"
            f"{cmeta['flag']} <b>{cmeta['name']}</b> "
            f"<span style='color:#94a3b8; font-size:0.8rem;'>({iso3})</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.metric(
            label=f"GDP · {year if year else '—'}",
            value=format_value(value, INDICATORS["gdp"]["unit"]),
            delta=format_delta(yoy),
        )


def _render_peer_cards(chosen: list[str], year_range: tuple[int, int]) -> None:
    """Top row: one peer card per country (flag, name, latest GDP, YoY delta)."""
    st.subheader("🏛️ Country peers")
    try:
        gdp_df = get_indicator_timeseries(chosen, "gdp", year_range[0], year_range[1])
    except Exception as exc:  # noqa: BLE001 — defensive UI boundary
        st.error(f"Failed to load GDP peer cards: {exc}")
        return

    gdp_latest = latest_value_per_country(gdp_df)
    if gdp_latest.empty:
        st.info("No GDP data available for the selected countries / year range.")
        return

    cols = st.columns(len(chosen))
    for col, iso3 in zip(cols, chosen):
        with col:
            _render_peer_card(iso3, gdp_latest)


def _render_indicator_picker(default_key: str = "gdp") -> str:
    """Horizontal pill bar to choose the hero-chart indicator. Returns the key."""
    options = HERO_INDICATOR_KEYS
    labels = [safe_indicator_label(k) for k in options]
    label_to_key = dict(zip(labels, options))
    default_label = safe_indicator_label(default_key)
    default_index = labels.index(default_label) if default_label in labels else 0
    chosen_label = st.radio(
        "Hero indicator",
        options=labels,
        index=default_index,
        horizontal=True,
        label_visibility="collapsed",
        key="overview_hero_indicator",
    )
    return label_to_key.get(chosen_label, default_key)


def _render_hero_chart(
    chosen: list[str],
    indicator_key: str,
    year_range: tuple[int, int],
) -> None:
    """Full-width hero line chart for the picked indicator."""
    meta = INDICATORS[indicator_key]
    try:
        df = get_indicator_timeseries(chosen, indicator_key, year_range[0], year_range[1])
    except Exception as exc:  # noqa: BLE001
        st.error(f"Failed to load {meta['label']}: {exc}")
        return

    source_tag = "—"
    if df is not None and not df.empty and "source" in df.columns:
        source_tag = df["source"].mode().iloc[0]

    st.markdown(
        f"### 📊 {meta['label']} "
        f"<span style='color:#94a3b8; font-size:0.85rem; font-weight:400;'>"
        f"· source: <code>{source_tag}</code> · unit: <code>{meta['unit']}</code>"
        f"</span>",
        unsafe_allow_html=True,
    )

    line_col, bar_col = st.columns([3, 1])
    with line_col:
        fig = line_chart(df, meta["label"], meta["unit"])
        fig.update_layout(height=420)
        st.plotly_chart(fig, use_container_width=True)
    with bar_col:
        bar = bar_chart(df, f"Latest {meta['label']}", meta["unit"])
        bar.update_layout(height=420, showlegend=False)
        st.plotly_chart(bar, use_container_width=True)


def _render_mini_cell(
    chosen: list[str],
    indicator_key: str,
    year_range: tuple[int, int],
) -> None:
    """One cell of the 2x2 secondary-indicator grid."""
    meta = INDICATORS[indicator_key]
    with st.container(border=True):
        try:
            df = get_indicator_timeseries(chosen, indicator_key, year_range[0], year_range[1])
        except Exception as exc:  # noqa: BLE001
            st.error(f"{meta['label']}: {exc}")
            return

        fig = mini_line_chart(df, meta["label"], meta["unit"])
        st.plotly_chart(fig, use_container_width=True)

        latest = latest_value_per_country(df)
        caption = leader_caption(latest, meta["unit"])
        if caption:
            st.caption(caption)


def _render_mini_grid(chosen: list[str], year_range: tuple[int, int]) -> None:
    """Fixed 2x2 grid of secondary indicators."""
    st.markdown("### 🧭 Secondary indicators")
    keys = MINI_GRID_KEYS

    row1 = st.columns(2)
    row2 = st.columns(2)
    cells = [row1[0], row1[1], row2[0], row2[1]]
    for cell, key in zip(cells, keys):
        with cell:
            _render_mini_cell(chosen, key, year_range)


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------

def render_overview(chosen: list[str], year_range: tuple[int, int]) -> None:
    """Render the stockpeers-style Overview tab.

    Args:
        chosen: ISO3 codes for the countries to compare (peer set).
        year_range: inclusive (start_year, end_year) window applied to every chart.
    """
    if not chosen:
        st.warning("Select at least one country in the sidebar to begin.")
        return

    # 1. Peer cards grid
    _render_peer_cards(chosen, year_range)

    st.divider()

    # 2. Indicator pill bar + 3. Hero chart
    hero_key = _render_indicator_picker(default_key="gdp")
    _render_hero_chart(chosen, hero_key, year_range)

    st.divider()

    # 4. 2x2 mini-chart grid (fixed indicators, independent of hero pick)
    _render_mini_grid(chosen, year_range)
