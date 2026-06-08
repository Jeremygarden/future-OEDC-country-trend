# future-OEDC-country-trend backend

TypeScript + Fastify backend for a global country stats dashboard.

## Prerequisites

- Node.js 20+
- npm 10+

## Setup

```bash
npm install
```

## Run locally

```bash
npm run dev
```

Server defaults:

- `HOST=0.0.0.0`
- `PORT=3000`

Health endpoint:

- `GET http://localhost:3000/api/v1/health`

## API Endpoints

- `GET /api/v1/health` - health check
- `GET /api/v1/countries` - country list with filtering/sorting/pagination
- `GET /api/v1/countries/summary` - aggregate summary for current filter
- `GET /api/v1/metrics` - request/uptime counters
- `GET /api/v1/timeseries` - time series values from ETL JSON/CSV files
- `GET /api/v1/indicators` - list available indicators grouped by country
- `GET /api/v1/compare` - compare one indicator across multiple countries
- `GET /api/v1/forecast` - project future values using linear/CAGR methods
- `GET /api/v1/openapi.json` - OpenAPI 3.0 spec describing all endpoints
- `GET /api/v1/docs` - machine-readable endpoint catalog

### `/api/v1/countries` query params

- `search` string filter by country name
- `region` exact region name (or omit for all)
- `sortBy` one of `population|gdpPerCapita|lifeExpectancy|internetUsers|co2PerCapita`
- `limit` positive integer
- `offset` integer >= 0

### `/api/v1/timeseries` query params

- Response includes `cached: true|false` and current cache stats.
- Invalid year windows (`fromYear > toYear`) return structured `400` error with code `INVALID_YEAR_RANGE`.

- `country` ISO country code (e.g. `US`, `CN`, `JPN`)
- `indicator` metric key/code (e.g. `GDP`)
- `fromYear` integer >= 1900
- `toYear` integer <= 2100

Data source resolution order:

1. `TIMESERIES_DATA_PATH` (if set)
2. `fixtures/timeseries.sample.json`
3. `fixtures/timeseries.sample.csv`
4. `db/timeseries.json`
5. `db/timeseries.csv`
6. `scripts/timeseries.json`
7. built-in fixture fallback

### `/api/v1/indicators` query params

- `country` optional ISO country code to filter one country

### `/api/v1/compare` query params

- `countries` comma-separated ISO codes (e.g. `US,CN,JP,AU,CA`)
- `indicator` indicator name/code (e.g. `GDP`)

### `/api/v1/forecast` query params

- `country` ISO country code
- `indicator` indicator name/code
- `yearsAhead` integer 1..20 (default 5)
- `method` `linear` or `cagr` (default `linear`)

## Docker deployment

Build and run with Docker Compose:

```bash
docker compose up --build
```

The API is exposed at `http://localhost:3000`.

## Scripts

- `npm run dev` - run with watch mode
- `npm run build` - compile TypeScript to `dist/`
- `npm run start` - run compiled app
- `npm run lint` - lint source files
- `npm run format` - format files with Prettier
- `npm run test` - run tests once
