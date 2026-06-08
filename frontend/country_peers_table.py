"""Stockpeers-style country peer comparison table.

Renders one row per country with KPI columns and an inline sparkline column,
mirroring the layout shown in https://demo-stockpeers.streamlit.app .

The table is driven by ``streamlit.column_config`` so users can click column
headers to sort. The sparkline column uses ``LineChartColumn`` (requires
Streamlit >= 1.30; available in the project's pinned 1.41+).

Public API
----------
``render_country_peers_table(chosen, year_range)`` — drop-in replacement for
the parent app's old ``render_country_table()`` call.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from data_client import (  # noqa: E402
    COUNTRY_META,
    INDICATORS,
    get_indicator_timeseries,
)

# --------------------------------------------------------------------------- #
# Style constants
# --------------------------------------------------------------------------- #

# Green / red / neutral used for YoY arrows. Matches the stockpeers palette
# and is friendly to both light- and dark-mode Streamlit themes.
COLOR_UP = "#16a34a"
COLOR_DOWN = "#dc2626"
COLOR_FLAT = "#64748b"

# Default indicator that drives the sparkline column. The user can switch
# this with a horizontal ``st.radio`` rendered above the table.
DEFAULT_SPARK_INDICATOR = "gdp"

# Stable column order. The "Sparkline" column floats just after country
# metadata so the eye reads identity -> trend -> KPIs (matches stockpeers).
_KPI_KEYS: list[str] = list(INDICATORS.keys())


# --------------------------------------------------------------------------- #
# Formatting helpers (pure, easily unit-testable)
# --------------------------------------------------------------------------- #


def _missing() -> str:
    """Placeholder rendered for cells with no data."""
    return "—"


def format_value(indicator_key: str, value: float | None) -> str:
    """Format a single indicator value per the style rules.

    - ``gdp``           → ``"23.45 T$"`` (2 decimals, trillions)
    - ``energy``        → ``"6,800 kgoe"`` (thousands separator)
    - everything else   → ``"3.21%"`` (2 decimals, percent)
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return _missing()
    if indicator_key == "gdp":
        return f"{value:.2f} T$"
    if indicator_key == "energy":
        return f"{value:,.0f} kgoe"
    # Default: percent (cpi, unemployment, debt, tax, fdi, savings, health).
    return f"{value:.2f}%"


def format_yoy(yoy_pct: float | None) -> str:
    """Format a YoY percentage with a colored ▲/▼ arrow as inline HTML.

    Returns ``"—"`` when input is None/NaN. The returned string contains a
    ``<span style="color:...">`` so it must be rendered via ``st.markdown``
    (or any HTML-aware sink). It is intentionally NOT used inside
    ``st.dataframe`` cells, which only support plain text.
    """
    if yoy_pct is None or (isinstance(yoy_pct, float) and pd.isna(yoy_pct)):
        return _missing()
    if yoy_pct > 0:
        return f"<span style='color:{COLOR_UP}'>▲ {yoy_pct:+.2f}%</span>"
    if yoy_pct < 0:
        return f"<span style='color:{COLOR_DOWN}'>▼ {yoy_pct:+.2f}%</span>"
    return f"<span style='color:{COLOR_FLAT}'>● 0.00%</span>"


def format_cell(indicator_key: str, value: float | None, yoy_pct: float | None) -> str:
    """Combined "value + arrow + YoY%" string for one indicator cell.

    Uses plain-text arrows so the result is safe to drop straight into a
    ``st.dataframe`` ``TextColumn`` (which does not allow HTML).
    """
    val_str = format_value(indicator_key, value)
    if yoy_pct is None or (isinstance(yoy_pct, float) and pd.isna(yoy_pct)):
        arrow = ""
    elif yoy_pct > 0:
        arrow = f"  ▲ {yoy_pct:+.2f}%"
    elif yoy_pct < 0:
        arrow = f"  ▼ {yoy_pct:+.2f}%"
    else:
        arrow = "  ● 0.00%"
    return f"{val_str}{arrow}"


