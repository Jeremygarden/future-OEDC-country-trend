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
endpoint (clearly tagged as ``source=synthetic``).
"""
from __future__ import annotations

import streamlit as st

# Frontend modules — kept relative-import-free so `streamlit run frontend/app.py`
# works without installing the package.
import sys
from pathlib import Path

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
)


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


def render_sidebar() -> tuple[list[str], str]:
    with st.sidebar:
        st.header("⚙️ Controls")
        labels = {iso: f"{m['flag']} {m['name']}" for iso, m in COUNTRY_META.items()}
        chosen = st.multiselect(
            "Countries",
            options=list(COUNTRY_META.keys()),
            default=list(COUNTRY_META.keys()),
            format_func=lambda iso: labels[iso],
        )

        st.divider()
        st.subheader("Backend")
        health = check_health()
        if health.online:
            st.success(f"✅ {health.message}")
        else:
            st.warning(f"⚠️ {health.message}\n\nUsing fallback fixtures.")
        st.caption(f"URL: `{health.backend_url}`")

        st.divider()
        st.caption("Iteration 2 — comparison line charts")

    return chosen, health.message


def render_country_overview(chosen: list[str]) -> None:
    st.subheader("Selected countries")
    cols = st.columns(len(chosen))
    for col, iso3 in zip(cols, chosen):
        meta = COUNTRY_META.get(iso3, {"name": iso3, "flag": "", "region": "—"})
        with col:
            st.metric(label=f"{meta['flag']} {meta['name']}", value=iso3, delta=meta["region"])


def render_country_table() -> None:
    df, source = get_country_table()
    if df.empty:
        st.info("No country list available from backend or fixture.")
        return
    st.markdown(f"**Country list** — source: `{source}`")
    st.dataframe(df, hide_index=True, use_container_width=True)


def render_comparison_charts(chosen: list[str]) -> None:
    st.subheader("📈 Comparison line charts")
    st.caption(
        "Multi-country trends 2015–2024. Backend lacks a time-series endpoint; "
        "values shown are deterministic synthetic series (`source=synthetic`)."
    )

    indicator_keys = ["gdp", "cpi", "unemployment"]
    tabs = st.tabs([INDICATORS[k]["label"] for k in indicator_keys])
    for tab, key in zip(tabs, indicator_keys):
        with tab:
            df = get_indicator_timeseries(chosen, key)
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
    chosen, _ = render_sidebar()

    if not chosen:
        st.warning("Select at least one country in the sidebar to begin.")
        return

    render_country_overview(chosen)
    st.divider()
    render_comparison_charts(chosen)
    st.divider()
    render_country_table()


if __name__ == "__main__":
    main()
