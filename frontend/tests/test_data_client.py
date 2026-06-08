"""Unit tests for ``frontend/data_client.py`` helpers.

These tests are network-free: they cover deterministic synthetic
generation, latest/YoY KPI helpers, and ranking. The HTTP client paths
(``check_health``, ``fetch_countries``, ``fetch_compare``) are exercised
indirectly via monkeypatched ``requests.get`` calls in
``test_backend_offline_fallback``.
"""
from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

import data_client
from data_client import (
    COUNTRY_META,
    INDICATORS,
    _synth_series,
    get_indicator_timeseries,
    latest_value_per_country,
    rank_countries,
)


def test_synth_series_is_deterministic() -> None:
    a = _synth_series("USA", "gdp", range(2015, 2025))
    b = _synth_series("USA", "gdp", range(2015, 2025))
    assert a == b
    assert len(a) == 10
    assert all(v >= 0.0 for v in a)


def test_synth_series_differs_per_country() -> None:
    usa = _synth_series("USA", "gdp", range(2015, 2025))
    chn = _synth_series("CHN", "gdp", range(2015, 2025))
    assert usa != chn  # different seeds → different drift


def test_get_indicator_timeseries_prefers_snapshot_when_backend_offline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With backend down but a bundled snapshot available, return real data."""
    def always_fail(*args: Any, **kwargs: Any) -> Any:
        raise data_client.requests.ConnectionError("offline")

    monkeypatch.setattr(data_client.requests, "get", always_fail)

    snap = data_client.load_snapshot()
    if not snap:
        pytest.skip("snapshot not built; run scripts/build_snapshot.py")

    df = get_indicator_timeseries(["USA", "CHN"], "gdp", 2018, 2022)
    assert not df.empty
    assert set(df.columns) >= {"year", "iso3", "country", "value", "indicator", "source"}
    assert set(df["iso3"].unique()) == {"USA", "CHN"}
    assert set(df["year"].unique()) == {2018, 2019, 2020, 2021, 2022}
    assert (df["source"] == "snapshot").all()


def test_get_indicator_timeseries_synthetic_when_no_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With both backend and snapshot unavailable, fall back to synthetic."""
    def always_fail(*args: Any, **kwargs: Any) -> Any:
        raise data_client.requests.ConnectionError("offline")

    monkeypatch.setattr(data_client.requests, "get", always_fail)
    # Disable snapshot for this test only.
    monkeypatch.setattr(data_client, "_SNAPSHOT_CACHE", None)
    monkeypatch.setattr(data_client, "load_snapshot", lambda: None)
    monkeypatch.setattr(data_client, "snapshot_rows_for", lambda *a, **k: [])

    df = get_indicator_timeseries(["USA", "CHN"], "gdp", 2018, 2022)
    assert not df.empty
    assert set(df["iso3"].unique()) == {"USA", "CHN"}
    assert set(df["year"].unique()) == {2018, 2019, 2020, 2021, 2022}
    assert (df["source"] == "synthetic").all()


def test_latest_value_per_country_computes_yoy() -> None:
    df = pd.DataFrame(
        [
            {"year": 2021, "iso3": "USA", "country": "US", "value": 100.0},
            {"year": 2022, "iso3": "USA", "country": "US", "value": 110.0},
            {"year": 2021, "iso3": "JPN", "country": "JP", "value": 50.0},
            {"year": 2022, "iso3": "JPN", "country": "JP", "value": 49.0},
        ]
    )
    out = latest_value_per_country(df).set_index("iso3")
    assert out.loc["USA", "value"] == 110.0
    assert out.loc["USA", "yoy_pct"] == pytest.approx(10.0)
    assert out.loc["JPN", "yoy_pct"] == pytest.approx(-2.0)


def test_latest_value_per_country_handles_single_year() -> None:
    df = pd.DataFrame(
        [
            {"year": 2022, "iso3": "USA", "country": "US", "value": 100.0},
        ]
    )
    out = latest_value_per_country(df).iloc[0]
    assert out["value"] == 100.0
    assert out["prev_value"] is None
    assert out["yoy_pct"] is None


def test_rank_countries_descending() -> None:
    latest = pd.DataFrame(
        [
            {"iso3": "USA", "country": "US", "year": 2022, "value": 100, "prev_value": 90, "yoy_pct": 11.1},
            {"iso3": "CHN", "country": "CN", "year": 2022, "value": 200, "prev_value": 180, "yoy_pct": 11.1},
            {"iso3": "JPN", "country": "JP", "year": 2022, "value": 50, "prev_value": 60, "yoy_pct": -16.7},
        ]
    )
    ranked = rank_countries(latest, ascending=False).set_index("iso3")
    assert int(ranked.loc["CHN", "rank"]) == 1
    assert int(ranked.loc["USA", "rank"]) == 2
    assert int(ranked.loc["JPN", "rank"]) == 3


def test_indicator_metadata_contains_required_keys() -> None:
    for key, meta in INDICATORS.items():
        assert "label" in meta
        assert "unit" in meta
        assert "code" in meta
    # Default supported countries cover the task's scope.
    assert set(COUNTRY_META.keys()) >= {"USA", "CHN", "JPN", "AUS", "CAN"}
