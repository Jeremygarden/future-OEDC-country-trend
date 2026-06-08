# Security Policy

## Supported branch

Security fixes are accepted on `main`.

## Reporting a vulnerability

Please open a private security advisory on GitHub if available, or contact the repository owner directly. Avoid posting exploit details in public issues until a fix is available.

Include:

- affected endpoint/file/component,
- reproduction steps or proof of concept,
- expected impact,
- suggested fix if known.

## Security expectations

- Country/statistical data from ETL, fixtures, or APIs must be treated as untrusted input.
- Static dashboard rendering should prefer DOM node construction and `textContent`; TypeScript HTML helpers must escape data before interpolation.
- Backend validation should use Zod schemas and `appHttpError` for consistent error envelopes.
- Python ETL errors should use `etl.errors.EtlError` / `etl_error_payload` so failures are structured and do not leak secrets.
- Dependency audits should be run periodically with `npm audit` and `pip-audit -r requirements.txt -r frontend/requirements.txt`.

## Known follow-ups

Open issues track non-blocking security/performance work, including dependency toolchain upgrades and SQL view optimization.