# --------------------------------------------------------------------------- #
# Data assembly
# --------------------------------------------------------------------------- #


def _series_for(
    iso3: str,
    indicator_key: str,
    year_range: tuple[int, int],
) -> pd.DataFrame:
    """One-country, one-indicator long DataFrame (year, value)."""
    return get_indicator_timeseries(
        [iso3], indicator_key, year_start=year_range[0], year_end=year_range[1]
    )


def _latest_and_yoy(df: pd.DataFrame) -> tuple[float | None, float | None, int | None]:
    """Pull the most-recent value plus a YoY % from a per-country series.

    Returns ``(latest_value, yoy_pct, latest_year)``; any field may be
    ``None`` when the underlying snapshot has gaps.
    """
    if df is None or df.empty:
        return None, None, None
    sorted_df = df.sort_values("year")
    latest_row = sorted_df.iloc[-1]
    latest_val = float(latest_row["value"])
    latest_year = int(latest_row["year"])
    if len(sorted_df) < 2:
        return latest_val, None, latest_year
    prev_val = float(sorted_df.iloc[-2]["value"])
    if prev_val == 0:
        return latest_val, None, latest_year
    yoy = ((latest_val - prev_val) / abs(prev_val)) * 100.0
    return latest_val, round(yoy, 2), latest_year


