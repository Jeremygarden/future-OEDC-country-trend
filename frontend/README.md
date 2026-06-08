# Frontend — Streamlit Country Stats Dashboard

Multi-country macroeconomic comparison UI for the
`future-OEDC-country-trend` backend.

## Quick start

```bash
pip install -r frontend/requirements.txt
streamlit run frontend/app.py
```

Backend URL is configurable via the `BACKEND_API_URL` environment variable
(default: `http://localhost:3000/api/v1`). When the backend is offline, the
app falls back to `fixtures/countries.sample.json` plus deterministic
synthetic time-series (clearly tagged `source=synthetic`).

## Features

- **Multi-country comparison** — side-by-side KPIs, line charts, bar
  charts for any subset of USA / CHN / JPN / AUS / CAN.
- **Three top-level tabs** — Overview (GDP / CPI / unemployment),
  Dimensions (Debt / Energy / Taxation / FDI / Household savings /
  Health spending), and a raw country table.
- **KPI cards** — latest value, YoY delta, country rank.
- **Sidebar controls** — country multi-select, year range slider
  (2000–2024), live backend health probe.
- **Themed Plotly charts** — shared template, per-country color map,
  unified hover.
- **Graceful fallback** — every chart and KPI works even when the
  backend is offline (synthetic series clearly tagged in the UI).
- **Loading spinners and error boundaries** — heavy panels show a
  spinner; data-fetch failures render a contextual `st.error` instead
  of crashing the page.

## Module layout

| File | Purpose |
| --- | --- |
| `app.py` | Streamlit entrypoint (page config, sidebar, top-level tabs) |
| `data_client.py` | HTTP client (`/health`, `/countries`, `/compare`) + fixture/synthetic fallback + KPI helpers |
| `charts.py` | Reusable Plotly helpers (`line_chart`, `bar_chart`) with shared theme |
| `dimension_pages.py` | Per-dimension page renderer used inside the Dimensions tab |
| `requirements.txt` | Pinned runtime dependencies |
| `tests/` | Unit tests for chart and data helpers (iteration 6) |

## Iteration log

- **iter-1** — skeleton, country selector for USA/CHN/JPN/AUS/CAN.
- **iter-2** — comparison line/bar charts for GDP/CPI/unemployment,
  backend health probe, fixture + synthetic fallbacks.
- **iter-3** — KPI metric cards with YoY delta and rank.
- **iter-4** — per-dimension tabs (Debt / Energy / Taxation / FDI /
  Household savings / Health spending).
- **iter-5** — UI polish: year-range slider, themed Plotly defaults,
  loading spinners, error-boundary wrappers around every fetch.
- **iter-6** — production: pinned deps, README, unit tests.
