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

## Module layout

| File | Purpose |
| --- | --- |
| `app.py` | Streamlit entrypoint (page config, sidebar, layout) |
| `data_client.py` | HTTP client + fixture/synthetic fallback |
| `charts.py` | Reusable Plotly chart helpers |
| `requirements.txt` | Pinned runtime dependencies |

## Iteration log

- **iter-1** — skeleton, country selector for USA/CHN/JPN/AUS/CAN
- **iter-2** — comparison line/bar charts (GDP, CPI, unemployment),
  backend health probe, fixture + synthetic fallbacks
