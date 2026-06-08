from __future__ import annotations

from pathlib import Path
from typing import Any
import sys

import pandas as pd
import streamlit as st

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from charts import line_chart, mini_line_chart
from data_client import (
    COUNTRY_META,
    DIMENSION_GROUPS,
    INDICATORS,
    format_value as dc_format_value,
    get_indicator_timeseries,
    latest_value_per_country,
)

HERO_INDICATOR_KEYS: list[str] = [
    key for group in DIMENSION_GROUPS for key in group.get("indicators", []) if key in INDICATORS
]
MINI_GRID_KEYS: list[str] = []


def format_value(value: float | None, unit: str) -> str:
    if value is None or pd.isna(value):
        return "—"
    if unit == "T$":
        return f"${float(value):.2f}T"
    if unit == "%":
        return f"{float(value):.2f}%"
    return f"{float(value):.2f} {unit}".strip()


def _fmt(indicator_key: str, value: float | None) -> str:
    return dc_format_value(indicator_key, value)


def format_delta(yoy_pct: float | None) -> str:
    if yoy_pct is None or pd.isna(yoy_pct):
        return "—"
    return f"{yoy_pct:+.2f}% YoY"


def leader_caption(df_latest: pd.DataFrame, unit: str) -> str:
    if df_latest is None or df_latest.empty:
        return ""
    leader = df_latest.sort_values("value", ascending=False).iloc[0]
    iso3 = str(leader["iso3"])
    return f"{iso3} leads · {format_value(float(leader['value']), unit)}"


def safe_indicator_label(indicator_key: str) -> str:
    return str(INDICATORS.get(indicator_key, {}).get("label", indicator_key.upper()))


def _group_options() -> tuple[list[str], dict[str, dict[str, Any]]]:
    groups = [g for g in DIMENSION_GROUPS if g.get("indicators")]
    by_label = {str(g["label"]): g for g in groups}
    return list(by_label.keys()), by_label


def _good_when_sort_ascending(indicator_key: str) -> bool:
    good_when = INDICATORS.get(indicator_key, {}).get("good_when", "neutral")
    return good_when == "low"


def _pick_leader(df_latest: pd.DataFrame, indicator_key: str) -> pd.Series | None:
    if df_latest is None or df_latest.empty:
        return None
    ascending = _good_when_sort_ascending(indicator_key)
    ranked = df_latest.sort_values("value", ascending=ascending)
    return ranked.iloc[0]


def _yoy_delta_text(yoy_pct: float | None) -> str:
    if yoy_pct is None or pd.isna(yoy_pct):
        return "—"
    arrow = "▲" if yoy_pct > 0 else ("▼" if yoy_pct < 0 else "●")
    return f"{arrow} {abs(float(yoy_pct)):.2f}% YoY"


def _peer_cards(chosen: list[str], year_range: tuple[int, int]) -> None:
    st.subheader("🏛️ Country peers")
    gdp_df = get_indicator_timeseries(chosen, "gdp", year_range[0], year_range[1])
    latest = latest_value_per_country(gdp_df)
    if latest.empty:
        st.info("No GDP data available for the selected countries / year range.")
        return

    cols = st.columns(len(chosen))
    for col, iso3 in zip(cols, chosen):
        with col:
            meta = COUNTRY_META.get(iso3, {"name": iso3, "flag": ""})
            row = latest[latest["iso3"] == iso3]
            value = None
            yoy = None
            if not row.empty:
                value = float(row.iloc[0]["value"])
                yoy = float(row.iloc[0]["yoy_pct"]) if pd.notna(row.iloc[0]["yoy_pct"]) else None
            st.metric(
                label=f"{meta.get('flag', '')} {meta.get('name', iso3)}",
                value=_fmt("gdp", value),
                delta=_yoy_delta_text(yoy),
            )


def _hero_picker() -> tuple[dict[str, Any], str]:
    group_labels, groups_by_label = _group_options()
    default_group_index = group_labels.index("Economy") if "Economy" in group_labels else 0

    selected_group_label = st.radio(
        "Indicator group",
        options=group_labels,
        index=default_group_index,
        horizontal=True,
        key="overview_group_radio",
    )
    selected_group = groups_by_label[selected_group_label]

    indicator_keys = [k for k in selected_group["indicators"] if k in INDICATORS]
    indicator_labels = [INDICATORS[k]["label"] for k in indicator_keys]
    selected_indicator_label = st.radio(
        "Indicator",
        options=indicator_labels,
        index=0,
        horizontal=True,
        key="overview_indicator_radio",
    )
    selected_indicator = indicator_keys[indicator_labels.index(selected_indicator_label)]
    return selected_group, selected_indicator


