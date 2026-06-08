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
    DIMENSION_GROUPS,
    INDICATORS,
    format_value,
    get_indicator_timeseries,
    get_year_range,
)


def _clean_indicator_df(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["year", "iso3", "country", "value"])
    out = df.copy()
    if "value" in out.columns:
        out = out[out["value"].notna()]
    return out


def _latest_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["iso3", "country", "year", "value", "prev_value", "yoy_pct"])

    sorted_df = df.sort_values(["iso3", "year"])
    rows: list[dict[str, object]] = []
    for iso3, group in sorted_df.groupby("iso3", sort=False):
        if group.empty:
            continue
        latest = group.iloc[-1]
        prev = group.iloc[-2] if len(group) >= 2 else None

        latest_value = float(latest["value"]) if pd.notna(latest["value"]) else None
        prev_value = float(prev["value"]) if prev is not None and pd.notna(prev["value"]) else None
        yoy_pct = None
        if latest_value is not None and prev_value not in (None, 0):
            yoy_pct = ((latest_value - prev_value) / abs(prev_value)) * 100.0

        rows.append(
            {
                "iso3": str(iso3),
                "country": str(latest.get("country", iso3)),
                "year": int(latest["year"]),
                "value": latest_value,
                "prev_value": prev_value,
                "yoy_pct": yoy_pct,
            }
        )

    return pd.DataFrame(rows)


def _leader_line(ind_key: str, df: pd.DataFrame) -> str:
    if df.empty:
        return "No data"

    latest_year = int(df["year"].max())
    latest_year_rows = df[df["year"] == latest_year].dropna(subset=["value"]).copy()
    if latest_year_rows.empty:
        return "No data"

    good_when = INDICATORS.get(ind_key, {}).get("good_when", "neutral")
    ascending = good_when == "low"
    top = latest_year_rows.sort_values("value", ascending=ascending).iloc[0]
    iso3 = str(top["iso3"])
    country = COUNTRY_META.get(iso3, {}).get("name", str(top.get("country", iso3)))
    value = float(top["value"])
    return f"🏆 {country} · {format_value(ind_key, value)}"


def _mini_chart(df: pd.DataFrame) -> go.Figure:
    fig = px.line(
        df,
        x="year",
        y="value",
        color="iso3",
        color_discrete_map=COUNTRY_COLORS,
    )
    fig.update_traces(line=dict(width=2), mode="lines")
    fig.update_layout(
        height=160,
        margin=dict(l=8, r=8, t=8, b=8),
        showlegend=False,
        xaxis_title=None,
        yaxis_title=None,
        hovermode="x unified",
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig


def _render_group_grid(group: dict[str, object], chosen: list[str], years: tuple[int, int]) -> None:
    indicators = list(group.get("indicators", []))
    label = str(group.get("label", group.get("key", "Group")))
    group_key = str(group.get("key", "group"))

    with st.expander(f"{label} · {len(indicators)} dimensions", expanded=True):
        cols = st.columns(5)
        for i, ind_key in enumerate(indicators):
            with cols[i % 5]:
                with st.container(border=True):
                    ind_meta = INDICATORS.get(ind_key, {})
                    ind_label = str(ind_meta.get("label", ind_key))
                    st.markdown(f"**{ind_label}**")

                    df_raw = get_indicator_timeseries(chosen, ind_key, years[0], years[1])
                    df = _clean_indicator_df(df_raw)
                    st.caption(_leader_line(ind_key, df))

                    if df.empty:
                        st.caption(":gray[No data]")
                    else:
                        st.plotly_chart(
                            _mini_chart(df),
                            use_container_width=True,
                            config={"displayModeBar": False},
                            key=f"mini_{group_key}_{ind_key}",
                        )

                    if st.button(
                        "View details",
                        key=f"open_{group_key}_{ind_key}",
                        use_container_width=True,
                    ):
                        st.session_state["dim_open"] = ind_key
                        st.rerun()


def _delta_color_for(ind_key: str) -> str:
    good_when = INDICATORS.get(ind_key, {}).get("good_when", "neutral")
    if good_when == "low":
        return "inverse"
    if good_when == "neutral":
        return "off"
    return "normal"


def _render_detail(ind_key: str, chosen: list[str], years: tuple[int, int]) -> None:
    if ind_key not in INDICATORS:
        return

    meta = INDICATORS[ind_key]
    df = _clean_indicator_df(get_indicator_timeseries(chosen, ind_key, years[0], years[1]))

    st.divider()
    st.subheader(f"{meta['label']} — {meta['group_label']}")
    st.caption(meta.get("description", ""))

    if st.button("← Back to grid", key="dim_back"):
        st.session_state.pop("dim_open", None)
        st.rerun()

    latest = _latest_rows(df)
    kpi_cols = st.columns(len(chosen))
    latest_by_iso = {str(r["iso3"]): r for _, r in latest.iterrows()} if not latest.empty else {}

    delta_color = _delta_color_for(ind_key)
    for col, iso3 in zip(kpi_cols, chosen):
        cmeta = COUNTRY_META.get(iso3, {"name": iso3, "flag": ""})
        row = latest_by_iso.get(iso3)

        value_txt = "—"
        delta_txt = "—"
        if row is not None and row.get("value") is not None:
            value_txt = format_value(ind_key, float(row["value"]))
            yoy = row.get("yoy_pct")
            if yoy is not None:
                delta_txt = f"{float(yoy):+.2f}%"

        with col:
            st.metric(
                label=f"{cmeta.get('flag', '')} {cmeta.get('name', iso3)}".strip(),
                value=value_txt,
                delta=delta_txt,
                delta_color=delta_color,
            )

    left, right = st.columns(2)
    with left:
        line_fig = line_chart(df, meta["label"], meta.get("unit", ""))
        line_fig.update_layout(height=420)
        st.plotly_chart(line_fig, use_container_width=True, config={"displayModeBar": False})
    with right:
        bar_fig = bar_chart(df, f"Latest {meta['label']}", meta.get("unit", ""))
        bar_fig.update_layout(height=320)
        st.plotly_chart(bar_fig, use_container_width=True, config={"displayModeBar": False})

    if df.empty:
        st.info("No data")
        return

    pivot = df.pivot_table(index="year", columns="country", values="value", aggfunc="first").sort_index()
    formatted = pivot.copy()
    for col in formatted.columns:
        formatted[col] = formatted[col].apply(
            lambda v: format_value(ind_key, float(v)) if pd.notna(v) else "—"
        )

    st.dataframe(formatted, hide_index=False, use_container_width=True)


def render_dimension_tabs(chosen: list[str], year_range: tuple[int, int] | None = None) -> None:
    if not chosen:
        st.warning("Select at least one country in the sidebar.")
        return

    years = year_range if year_range is not None else get_year_range()

    for group in DIMENSION_GROUPS:
        _render_group_grid(group, chosen, years)

    open_key = st.session_state.get("dim_open")
    if isinstance(open_key, str) and open_key in INDICATORS:
        _render_detail(open_key, chosen, years)
