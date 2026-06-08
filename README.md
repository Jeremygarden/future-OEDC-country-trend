# Future OECD Country Trend — Data Layer

A production-quality database and ETL pipeline for tracking macroeconomic trends across 
**US, China, Japan, Australia, and Canada** using World Bank and OECD data sources.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Data Sources                          │
│  ┌──────────────────┐    ┌──────────────────────────┐   │
│  │  World Bank       │    │  OECD SDMX REST API      │   │
│  │  Data360 API      │    │  sdmx.oecd.org           │   │
│  └────────┬─────────┘    └─────────┬────────────────┘   │
└───────────┼──────────────────────── ┼───────────────────┘
            │                         │
            ▼                         ▼
┌─────────────────────────────────────────────────────────┐
│                    ETL Layer                             │
│  ┌──────────────────┐    ┌──────────────────────────┐   │
│  │  worldbank_client │    │  oecd_client.py          │   │
│  │  .py              │    │  (SDMX-JSON parser)      │   │
│  └────────┬─────────┘    └─────────┬────────────────┘   │
│           └──────────┬─────────────┘                     │
│                      ▼                                    │
│            ┌──────────────────┐                          │
│            │  transform.py    │                          │
│            │  (normalize,     │                          │
│            │   derive, rank)  │                          │
│            └────────┬─────────┘                          │
└─────────────────────┼───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                 SQLite Database                          │
│                 db/country_stats.db                      │
│                                                          │
│  countries  ──► data_points ◄── indicators              │
│                    │                                     │
│  data_sources ─────┘                                    │
│  etl_runs                                                │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                  Query Layer                             │
│  db/query.py: get_country_stats, get_indicator_trend,   │
│               get_latest_comparison, search_indicators  │
│  db/cache.py: TTL file cache for expensive queries      │
└─────────────────────────────────────────────────────────┘
```

## Countries Covered
| Country   | ISO2 | ISO3 | Region       |
|-----------|------|------|--------------|
| USA       | US   | USA  | North America|
| China     | CN   | CHN  | East Asia    |
| Japan     | JP   | JPN  | East Asia    |
| Australia | AU   | AUS  | Oceania      |
| Canada    | CA   | CAN  | North America|

## Quick Start

```bash
# 1. Set up Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Initialize database
python scripts/seed.py

# 3. Run full ETL pipeline
python scripts/full_pipeline.py

# 4. Query data
python -c "
from db.query import get_latest_comparison
import json
data = get_latest_comparison()
print(json.dumps(data, indent=2, default=str))
"
```

## Database Schema

| Table | Description |
|-------|-------------|
| `countries` | 5 target countries with ISO codes |
| `indicators` | Macro indicators (GDP, CPI, unemployment, etc.) |
| `data_points` | Time-series values per country/indicator/year |
| `data_sources` | World Bank, OECD API registrations |
| `etl_runs` | ETL audit log with status and error tracking |

## Key Indicators

**World Bank (Data360 API)**
- `NY.GDP.MKTP.CD` - GDP (current USD)
- `NY.GDP.PCAP.CD` - GDP per capita
- `NY.GDP.MKTP.KD.ZG` - GDP growth rate (%)
- `SP.POP.TOTL` - Total population
- `FP.CPI.TOTL.ZG` - Inflation/CPI (%)
- `SL.UEM.TOTL.ZS` - Unemployment rate (%)
- `NE.TRD.GNFS.ZS` - Trade (% of GDP)

**OECD (SDMX REST API)**
- GDP via QNA/SNA datasets
- Unemployment via MEI (LRHUTTTT)
- CPI via MEI (CPALTT01)
- Government debt % GDP
- Current account balance

## Running Tests

```bash
pytest tests/ -v
```

---

## Frontend (Streamlit) — see `frontend/README.md`

A multi-country comparison dashboard inspired by stockpeers-style
side-by-side analysis. Multi-select countries, year-range slider, KPI
cards (latest · YoY · rank), themed Plotly charts, six per-dimension
pages (Debt / Energy / Taxation / FDI / Household savings / Health
spending), and graceful fallback when the backend is offline.

```bash
pip install -r frontend/requirements.txt
streamlit run frontend/app.py
```

Backend URL is configurable:

```bash
BACKEND_API_URL=http://localhost:3000/api/v1 streamlit run frontend/app.py
```

Frontend unit tests:

```bash
pytest frontend/tests/ -v
```

---

## Backend (TypeScript Fastify) — see README.backend.md
