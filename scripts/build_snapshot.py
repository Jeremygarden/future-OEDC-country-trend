#!/usr/bin/env python3
"""Build offline data snapshots for the Streamlit frontend.

Fetches the 9 dashboard indicators for USA/CHN/JPN/AUS/CAN from the public
World Bank WDI v2 API and writes a single JSON file that the frontend can
read directly when no backend is reachable. Designed for Streamlit Community
Cloud deployments where only the Python frontend is hosted.

Usage:
    python scripts/build_snapshot.py
    # writes data/snapshots/country_stats.json

The frontend's data_client reads this file before falling back to synthetic
series, so a deployed dashboard always shows real numbers.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

WB_API = "https://api.worldbank.org/v2"
COUNTRIES = ["USA", "CHN", "JPN", "AUS", "CAN"]

# Indicators keyed by the frontend's short id (must match
# frontend/data_client.py INDICATORS).
INDICATORS = {
    "gdp": "NY.GDP.MKTP.CD",
    "cpi": "FP.CPI.TOTL.ZG",
    "unemployment": "SL.UEM.TOTL.ZS",
    "debt": "GC.DOD.TOTL.GD.ZS",
    "energy": "EG.USE.PCAP.KG.OE",
    "tax": "GC.TAX.TOTL.GD.ZS",
    "fdi": "BX.KLT.DINV.WD.GD.ZS",
    "health": "SH.XPD.CHEX.GD.ZS",
    # savings: World Bank household savings code is not consistently
    # populated; frontend falls back to synthetic if missing.
    "savings": "NY.GNS.ICTR.ZS",
}

START_YEAR = 2010
END_YEAR = 2024

OUT_PATH = Path(__file__).resolve().parents[1] / "data" / "snapshots" / "country_stats.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("snapshot")


def fetch_indicator(code: str) -> list[dict[str, Any]]:
    """Fetch one indicator for all target countries in one request.

    World Bank v2 supports semicolon-separated country codes.
    """
    url = f"{WB_API}/country/{';'.join(COUNTRIES)}/indicator/{code}"
    params = {
        "format": "json",
        "date": f"{START_YEAR}:{END_YEAR}",
        "per_page": 1000,
    }
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, timeout=30)
            if r.status_code == 200:
                payload = r.json()
                if isinstance(payload, list) and len(payload) >= 2:
                    return payload[1] or []
                return []
            log.warning("HTTP %s for %s", r.status_code, code)
        except requests.RequestException as exc:
            log.warning("Request failed for %s (attempt %d): %s", code, attempt + 1, exc)
        time.sleep(2 ** attempt)
    return []


def build_snapshot() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for short, code in INDICATORS.items():
        log.info("Fetching %s (%s)", short, code)
        for entry in fetch_indicator(code):
            value = entry.get("value")
            if value is None:
                continue
            iso3 = entry.get("countryiso3code") or ""
            if iso3 not in COUNTRIES:
                continue
            try:
                year = int(entry.get("date"))
            except (TypeError, ValueError):
                continue
            rows.append(
                {
                    "indicator": short,
                    "indicator_code": code,
                    "iso3": iso3,
                    "country": (entry.get("country") or {}).get("value") or iso3,
                    "year": year,
                    "value": float(value),
                }
            )
        time.sleep(0.4)  # be polite to the WB API

    rows.sort(key=lambda r: (r["indicator"], r["iso3"], r["year"]))

    snapshot = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "World Bank WDI v2 (https://api.worldbank.org/v2)",
        "countries": COUNTRIES,
        "indicators": INDICATORS,
        "year_range": [START_YEAR, END_YEAR],
        "row_count": len(rows),
        "rows": rows,
    }
    return snapshot


def main() -> int:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    snap = build_snapshot()
    OUT_PATH.write_text(json.dumps(snap, indent=2))
    log.info("Wrote %d rows -> %s (%.1f KB)", snap["row_count"], OUT_PATH, OUT_PATH.stat().st_size / 1024)
    return 0


if __name__ == "__main__":
    sys.exit(main())