def _hero_chart(chosen: list[str], year_range: tuple[int, int], indicator_key: str) -> None:
    meta = INDICATORS[indicator_key]
    df = get_indicator_timeseries(chosen, indicator_key, year_range[0], year_range[1])
    fig = line_chart(df, meta["label"], meta["unit"])
    fig.update_layout(height=420)
    st.plotly_chart(fig, use_container_width=True)

    latest = latest_value_per_country(df)
    leader = _pick_leader(latest, indicator_key)
    if leader is None:
        st.caption("No latest-value delta available in this range.")
        return

    leader_iso3 = str(leader["iso3"])
    leader_meta = COUNTRY_META.get(leader_iso3, {"name": leader_iso3})
    latest_value = float(leader["value"])
    prev_value = float(leader["prev_value"]) if pd.notna(leader["prev_value"]) else None
    abs_delta = None if prev_value is None else (latest_value - prev_value)

    # KPI delta uses data_client.format_value to keep number formatting consistent.
    delta_text = "—" if abs_delta is None else (
        f"{('+' if abs_delta >= 0 else '')}{_fmt(indicator_key, abs_delta)} vs prev year"
    )
    st.metric(
        label=f"Leader: {leader_meta.get('name', leader_iso3)}",
        value=_fmt(indicator_key, latest_value),
        delta=delta_text,
    )


def _mini_keys_for_group(current_group_key: str, hero_indicator: str, target_cells: int = 6) -> list[str]:
    group_list = [g for g in DIMENSION_GROUPS if g.get("indicators")]
    idx = next((i for i, g in enumerate(group_list) if g.get("key") == current_group_key), 0)

    siblings = [k for k in group_list[idx]["indicators"] if k != hero_indicator and k in INDICATORS]
    picked: list[str] = list(siblings)

    # Fill to 6 cells by cycling through next groups in order, taking indicators in-group order.
    # This stays deterministic and keeps the hero's own group indicators first.
    g_off = 1
    while len(picked) < target_cells and g_off <= len(group_list):
        next_group = group_list[(idx + g_off) % len(group_list)]
        for key in next_group["indicators"]:
            if key in INDICATORS and key not in picked and key != hero_indicator:
                picked.append(key)
                if len(picked) >= target_cells:
                    break
        g_off += 1
    return picked[:target_cells]


def _mini_cell(chosen: list[str], year_range: tuple[int, int], indicator_key: str) -> None:
    meta = INDICATORS[indicator_key]
    with st.container(border=True):
        df = get_indicator_timeseries(chosen, indicator_key, year_range[0], year_range[1])
        fig = mini_line_chart(df, meta["label"], meta["unit"])
        fig.update_layout(height=180, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        latest = latest_value_per_country(df)
        leader = _pick_leader(latest, indicator_key)
        if leader is None:
            st.caption("No latest data")
            return
        leader_iso3 = str(leader["iso3"])
        leader_name = COUNTRY_META.get(leader_iso3, {"name": leader_iso3}).get("name", leader_iso3)
        st.caption(f"{leader_name} · {_fmt(indicator_key, float(leader['value']))}")


def _mini_grid(chosen: list[str], year_range: tuple[int, int], current_group_key: str, hero_indicator: str) -> None:
    st.markdown("### 📎 Related indicators")
    keys = _mini_keys_for_group(current_group_key, hero_indicator, target_cells=6)
    for row_start in range(0, 6, 3):
        cols = st.columns(3)
        for i, col in enumerate(cols):
            idx = row_start + i
            with col:
                if idx < len(keys):
                    _mini_cell(chosen, year_range, keys[idx])


def render_overview(chosen: list[str], year_range: tuple[int, int]) -> None:
    if not chosen:
        st.warning("Select at least one country in the sidebar to begin.")
        return

    _peer_cards(chosen, year_range)
    st.divider()

    selected_group, selected_indicator = _hero_picker()
    _hero_chart(chosen, year_range, selected_indicator)

    st.divider()
    _mini_grid(chosen, year_range, str(selected_group["key"]), selected_indicator)
