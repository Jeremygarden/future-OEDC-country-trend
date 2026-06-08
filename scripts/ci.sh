#!/usr/bin/env bash
# scripts/ci.sh — Local CI parity runner
#
# Runs the same checks GitHub Actions does (lint + build + tests for the
# TypeScript backend AND Python ETL, plus syntax checks for both frontends).
# Designed so contributors can validate before pushing.
#
# Usage:
#   scripts/ci.sh             # run everything
#   scripts/ci.sh --ts        # TypeScript stack only
#   scripts/ci.sh --py        # Python stack only
#   scripts/ci.sh --frontend  # frontend syntax checks only
#
# Exits non-zero on the first failure.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODE="${1:-all}"

log() { printf '\n=== %s ===\n' "$*"; }

run_ts() {
  log "TypeScript: lint"
  npm run lint

  log "TypeScript: build"
  npm run build

  log "TypeScript: vitest"
  npm test

  log "Frontend (vanilla JS): node --check app.js"
  node --check app.js
}

run_py() {
  log "Python: pytest tests/"
  pytest tests

  log "Python: frontend syntax (frontend/*.py)"
  python -m py_compile \
    frontend/app.py \
    frontend/charts.py \
    frontend/data_client.py
}

run_frontend_syntax() {
  log "Frontend: node --check app.js"
  node --check app.js

  log "Frontend: python -m py_compile frontend/*.py"
  python -m py_compile \
    frontend/app.py \
    frontend/charts.py \
    frontend/data_client.py
}

case "$MODE" in
  --ts|ts)
    run_ts
    ;;
  --py|py)
    run_py
    ;;
  --frontend|frontend)
    run_frontend_syntax
    ;;
  all|"")
    run_ts
    run_py
    ;;
  -h|--help|help)
    sed -n '1,18p' "$0"
    exit 0
    ;;
  *)
    echo "Unknown mode: $MODE (use --ts, --py, --frontend, or all)" >&2
    exit 2
    ;;
esac

log "CI checks passed."
