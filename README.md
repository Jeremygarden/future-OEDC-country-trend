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
- `GET /api/v1/docs` - machine-readable endpoint catalog

### `/api/v1/countries` query params

- `search` string filter by country name
- `region` exact region name (or omit for all)
- `sortBy` one of `population|gdpPerCapita|lifeExpectancy|internetUsers|co2PerCapita`
- `limit` positive integer
- `offset` integer >= 0

## Scripts

- `npm run dev` - run with watch mode
- `npm run build` - compile TypeScript to `dist/`
- `npm run start` - run compiled app
- `npm run lint` - lint source files
- `npm run format` - format files with Prettier
- `npm run test` - run tests once
