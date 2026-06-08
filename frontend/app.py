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
app falls back to fixtures/countries.sample.json.
"""
from __future__ import annotations

import streamlit as st

# Iteration 1: Skeleton + country selector. More features land in
# subsequent iterations.

DEFAULT_COUNTRIES = [
    {"iso3": "USA", "name": "United States", "flag": "🇺🇸"},
    {"iso3": "CHN", "name": "China", "flag": "🇨🇳"},
    {"iso3": "JPN", "name": "Japan", "flag": "🇯🇵"},
    {"iso3": "AUS", "name": "Australia", "flag": "🇦🇺"},
    {"iso3": "CAN", "name": "Canada", "flag": "🇨🇦"},
]


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


def render_country_selector() -> list[str]:
    """Render the sidebar country selector and return chosen ISO3 codes."""
    with st.sidebar:
        st.header("⚙️ Controls")
        labels = {c["iso3"]: f"{c['flag']} {c['name']}" for c in DEFAULT_COUNTRIES}
        chosen = st.multiselect(
            "Countries",
            options=[c["iso3"] for c in DEFAULT_COUNTRIES],
            default=[c["iso3"] for c in DEFAULT_COUNTRIES],
            format_func=lambda iso: labels[iso],
        )
        st.divider()
        st.caption("Iteration 1 — skeleton")
    return chosen


def main() -> None:
    configure_page()
    render_header()
    chosen = render_country_selector()

    if not chosen:
        st.warning("Select at least one country in the sidebar to begin.")
        return

    cols = st.columns(len(chosen))
    label_by_iso = {c["iso3"]: c for c in DEFAULT_COUNTRIES}
    for col, iso3 in zip(cols, chosen):
        meta = label_by_iso[iso3]
        with col:
            st.metric(label=f"{meta['flag']} {meta['name']}", value=meta["iso3"])

    st.info(
        "Charts, KPIs, and per-dimension tabs land in iterations 2–6. "
        "Backend integration is configurable via BACKEND_API_URL."
    )


if __name__ == "__main__":
    main()
