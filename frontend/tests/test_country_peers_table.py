"""Unit tests for ``frontend/country_peers_table.py``.

These tests exercise the pure helpers and the wide-DataFrame builder
without rendering Streamlit. The Streamlit render entrypoint is covered
indirectly via the import + the build_peers_dataframe contract; the
Streamlit-specific UI bits (column_config, radio) are smoke-imported.
"""
from __future__ import annotations

import math

import pandas as pd

from country_peers_table import (
    DEFAULT_SPARK_INDICATOR,
    build_peers_dataframe,
    format_cell,
    format_value,
    format_yoy,
)
from data_client import COUNTRY_META, INDICATORS


# --------------------------------------------------------------------------- #
# Formatting helpers
# --------------------------------------------------------------------------- #


def test_format_value_gdp_uses_trillions_suffix() -> None:
    assert format_value("gdp", 23.4567) == "23.46 T$"


def test_format_value_energy_uses_thousands_separator() -> None:
    assert format_value("energy", 6800.4) == "6,800 kgoe"


def test_format_value_percent_default() -> None:
    # cpi/unemployment/debt/tax/fdi/savings/health all share the % template.
    assert format_value("cpi", 3.21) == "3.21%"
    assert format_value("unemployment", 4.0) == "4.00%"
    assert format_value("health", 17.5) == "17.50%"


def test_format_value_missing_returns_dash() -> None:
    assert format_value("gdp", None) == "—"
    assert format_value("cpi", float("nan")) == "—"


def test_format_yoy_colors() -> None:
    up = format_yoy(2.31)
    down = format_yoy(-1.22)
    flat = format_yoy(0.0)
    missing = format_yoy(None)

    assert "▲" in up and "#16a34a" in up and "+2.31%" in up
    assert "▼" in down and "#dc2626" in down and "-1.22%" in down
    assert "#64748b" in flat
    assert missing == "—"


def test_format_cell_combines_value_and_arrow() -> None:
    assert format_cell("gdp", 23.4, 2.31) == "23.40 T$  ▲ +2.31%"
    assert format_cell("cpi", 3.0, -1.5) == "3.00%  ▼ -1.50%"
    assert format_cell("gdp", 23.4, None) == "23.40 T$"
    assert format_cell("gdp", None, None) == "—"


# --------------------------------------------------------------------------- #
# DataFrame builder
# --------------------------------------------------------------------------- #


def test_build_peers_dataframe_shape_for_two_countries() -> None:
    wide, long = build_peers_dataframe(["USA", "JPN"], (2018, 2024))

    # Two rows — one per chosen country, in input order.
    assert list(wide["Country"]) == [
        f"{COUNTRY_META['USA']['flag']} United States",
        f"{COUNTRY_META['JPN']['flag']} Japan",
    ]
    # All expected indicator columns are present (labels without unit suffix).
    expected_cols = {INDICATORS[k]["label"].split(" (")[0] for k in INDICATORS}
    assert expected_cols.issubset(set(wide.columns))
    # Region and Sparkline columns wired up.
    assert "Region" in wide.columns and "Sparkline" in wide.columns
    # Sparkline cell is a list (per LineChartColumn contract).
    assert isinstance(wide["Sparkline"].iloc[0], list)
    # Long format is non-empty and carries the snapshot columns.
    assert not long.empty
    assert {"year", "iso3", "value", "indicator"}.issubset(set(long.columns))


def test_build_peers_dataframe_sparkline_respects_year_range() -> None:
    wide, _ = build_peers_dataframe(["USA"], (2020, 2024), spark_indicator="gdp")
    spark = wide["Sparkline"].iloc[0]
    assert isinstance(spark, list)
    # 2020..2024 inclusive == at most 5 points (snapshot may have gaps but
    # never more than the window width).
    assert 0 < len(spark) <= 5
    assert all(isinstance(v, float) for v in spark)


def test_build_peers_dataframe_handles_empty_chosen() -> None:
    wide, long = build_peers_dataframe([], (2015, 2024))
    assert wide.empty
    assert long.empty


def test_build_peers_dataframe_cells_render_with_expected_units() -> None:
    wide, _ = build_peers_dataframe(["USA"], (2018, 2024))
    row = wide.iloc[0]
    # GDP cell uses trillions suffix; either "T$" string or "—" placeholder.
    gdp_cell = row["GDP"]
    assert gdp_cell == "—" or "T$" in gdp_cell
    # CPI inflation rendered as %.
    cpi_cell = row["CPI inflation"]
    assert cpi_cell == "—" or "%" in cpi_cell


def test_default_spark_indicator_is_known() -> None:
    assert DEFAULT_SPARK_INDICATOR in INDICATORS


# --------------------------------------------------------------------------- #
# Smoke import for the Streamlit entrypoint
# --------------------------------------------------------------------------- #


def test_render_entrypoint_is_importable_and_callable() -> None:
    # The entrypoint touches st.* APIs so we don't *call* it here — just
    # confirm the symbol exists and is a callable so the parent app can
    # bind to it.
    from country_peers_table import render_country_peers_table

    assert callable(render_country_peers_table)


def test_no_nan_leaks_into_value_format() -> None:
    # Defence against pd.NA / np.nan slipping past the "—" placeholder.
    assert format_value("gdp", math.nan) == "—"
    assert format_value("cpi", math.nan) == "—"