def build_peers_dataframe(
    chosen: list[str],
    year_range: tuple[int, int],
    spark_indicator: str = DEFAULT_SPARK_INDICATOR,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Assemble the wide peer table plus the long-format snapshot view.

    Returns
    -------
    (wide_df, long_df)
        ``wide_df`` — one row per country, columns:
            ``Country`` (str, "🇺🇸 United States"),
            ``Region`` (str),
            ``Sparkline`` (list[float] for ``LineChartColumn``),
            ``GDP``, ``CPI``, ``Unemployment``, … (pre-formatted strings).
        ``long_df`` — full snapshot rows for the expander; columns:
            ``year, iso3, country, indicator, value, source``.
    """
    long_records: list[dict[str, Any]] = []
    wide_records: list[dict[str, Any]] = []

    for iso3 in chosen:
        meta = COUNTRY_META.get(iso3, {"name": iso3, "flag": "", "region": "—"})
        row: dict[str, Any] = {
            "Country": f"{meta['flag']} {meta['name']}",
            "Region": meta.get("region", "—"),
        }

        # Sparkline column — values for the user-picked indicator across the
        # selected year window. Streamlit's LineChartColumn expects a
        # list-like of numbers per cell.
        spark_df = _series_for(iso3, spark_indicator, year_range)
        if spark_df is not None and not spark_df.empty:
            spark_values = spark_df.sort_values("year")["value"].astype(float).tolist()
        else:
            spark_values = []
        row["Sparkline"] = spark_values

        # KPI columns — latest value + YoY for every indicator.
        for key in _KPI_KEYS:
            label = INDICATORS[key]["label"].split(" (")[0]  # e.g. "GDP"
            ind_df = _series_for(iso3, key, year_range)
            val, yoy, _year = _latest_and_yoy(ind_df)
            row[label] = format_cell(key, val, yoy)

            # Long-format dump for the expander below the table.
            if ind_df is not None and not ind_df.empty:
                long_records.extend(ind_df.to_dict("records"))

        wide_records.append(row)

    wide_df = pd.DataFrame(wide_records)
    long_df = pd.DataFrame(long_records)
    if not long_df.empty:
        long_df = long_df.sort_values(["iso3", "indicator", "year"]).reset_index(drop=True)
    return wide_df, long_df


# --------------------------------------------------------------------------- #
# Column config (Streamlit native sortable table)
# --------------------------------------------------------------------------- #


def _column_config(spark_indicator: str) -> dict[str, Any]:
    """Build the ``column_config`` mapping for ``st.dataframe``."""
    spark_meta = INDICATORS.get(spark_indicator, {"label": "Trend", "unit": ""})
    cfg: dict[str, Any] = {
        "Country": st.column_config.TextColumn(
            "Country",
            help="Flag + country name. Click to sort alphabetically.",
            width="medium",
        ),
        "Region": st.column_config.TextColumn(
            "Region",
            width="small",
        ),
        "Sparkline": st.column_config.LineChartColumn(
            f"Trend · {spark_meta['label']}",
            help=(
                f"Per-country trend of {spark_meta['label']} over the selected "
                "year range. Pick a different indicator with the radio above."
            ),
            width="medium",
        ),
    }
    # KPI text columns — sortable lexicographically (good enough for a peer
    # table; numeric sort within a single unit is preserved because we
    # zero-pad-free format with the same template).
    for key in _KPI_KEYS:
        label = INDICATORS[key]["label"].split(" (")[0]
        cfg[label] = st.column_config.TextColumn(
            label,
            help=f"{INDICATORS[key]['label']} — latest value + YoY change.",
            width="small",
        )
    return cfg


# --------------------------------------------------------------------------- #
# Streamlit render (public entrypoint)
# --------------------------------------------------------------------------- #


def render_country_peers_table(
    chosen: list[str],
    year_range: tuple[int, int],
) -> None:
    """Render the stockpeers-style peer comparison table.

    Drop-in replacement for the previous ``render_country_table()`` call in
    ``frontend/app.py``. Safe for an empty ``chosen`` selection (renders an
    informational placeholder instead of erroring).
    """
    if not chosen:
        st.info("Select at least one country in the sidebar to populate the table.")
        return

    st.subheader("📋 Country peer comparison")
    st.caption(
        "Side-by-side macro snapshot for the selected countries. "
        "Each KPI cell shows the latest value plus YoY change "
        "(▲ green = up, ▼ red = down)."
    )

    # Indicator selector — drives the sparkline column only. Stored in
    # session state so the choice survives reruns from the sidebar.
    radio_options = list(INDICATORS.keys())
    radio_labels = {k: INDICATORS[k]["label"].split(" (")[0] for k in radio_options}
    default_index = (
        radio_options.index(DEFAULT_SPARK_INDICATOR)
        if DEFAULT_SPARK_INDICATOR in radio_options
        else 0
    )
    spark_indicator = st.radio(
        "Sparkline indicator",
        options=radio_options,
        index=default_index,
        format_func=lambda k: radio_labels[k],
        horizontal=True,
        key="peers_table_spark_indicator",
        help="Pick which indicator's trend is plotted in the Sparkline column.",
    )

    with st.spinner("Building peer table…"):
        try:
            wide_df, long_df = build_peers_dataframe(chosen, year_range, spark_indicator)
        except Exception as exc:  # noqa: BLE001 — defensive UI boundary
            st.error(f"Failed to build peer table: {exc}")
            return

    if wide_df.empty:
        st.info("No data available for the selected countries / year range.")
        return

    st.dataframe(
        wide_df,
        column_config=_column_config(spark_indicator),
        use_container_width=True,
        hide_index=True,
    )

    # Legend for the YoY arrows. Plain HTML via st.markdown so the colors
    # render. Keeps the dataframe cells pure-text (Streamlit's TextColumn
    # does not support inline HTML / colors).
    st.markdown(
        f"<small>YoY legend: "
        f"<span style='color:{COLOR_UP}'>▲ up</span> · "
        f"<span style='color:{COLOR_DOWN}'>▼ down</span> · "
        f"<span style='color:{COLOR_FLAT}'>● flat / no data</span>"
        f"</small>",
        unsafe_allow_html=True,
    )

    with st.expander("Raw data (long format)", expanded=False):
        if long_df.empty:
            st.info("No long-format rows for the current selection.")
        else:
            st.caption(
                f"{len(long_df):,} rows · {long_df['indicator'].nunique()} indicators "
                f"· {long_df['iso3'].nunique()} countries"
            )
            st.dataframe(
                long_df,
                use_container_width=True,
                hide_index=True,
            )


__all__ = [
    "render_country_peers_table",
    "build_peers_dataframe",
    "format_value",
    "format_yoy",
    "format_cell",
]
