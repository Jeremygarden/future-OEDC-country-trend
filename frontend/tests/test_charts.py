"""Unit tests for ``frontend/charts.py`` helpers.

These tests exercise the chart factory functions without rendering a
Streamlit app. They check that:
- the helpers always return a Plotly Figure (never raise),
- the empty-DataFrame path produces a labelled placeholder figure,
- the populated path uses the configured country color map,
- the bar chart collapses to one row per country (latest year only).
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from charts import COUNTRY_COLORS, bar_chart, line_chart


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"year": 2022, "iso3": "USA", "country": "United States", "value": 23.0},
            {"year": 2023, "iso3": "USA", "country": "United States", "value": 24.5},
            {"year": 2022, "iso3": "CHN", "country": "China", "value": 17.0},
            {"year": 2023, "iso3": "CHN", "country": "China", "value": 17.8},
        ]
    )


def test_line_chart_returns_figure_with_two_traces() -> None:
    fig = line_chart(_sample_df(), title="GDP", y_label="T$")
    assert isinstance(fig, go.Figure)
    # Two countries → two traces.
    assert len(fig.data) == 2
    iso_names = {trace.name for trace in fig.data}
    assert iso_names == {"USA", "CHN"}


def test_line_chart_uses_country_color_map() -> None:
    fig = line_chart(_sample_df(), title="GDP", y_label="T$")
    for trace in fig.data:
        expected = COUNTRY_COLORS.get(trace.name)
        assert expected is not None, f"unexpected trace name {trace.name}"
        # Plotly normalizes hex; compare case-insensitively.
        assert trace.line.color.lower() == expected.lower()


def test_line_chart_handles_empty_dataframe() -> None:
    fig = line_chart(pd.DataFrame(), title="GDP", y_label="T$")
    assert isinstance(fig, go.Figure)
    assert "no data" in (fig.layout.title.text or "").lower()


def test_bar_chart_collapses_to_latest_per_country() -> None:
    fig = bar_chart(_sample_df(), title="Latest GDP", y_label="T$")
    assert isinstance(fig, go.Figure)
    # ``px.bar(color=...)`` produces one trace per country. Flatten them.
    by_country: dict[str, float] = {}
    for trace in fig.data:
        for x, y in zip(trace.x, trace.y):
            by_country[str(x)] = float(y)
    assert sorted(by_country) == ["CHN", "USA"]
    # 2023 values: USA=24.5, CHN=17.8.
    assert by_country["USA"] == 24.5
    assert by_country["CHN"] == 17.8


def test_bar_chart_handles_empty_dataframe() -> None:
    fig = bar_chart(None, title="Latest GDP", y_label="T$")  # type: ignore[arg-type]
    assert isinstance(fig, go.Figure)
    assert "no data" in (fig.layout.title.text or "").lower()
