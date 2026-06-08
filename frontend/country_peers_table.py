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
    DIMENSION_GROUPS,
    INDICATORS,
    format_value as dc_format_value,
    get_indicator_timeseries,
)

COLOR_UP = "#16a34a"
COLOR_DOWN = "#dc2626"
COLOR_FLAT = "#64748b"

DEFAULT_SPARK_INDICATOR = "gdp"

GROUP_ABBR = {
    "economy": "E",
    "trade_finance": "T",
    "society": "S",
    "innovation_environment": "I",
}


def _indicator_to_group_abbr() -> dict[str, str]:
    out: dict[str, str] = {}
    for group in DIMENSION_GROUPS:
        abbr = GROUP_ABBR.get(str(group.get("key")), str(group.get("label", ""))[:1].upper())
        for key in group.get("indicators", []):
            out[str(key)] = abbr
    return out


def _base_label(indicator_key: str) -> str:
    return INDICATORS[indicator_key]["label"].split(" (")[0]


def _column_label(indicator_key: str) -> str:
    abbr = _indicator_to_group_abbr().get(indicator_key, "?")
    return f"{abbr} · {_base_label(indicator_key)}"


def format_value(indicator_key: str, value: float | None) -> str:
    if value is None or pd.isna(value):
        return "—"
    if indicator_key == "gdp":
        return f"{float(value):.2f} T$"
    if indicator_key == "energy":
        return f"{float(value):,.0f} kgoe"
    raw = dc_format_value(indicator_key, float(value))
    return raw.replace(" %", "%")


def _good_when(indicator_key: str) -> str:
    return str(INDICATORS.get(indicator_key, {}).get("good_when", "neutral"))


def _colored_arrow_html(indicator_key: str, yoy_pct: float | None) -> str:
    if yoy_pct is None or pd.isna(yoy_pct):
        return ""

    direction_up = yoy_pct > 0
    direction_down = yoy_pct < 0
    if not (direction_up or direction_down):
        return f"<span style='color:{COLOR_FLAT}'>● 0.00%</span>"

    gw = _good_when(indicator_key)
    if gw == "high":
        color = COLOR_UP if direction_up else COLOR_DOWN
    elif gw == "low":
        color = COLOR_DOWN if direction_up else COLOR_UP
    else:
        color = COLOR_FLAT

    arrow = "▲" if direction_up else "▼"
    return f"<span style='color:{color}'>{arrow} {abs(float(yoy_pct)):.2f}%</span>"


def format_yoy(yoy_pct: float | None) -> str:
    if yoy_pct is None or pd.isna(yoy_pct):
        return "—"
    if yoy_pct > 0:
        return f"<span style='color:{COLOR_UP}'>▲ +{abs(float(yoy_pct)):.2f}%</span>"
    if yoy_pct < 0:
        return f"<span style='color:{COLOR_DOWN}'>▼ -{abs(float(yoy_pct)):.2f}%</span>"
    return f"<span style='color:{COLOR_FLAT}'>● 0.00%</span>"


def _plain_arrow(indicator_key: str, yoy_pct: float | None) -> str:
    if yoy_pct is None or pd.isna(yoy_pct):
        return ""
    if yoy_pct > 0:
        return f"▲ +{abs(float(yoy_pct)):.2f}%"
    if yoy_pct < 0:
        return f"▼ -{abs(float(yoy_pct)):.2f}%"
    return "● 0.00%"


def format_cell(indicator_key: str, value: float | None, yoy_pct: float | None) -> str:
    value_text = format_value(indicator_key, value)
    arrow_text = _plain_arrow(indicator_key, yoy_pct)
    return value_text if not arrow_text else f"{value_text}  {arrow_text}"


def _latest_and_yoy(df: pd.DataFrame) -> tuple[float | None, float | None, int | None]:
    if df is None or df.empty:
        return None, None, None
    sorted_df = df.sort_values("year")
    latest_row = sorted_df.iloc[-1]
    latest_val = float(latest_row["value"]) if pd.notna(latest_row["value"]) else None
    latest_year = int(latest_row["year"]) if pd.notna(latest_row["year"]) else None
    if latest_val is None or len(sorted_df) < 2:
        return latest_val, None, latest_year

    prev_row = sorted_df.iloc[-2]
    prev_val = float(prev_row["value"]) if pd.notna(prev_row["value"]) else None
    if prev_val in (None, 0):
        return latest_val, None, latest_year

    yoy = ((latest_val - prev_val) / abs(prev_val)) * 100.0
    return latest_val, round(yoy, 2), latest_year


def _all_indicator_keys_in_group_order() -> list[str]:
    keys: list[str] = []
    for group in DIMENSION_GROUPS:
        for key in group.get("indicators", []):
            if key in INDICATORS and key not in keys:
                keys.append(key)
    # Safety fallback if catalog/group mismatch appears.
    for key in INDICATORS:
        if key not in keys:
            keys.append(key)
    return keys


def _spark_selector() -> str:
    groups = [g for g in DIMENSION_GROUPS if g.get("indicators")]
    group_labels = [str(g["label"]) for g in groups]
    default_group_index = group_labels.index("Economy") if "Economy" in group_labels else 0

    group_label = st.radio(
        "Sparkline group",
        options=group_labels,
        index=default_group_index,
        horizontal=True,
        key="peers_spark_group",
    )
    selected_group = groups[group_labels.index(group_label)]

    indicator_keys = [k for k in selected_group["indicators"] if k in INDICATORS]
    indicator_labels = [INDICATORS[k]["label"] for k in indicator_keys]
    indicator_label = st.radio(
        "Sparkline indicator",
        options=indicator_labels,
        index=0,
        horizontal=True,
        key="peers_spark_indicator",
    )
    return indicator_keys[indicator_labels.index(indicator_label)]


