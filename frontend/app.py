"""
Global Country Stats Dashboard - Streamlit Frontend
====================================================

Multi-country comparison dashboard for the future-OEDC-country-trend backend.
Inspired by stockpeers-style multi-entity comparison: side-by-side country
selectors, KPI cards, and themed Plotly charts.

Run locally:
    streamlit run frontend/app.py

Backend URL is configurable via the BACKEND_API_URL environment variable
(default: http://localhost:3000/api/v1). When the backend is offline, the
app falls back to fixtures/countries.sample.json plus deterministic
synthetic time-series for indicators not surfaced by the simple list
endpoint (clearly tagged ``source=synthetic``).
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
    COUNTRY_META,
    INDICATORS,
    check_health,
    get_country_table,
    get_indicator_timeseries,
    latest_value_per_country,
    rank_countries,
)
from dimension_pages import render_dimension_tabs  # noqa: E402

DEFAULT_YEAR_RANGE = (2015, 2024)


def configure_page() -> None:
    st.set_page_config(
        page_title="Global Country Stats Dashboard",
        page_icon="🌐",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def render_header() -> None:
    st.title("🌐 Global Country Stats Dashboard")
    st.caption(
        "Multi-country macroeconomic comparison • USA • China • Japan • Australia • Canada"
    )


def render_sidebar() -> tuple[list[str], tuple[int, int]]:
    with st.sidebar:
        st.header("⚙️ Controls")
        labels = {iso: f"{m['flag']} {m['name']}" for iso, m in COUNTRY_META.items()}
        chosen = st.multiselect(
            "Countries",
            options=list(COUNTRY_META.keys()),
            default=list(COUNTRY_META.keys()),
            format_func=lambda iso: labels[iso],
            help="Select up to 5 countries for side-by-side comparison.",
        )

        year_range = st.slider(
            "Year range",
            min_value=2000,
            max_value=2024,
            value=DEFAULT_YEAR_RANGE,
            step=1,
            help="Window applied to every comparison chart and KPI card.",
        )

        st.divider()
        st.subheader("Backend")
        with st.spinner("Pinging backend…"):
            health = check_health()
        if health.online:
            st.success(f"✅ {health.message}")
        else:
            st.warning(f"⚠️ {health.message}\n\nUsing fallback fixtures.")
        st.caption(f"URL: `{health.backend_url}`")

        st.divider()
        st.caption("Iteration 5 — UI polish")

    return chosen, year_range


def render_country_overview(chosen: list[str]) -> None:
    st.subheader("Selected countries")
    cols = st.columns(len(chosen))
    for col, iso3 in zip(cols, chosen):
        meta = COUNTRY_META.get(iso3, {"name": iso3, "flag": "", "region": "—"})
        with col:
            st.metric(label=f"{meta['flag']} {meta['name']}", value=iso3, delta=meta["region"])


def render_kpi_row(chosen: list[str], indicator_key: str, year_range: tuple[int, int]) -> None:
    """KPI metric cards: latest value, YoY delta, rank per country."""
    meta = INDICATORS[indicator_key]
    try:
        df = get_indicator_timeseries(chosen, indicator_key, year_range[0], year_range[1])
    except Exception as exc:  # noqa: BLE001 — defensive UI boundary
        st.error(f"Failed to load {meta['label']}: {exc}")
        return

    latest = latest_value_per_country(df)
    ranked = rank_countries(latest, ascending=False)

    if ranked.empty:
        st.info("No data available for KPI cards.")
        return

    source_tag = df["source"].mode().iloc[0] if "source" in df.columns else "—"
    st.markdown(
        f"**KPI: {meta['label']}** &nbsp;•&nbsp; source: `{source_tag}` &nbsp;•&nbsp; "
        f"unit: `{meta['unit']}`"
    )

    cols = st.columns(len(ranked))
    for col, (_, row) in zip(cols, ranked.iterrows()):
        iso3 = row["iso3"]
        cmeta = COUNTRY_META.get(iso3, {"flag": "", "name": iso3})
        yoy = row["yoy_pct"]
        delta_str = f"{yoy:+.2f}% YoY" if yoy is not None else "—"
        rank_str = f"#{int(row['rank'])} of {len(ranked)}"
        with col:
            st.metric(
                label=f"{cmeta['flag']} {cmeta['name']}  ·  {rank_str}",
                value=f"{row['value']:.2f} {meta['unit']}",
                delta=delta_str,
            )


def render_country_table() -> None:
    with st.spinner("Loading country list…"):
        try:
            df, source = get_country_table()
        except Exception as exc:  # noqa: BLE001
            st.error(f"Failed to load countries: {exc}")
            return
    if df.empty:
        st.info("No country list available from backend or fixture.")
        return
    st.markdown(f"**Country list** — source: `{source}`")
    st.dataframe(df, hide_index=True, use_container_width=True)


def render_comparison_charts(chosen: list[str], year_range: tuple[int, int]) -> None:
    st.subheader("📈 Comparison line charts")
    st.caption(
        "Multi-country trends. Backend `/compare` is used when available; "
        "otherwise deterministic synthetic series (`source=synthetic`)."
    )

    indicator_keys = ["gdp", "cpi", "unemployment"]
    tabs = st.tabs([INDICATORS[k]["label"] for k in indicator_keys])
    for tab, key in zip(tabs, indicator_keys):
        with tab:
            with st.spinner(f"Loading {INDICATORS[key]['label']}…"):
                render_kpi_row(chosen, key, year_range)
                try:
                    df = get_indicator_timeseries(chosen, key, year_range[0], year_range[1])
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Failed to load chart data: {exc}")
                    continue
                meta = INDICATORS[key]
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


def main() -> None:
    configure_page()
    render_header()
    chosen, year_range = render_sidebar()

    if not chosen:
        st.warning("Select at least one country in the sidebar to begin.")
        return

    render_country_overview(chosen)
    st.divider()

    overview_tab, dimensions_tab, table_tab = st.tabs(
        ["📊 Overview", "🗂 Dimensions", "📋 Country table"]
    )
    with overview_tab:
        render_comparison_charts(chosen, year_range)
    with dimensions_tab:
        st.subheader("Per-dimension comparison")
        st.caption(
            "Debt, Energy, Taxation, FDI, Household savings, Health spending"
        )
        with st.spinner("Loading dimension pages…"):
            render_dimension_tabs(chosen, year_range)
    with table_tab:
        render_country_table()


if __name__ == "__main__":
    main()
