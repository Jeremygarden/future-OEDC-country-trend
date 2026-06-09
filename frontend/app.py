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

from data_client import (  # noqa: E402
    COUNTRY_META,
    INDICATORS,
    check_health,
)
from dimension_pages import render_dimension_tabs  # noqa: E402
from overview_page import render_overview  # noqa: E402
from country_peers_table import render_country_peers_table  # noqa: E402

DEFAULT_YEAR_RANGE = (2015, 2026)


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
            max_value=2026,
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
        elif "snapshot" in health.message.lower() or "offline mode" in health.message.lower():
            st.info(f"ℹ️ {health.message}")
        else:
            st.warning(f"⚠️ {health.message}\n\nUsing fallback fixtures.")
        st.caption(f"URL: `{health.backend_url}`")

        st.divider()
        st.caption("Iteration 5 — UI polish")

    return chosen, year_range


def main() -> None:
    configure_page()
    render_header()
    chosen, year_range = render_sidebar()

    if not chosen:
        st.warning("Select at least one country in the sidebar to begin.")
        return

    overview_tab, dimensions_tab, table_tab = st.tabs(
        ["📊 Overview", "🗂 Dimensions", "📋 Country table"]
    )
    with overview_tab:
        render_overview(chosen, year_range)
    with dimensions_tab:
        with st.spinner("Loading dimensions…"):
            render_dimension_tabs(chosen, year_range)
    with table_tab:
        render_country_peers_table(chosen, year_range)


if __name__ == "__main__":
    main()
