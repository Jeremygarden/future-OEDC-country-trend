# Contributing

Thanks for helping improve `future-OEDC-country-trend`.

## Development setup

### TypeScript backend

```bash
npm ci
npm run lint
npm run build
npm test
```

The Fastify API lives in `src/`. Route tests live in `test/` and run with Vitest.

### Python ETL and dashboard helpers

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt -r frontend/requirements.txt
pytest tests
python -m py_compile frontend/app.py frontend/charts.py frontend/data_client.py
```

ETL clients live in `etl/`, database helpers in `db/`, and Python tests in `tests/`.

## Pull request expectations

1. Keep changes focused and additive.
2. Add or update tests for bug fixes and new behavior.
3. Run the relevant checks before pushing:
   - `npm run lint`
   - `npm run build`
   - `npm test`
   - `pytest tests`
   - `node --check app.js` when touching the static frontend
   - `python -m py_compile frontend/app.py frontend/charts.py frontend/data_client.py` when touching Streamlit/frontend Python
4. Document new endpoints or data contracts in `README.md`, `README.backend.md`, or route docs.
5. Do not commit generated dependency directories such as `node_modules/`, virtualenvs, caches, or local databases.

## Error response contract

Backend application errors should use the shared envelope:

```json
{
  "error": {
    "code": "MACHINE_READABLE_CODE",
    "message": "Human readable message",
    "statusCode": 400,
    "details": []
  }
}
```

Python ETL errors use the same shape with Python naming for the status field (`status_code`). Use `etl.errors.EtlError` or `etl_error_payload` for new ETL-facing errors.

## Data and security hygiene

- Treat imported country, indicator, and source data as untrusted.
- Render user/imported strings with DOM `textContent` or escaped helpers; avoid `innerHTML` for data-driven content.
- Keep secrets in environment variables or local `.env` files only. Never commit tokens, API keys, database dumps, or private datasets.
