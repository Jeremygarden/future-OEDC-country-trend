"""Per-dimension tabbed pages for the dashboard (iteration 4).

One page per macro dimension, each rendering a KPI row + line chart +
bar chart for the selected countries.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from charts import bar_chart, line_chart  # noqa: E402
from data_client import (  # noqa: E402
    INDICATORS,
    get_indicator_timeseries,
    latest_value_per_country,
    rank_countries,
)

# Tab → indicator key. Keep ordering stable for the UI.
DIMENSION_TABS: list[tuple[str, str]] = [
    ("💰 Debt", "debt"),
    ("⚡ Energy", "energy"),
    ("🧾 Taxation", "tax"),
    ("🌍 FDI", "fdi"),
    ("🏠 Household savings", "savings"),
    ("🩺 Health spending", "health"),
]


def render_dimension_page(chosen: list[str], indicator_key: str) -> None:
    meta = INDICATORS[indicator_key]
    df = get_indicator_timeseries(chosen, indicator_key)

    if df.empty:
        st.info(f"No data available for {meta['label']}.")
        return

    source_tag = df["source"].mode().iloc[0] if "source" in df.columns else "—"
    st.markdown(
        f"### {meta['label']}\n"
        f"_source: `{source_tag}` · unit: `{meta['unit']}` · "
        f"countries: {len(chosen)}_"
    )

    # KPI row.
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

    # Charts.
    line_col, bar_col = st.columns([2, 1])
    with line_col:
        st.plotly_chart(
            line_chart(df, meta["label"], meta["unit"]),
            use_container_width=True,
        )
    with bar_col:
        st.plotly_chart(
            bar_chart(df, f"Latest {meta['label']}", meta["unit"]),
            use_container_width=True,
        )

    # Sortable data table.
    pivot = (
        df.pivot_table(index="year", columns="iso3", values="value", aggfunc="first")
        .sort_index()
    )
    st.markdown("**Year × country values**")
    st.dataframe(pivot, use_container_width=True)


def render_dimension_tabs(chosen: list[str]) -> None:
    if not chosen:
        st.warning("Select at least one country in the sidebar.")
        return
    tabs = st.tabs([label for label, _ in DIMENSION_TABS])
    for tab, (_, key) in zip(tabs, DIMENSION_TABS):
        with tab:
            render_dimension_page(chosen, key)
