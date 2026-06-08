#!/usr/bin/env python3
"""Build offline data snapshot for the Streamlit frontend.

Fetches the configured dashboard dimensions from World Bank WDI v2 for
USA/CHN/JPN/AUS/CAN and writes data/snapshots/country_stats.json.
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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from etl.dimension_catalog import DIMENSIONS, GROUP_LABELS, GROUPS

WB_API = "https://api.worldbank.org/v2"
COUNTRIES = ["USA", "CHN", "JPN", "AUS", "CAN"]
START_YEAR = 2010
END_YEAR = 2024
OUT_PATH = Path(__file__).resolve().parents[1] / "data" / "snapshots" / "country_stats.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("snapshot")


def fetch_indicator(code: str) -> list[dict[str, Any]]:
    """Fetch one indicator for all target countries in one request."""
    url = f"{WB_API}/country/{';'.join(COUNTRIES)}/indicator/{code}"
    params = {
        "format": "json",
        "date": f"{START_YEAR}:{END_YEAR}",
        "per_page": 2000,
    }

    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                payload = resp.json()
                if isinstance(payload, list) and len(payload) >= 2:
                    return payload[1] or []
                return []
            log.warning("HTTP %s for %s", resp.status_code, code)
        except requests.RequestException as exc:
            log.warning("Request failed for %s (attempt %d): %s", code, attempt + 1, exc)

        if attempt < 2:
            wait_s = 2**attempt
            time.sleep(wait_s)

    return []


def apply_scale(raw_value: float, scale: float | None) -> float:
    if scale in (None, 0):
        return float(raw_value)
    return float(raw_value) / float(scale)


def build_snapshot() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []

    indicators = {dim["key"]: dim["wb_code"] for dim in DIMENSIONS}

    for dim in DIMENSIONS:
        indicator_key = dim["key"]
        wb_code = dim["wb_code"]
        group = dim["group"]
        scale = dim.get("scale")
        decimals = int(dim.get("decimals", 4))

        log.info("Fetching %s (%s)", indicator_key, wb_code)
        indicator_rows = 0

        for entry in fetch_indicator(wb_code):
            raw_value = entry.get("value")
            if raw_value is None:
                continue

            iso3 = entry.get("countryiso3code") or ""
            if iso3 not in COUNTRIES:
                continue

            try:
                year = int(entry.get("date"))
                value = round(apply_scale(float(raw_value), scale), decimals)
            except (TypeError, ValueError):
                continue

            rows.append(
                {
                    "indicator": indicator_key,
                    "indicator_code": wb_code,
                    "group": group,
                    "iso3": iso3,
                    "country": (entry.get("country") or {}).get("value") or iso3,
                    "year": year,
                    "value": value,
                }
            )
            indicator_rows += 1

        log.info("  %s rows accepted for %s", indicator_rows, indicator_key)
        time.sleep(0.4)

    rows.sort(key=lambda r: (r["group"], r["indicator"], r["iso3"], r["year"]))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "World Bank WDI v2 (https://api.worldbank.org/v2)",
        "countries": COUNTRIES,
        "indicators": indicators,
        "year_range": [START_YEAR, END_YEAR],
        "groups": GROUPS,
        "group_labels": GROUP_LABELS,
        "dimensions": DIMENSIONS,
        "row_count": len(rows),
        "rows": rows,
    }


def main() -> int:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    snapshot = build_snapshot()
    OUT_PATH.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    complete = len({r["indicator"] for r in snapshot["rows"]})
    log.info(
        "Wrote %d rows across %d indicators (%d series complete)",
        snapshot["row_count"],
        len(snapshot["indicators"]),
        complete,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
