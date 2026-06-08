"""Unit tests for ``frontend/overview_page.py`` pure helpers and ``mini_line_chart``.

The Streamlit render functions can only be exercised inside the Streamlit
runtime, so this module tests only the pure helpers — the same pattern
already used by ``test_charts.py``.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from charts import COUNTRY_COLORS, mini_line_chart
from overview_page import (
    HERO_INDICATOR_KEYS,
    MINI_GRID_KEYS,
    format_delta,
    format_value,
    leader_caption,
    render_overview,
    safe_indicator_label,
)


def _sample_latest_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"iso3": "USA", "country": "United States", "year": 2023, "value": 24.5, "prev_value": 23.0, "yoy_pct": 6.52},
            {"iso3": "CHN", "country": "China", "year": 2023, "value": 17.8, "prev_value": 17.0, "yoy_pct": 4.71},
            {"iso3": "JPN", "country": "Japan", "year": 2023, "value": 4.2, "prev_value": 4.4, "yoy_pct": -4.55},
        ]
    )


def _sample_series_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"year": 2021, "iso3": "USA", "country": "United States", "value": 22.0},
            {"year": 2022, "iso3": "USA", "country": "United States", "value": 23.0},
            {"year": 2023, "iso3": "USA", "country": "United States", "value": 24.5},
            {"year": 2021, "iso3": "CHN", "country": "China", "value": 16.0},
            {"year": 2022, "iso3": "CHN", "country": "China", "value": 17.0},
            {"year": 2023, "iso3": "CHN", "country": "China", "value": 17.8},
        ]
    )


# ---------------------------------------------------------------------------
# Public API surface
# ---------------------------------------------------------------------------

def test_render_overview_is_exported_callable() -> None:
    assert callable(render_overview)


def test_hero_and_mini_indicator_keys_are_known() -> None:
    from data_client import INDICATORS

    for key in HERO_INDICATOR_KEYS:
        assert key in INDICATORS, f"{key!r} missing from INDICATORS"
    for key in MINI_GRID_KEYS:
        assert key in INDICATORS, f"{key!r} missing from INDICATORS"


# ---------------------------------------------------------------------------
# format_value
# ---------------------------------------------------------------------------

def test_format_value_handles_none() -> None:
    assert format_value(None, "T$") == "—"
    assert format_value(None, "%") == "—"


def test_format_value_gdp_uses_dollar_T_suffix() -> None:
    assert format_value(24.5, "T$") == "$24.50T"


def test_format_value_percent() -> None:
    assert format_value(7.25, "%") == "7.25%"


def test_format_value_other_unit() -> None:
    assert format_value(6800.0, "kgoe") == "6800.00 kgoe"


# ---------------------------------------------------------------------------
# format_delta
# ---------------------------------------------------------------------------

def test_format_delta_none() -> None:
    assert format_delta(None) == "—"


def test_format_delta_positive_has_explicit_sign() -> None:
    assert format_delta(6.52) == "+6.52% YoY"


def test_format_delta_negative() -> None:
    assert format_delta(-4.55) == "-4.55% YoY"


# ---------------------------------------------------------------------------
# leader_caption
# ---------------------------------------------------------------------------

def test_leader_caption_picks_highest_value() -> None:
    caption = leader_caption(_sample_latest_df(), "T$")
    # USA at 24.5 beats CHN (17.8) and JPN (4.2).
    assert "USA" in caption
    assert "24.50" in caption
    assert "leads" in caption


def test_leader_caption_empty_returns_blank() -> None:
    assert leader_caption(pd.DataFrame(), "T$") == ""
    assert leader_caption(None, "T$") == ""  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# safe_indicator_label
# ---------------------------------------------------------------------------

def test_safe_indicator_label_known_key() -> None:
    from data_client import INDICATORS

    assert safe_indicator_label("gdp") == INDICATORS["gdp"]["label"]


def test_safe_indicator_label_unknown_falls_back_to_uppercase() -> None:
    assert safe_indicator_label("unknown_metric") == "UNKNOWN_METRIC"


# ---------------------------------------------------------------------------
# mini_line_chart (newly added to charts.py)
# ---------------------------------------------------------------------------

def test_mini_line_chart_returns_figure_with_two_traces() -> None:
    fig = mini_line_chart(_sample_series_df(), title="GDP mini", y_label="T$")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 2
    assert {trace.name for trace in fig.data} == {"USA", "CHN"}


def test_mini_line_chart_hides_legend_and_uses_small_height() -> None:
    fig = mini_line_chart(_sample_series_df(), title="GDP mini", y_label="T$")
    assert fig.layout.showlegend is False
    assert fig.layout.height == 200


def test_mini_line_chart_uses_country_color_map() -> None:
    fig = mini_line_chart(_sample_series_df(), title="GDP mini", y_label="T$")
    for trace in fig.data:
        assert trace.line.color == COUNTRY_COLORS[trace.name]


def test_mini_line_chart_empty_returns_placeholder_with_compact_layout() -> None:
    fig = mini_line_chart(pd.DataFrame(), title="GDP mini", y_label="T$")
    assert isinstance(fig, go.Figure)
    assert fig.layout.showlegend is False
    assert fig.layout.height == 200