def build_peers_dataframe(
    chosen: list[str],
    year_range: tuple[int, int],
    spark_indicator: str = DEFAULT_SPARK_INDICATOR,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    indicator_keys = _all_indicator_keys_in_group_order()
    long_records: list[dict[str, Any]] = []
    wide_records: list[dict[str, Any]] = []

    for iso3 in chosen:
        meta = COUNTRY_META.get(iso3, {"name": iso3, "flag": "", "region": "—"})
        row: dict[str, Any] = {
            "Country": f"{meta['flag']} {meta['name']}",
            "Region": meta.get("region", "—"),
        }

        spark_df = get_indicator_timeseries([iso3], spark_indicator, year_range[0], year_range[1])
        if spark_df is not None and not spark_df.empty:
            spark_values = spark_df.sort_values("year")["value"].dropna().astype(float).tolist()
        else:
            spark_values = []
        row["Sparkline"] = spark_values

        for key in indicator_keys:
            label = _base_label(key)
            ind_df = get_indicator_timeseries([iso3], key, year_range[0], year_range[1])
            val, yoy, _ = _latest_and_yoy(ind_df)
            row[label] = format_cell(key, val, yoy)

            if ind_df is not None and not ind_df.empty:
                long_records.extend(ind_df.to_dict("records"))

        wide_records.append(row)

    wide_df = pd.DataFrame(wide_records)
    long_df = pd.DataFrame(long_records)
    if not long_df.empty:
        long_df = long_df.sort_values(["iso3", "indicator", "year"]).reset_index(drop=True)
    return wide_df, long_df


def _column_config(spark_indicator: str) -> dict[str, Any]:
    spark_meta = INDICATORS.get(spark_indicator, {"label": "Trend"})
    cfg: dict[str, Any] = {
        "Country": st.column_config.TextColumn("Country", width="medium"),
        "Region": st.column_config.TextColumn("Region", width="small"),
        "Sparkline": st.column_config.LineChartColumn(
            f"Trend · {spark_meta['label']}",
            width="medium",
        ),
    }

    for key in _all_indicator_keys_in_group_order():
        base_label = _base_label(key)
        cfg[base_label] = st.column_config.TextColumn(
            _column_label(key),
            help=f"{INDICATORS[key]['label']} — latest value + YoY.",
            width="small",
        )
    return cfg


def _cell_style_for(indicator_key: str, text: Any) -> str:
    if not isinstance(text, str):
        return ""
    if "▲" in text:
        if _good_when(indicator_key) == "high":
            return f"color: {COLOR_UP};"
        if _good_when(indicator_key) == "low":
            return f"color: {COLOR_DOWN};"
        return f"color: {COLOR_FLAT};"
    if "▼" in text:
        if _good_when(indicator_key) == "high":
            return f"color: {COLOR_DOWN};"
        if _good_when(indicator_key) == "low":
            return f"color: {COLOR_UP};"
        return f"color: {COLOR_FLAT};"
    if "●" in text:
        return f"color: {COLOR_FLAT};"
    return ""


def _yoy_legend() -> None:
    entries = []
    for key in _all_indicator_keys_in_group_order():
        label = _column_label(key)
        sample = _colored_arrow_html(key, 1.23)
        if _good_when(key) == "low":
            sample_down = _colored_arrow_html(key, -1.23)
            entries.append(f"<li>{label}: {sample} / {sample_down}</li>")
    if not entries:
        entries = [
            f"<li>High-good indicators: <span style='color:{COLOR_UP}'>▲</span> up is good, <span style='color:{COLOR_DOWN}'>▼</span> down is bad</li>",
            f"<li>Low-good indicators: <span style='color:{COLOR_DOWN}'>▲</span> up is bad, <span style='color:{COLOR_UP}'>▼</span> down is good</li>",
            f"<li>Neutral indicators: <span style='color:{COLOR_FLAT}'>▲/▼</span> neutral</li>",
        ]

    st.markdown(
        "<small><b>YoY color rule</b><ul style='margin-top:0.2rem'>"
        + "".join(entries[:4])
        + "</ul></small>",
        unsafe_allow_html=True,
    )


def render_country_peers_table(chosen: list[str], year_range: tuple[int, int]) -> None:
    if not chosen:
        st.info("Select at least one country in the sidebar to populate the table.")
        return

    st.subheader("📋 Country peer comparison")
    spark_indicator = _spark_selector()

    with st.spinner("Building peer table…"):
        wide_df, long_df = build_peers_dataframe(chosen, year_range, spark_indicator)

    if wide_df.empty:
        st.info("No data available for the selected countries / year range.")
        return

    metric_cols = _all_indicator_keys_in_group_order()
    metric_base_labels = [_base_label(k) for k in metric_cols]

    def _style_col(series: pd.Series) -> list[str]:
        indicator_key = next((k for k in metric_cols if _base_label(k) == series.name), None)
        if indicator_key is None:
            return [""] * len(series)
        return [_cell_style_for(indicator_key, v) for v in series]

    styled = wide_df.style.apply(_style_col, subset=metric_base_labels)

    st.dataframe(
        styled,
        column_config=_column_config(spark_indicator),
        use_container_width=True,
        hide_index=True,
    )

    _yoy_legend()

    with st.expander("Raw data (long format)", expanded=False):
        if long_df.empty:
            st.info("No long-format rows for the current selection.")
        else:
            st.dataframe(long_df, use_container_width=True, hide_index=True)


__all__ = [
    "render_country_peers_table",
    "build_peers_dataframe",
    "format_value",
    "format_yoy",
    "format_cell",
    "DEFAULT_SPARK_INDICATOR",
]
