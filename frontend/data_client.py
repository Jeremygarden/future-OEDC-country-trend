"""Backend HTTP client + fallback fixture loader for the dashboard.

Adds a thin requests-based client around the Fastify backend:
  GET {BACKEND_API_URL}/health
  GET {BACKEND_API_URL}/countries
  GET {BACKEND_API_URL}/countries/summary
  GET {BACKEND_API_URL}/indicators?country=ISO3      (optional, since iter-2)
  GET {BACKEND_API_URL}/compare?countries=...&indicator=...   (optional)

When the backend is unreachable, callers fall back to the bundled fixture
(``fixtures/countries.sample.json``) plus deterministic synthetic time-series
for indicators not exposed by the simple list endpoint. Synthetic series are
clearly labeled in the UI as ``source=synthetic`` so they never masquerade
as real data.
"""
from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import requests

DEFAULT_BACKEND_URL = "http://localhost:3000/api/v1"

# fixtures/ is two levels above this file (frontend/data_client.py -> repo/)
REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPO_ROOT / "fixtures" / "countries.sample.json"

INDICATORS = {
    "gdp": {"label": "GDP (USD trillions)", "unit": "T$", "code": "NY.GDP.MKTP.CD"},
    "cpi": {"label": "CPI inflation (%)", "unit": "%", "code": "FP.CPI.TOTL.ZG"},
    "unemployment": {"label": "Unemployment (%)", "unit": "%", "code": "SL.UEM.TOTL.ZS"},
    "debt": {"label": "Govt debt (% of GDP)", "unit": "%", "code": "GC.DOD.TOTL.GD.ZS"},
    "energy": {"label": "Energy use per capita (kg oil eq.)", "unit": "kgoe", "code": "EG.USE.PCAP.KG.OE"},
    "tax": {"label": "Tax revenue (% of GDP)", "unit": "%", "code": "GC.TAX.TOTL.GD.ZS"},
    "fdi": {"label": "FDI net inflows (% of GDP)", "unit": "%", "code": "BX.KLT.DINV.WD.GD.ZS"},
    "savings": {"label": "Household savings (% of disposable income)", "unit": "%", "code": "SAVE_HH"},
    "health": {"label": "Health spending (% of GDP)", "unit": "%", "code": "SH.XPD.CHEX.GD.ZS"},
}

COUNTRY_META = {
    "USA": {"name": "United States", "flag": "🇺🇸", "region": "North America"},
    "CHN": {"name": "China", "flag": "🇨🇳", "region": "East Asia"},
    "JPN": {"name": "Japan", "flag": "🇯🇵", "region": "East Asia"},
    "AUS": {"name": "Australia", "flag": "🇦🇺", "region": "Oceania"},
    "CAN": {"name": "Canada", "flag": "🇨🇦", "region": "North America"},
}


@dataclass(frozen=True)
class HealthStatus:
    online: bool
    message: str
    backend_url: str


def get_backend_url() -> str:
    return os.environ.get("BACKEND_API_URL", DEFAULT_BACKEND_URL).rstrip("/")


def check_health(timeout: float = 1.5) -> HealthStatus:
    url = get_backend_url()
    try:
        resp = requests.get(f"{url}/health", timeout=timeout)
        if resp.ok:
            return HealthStatus(True, "Backend online", url)
        return HealthStatus(False, f"Backend returned HTTP {resp.status_code}", url)
    except requests.RequestException as exc:
        return HealthStatus(False, f"Backend unreachable: {exc.__class__.__name__}", url)


def fetch_countries(timeout: float = 3.0) -> list[dict[str, Any]] | None:
    url = get_backend_url()
    try:
        resp = requests.get(f"{url}/countries", timeout=timeout)
        if not resp.ok:
            return None
        payload = resp.json()
        if isinstance(payload, dict) and "items" in payload:
            return list(payload["items"])
        if isinstance(payload, list):
            return payload
        return None
    except (requests.RequestException, ValueError):
        return None


def fetch_compare(
    iso_codes: list[str], indicator_code: str, timeout: float = 3.0
) -> list[dict[str, Any]] | None:
    """Try the optional `/compare` endpoint; return None if unavailable."""
    url = get_backend_url()
    if not iso_codes or not indicator_code:
        return None
    try:
        resp = requests.get(
            f"{url}/compare",
            params={"countries": ",".join(iso_codes), "indicator": indicator_code},
            timeout=timeout,
        )
        if not resp.ok:
            return None
        payload = resp.json()
        if isinstance(payload, dict) and isinstance(payload.get("items"), list):
            return list(payload["items"])
        return None
    except (requests.RequestException, ValueError):
        return None


def load_fixture_countries() -> list[dict[str, Any]]:
    if not FIXTURE_PATH.exists():
        return []
    try:
        return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def get_country_table(prefer_backend: bool = True) -> tuple[pd.DataFrame, str]:
    """Return a DataFrame of countries plus the data source tag."""
    if prefer_backend:
        rows = fetch_countries()
        if rows:
            return pd.DataFrame(rows), "backend"
    fixture_rows = load_fixture_countries()
    return pd.DataFrame(fixture_rows), "fixture"


def _synth_series(iso3: str, indicator_key: str, years: Iterable[int]) -> list[float]:
    """Deterministic synthetic time series for a (country, indicator) pair."""
    seed = abs(hash((iso3, indicator_key))) % (2**31)
    rng = random.Random(seed)
    base_by_indicator = {
        "gdp": {"USA": 23.0, "CHN": 17.5, "JPN": 4.2, "AUS": 1.6, "CAN": 2.0},
        "cpi": {"USA": 3.2, "CHN": 1.0, "JPN": 1.5, "AUS": 4.0, "CAN": 2.8},
        "unemployment": {"USA": 4.0, "CHN": 5.2, "JPN": 2.7, "AUS": 4.1, "CAN": 5.5},
        "debt": {"USA": 120.0, "CHN": 75.0, "JPN": 250.0, "AUS": 50.0, "CAN": 105.0},
        "energy": {"USA": 6800.0, "CHN": 2500.0, "JPN": 3400.0, "AUS": 5400.0, "CAN": 7500.0},
        "tax": {"USA": 11.0, "CHN": 9.0, "JPN": 12.0, "AUS": 23.0, "CAN": 14.0},
        "fdi": {"USA": 2.0, "CHN": 1.5, "JPN": 0.8, "AUS": 3.0, "CAN": 2.5},
        "savings": {"USA": 7.0, "CHN": 30.0, "JPN": 4.0, "AUS": 5.0, "CAN": 6.0},
        "health": {"USA": 17.5, "CHN": 5.5, "JPN": 11.0, "AUS": 9.5, "CAN": 11.5},
    }
    base = base_by_indicator.get(indicator_key, {}).get(iso3, 5.0)
    out: list[float] = []
    drift = 0.0
    for _ in years:
        drift += rng.uniform(-0.04, 0.05)
        v = max(0.0, base * (1.0 + drift))
        out.append(round(v, 3))
    return out


def get_indicator_timeseries(
    iso_codes: list[str],
    indicator_key: str,
    year_start: int = 2015,
    year_end: int = 2024,
) -> pd.DataFrame:
    """Long-format DataFrame: year, iso3, country, value, indicator, source."""
    years = list(range(year_start, year_end + 1))

    # Try real backend /compare first.
    code = INDICATORS.get(indicator_key, {}).get("code")
    if code:
        backend_rows = fetch_compare(iso_codes, code)
        if backend_rows:
            records: list[dict[str, Any]] = []
            for entry in backend_rows:
                iso3 = (entry.get("countryCode") or "").upper()
                cname = entry.get("countryName") or COUNTRY_META.get(iso3, {}).get("name", iso3)
                for pt in entry.get("points") or []:
                    year = pt.get("year")
                    val = pt.get("value")
                    if year is None or val is None:
                        continue
                    if year_start <= int(year) <= year_end:
                        records.append(
                            {
                                "year": int(year),
                                "iso3": iso3,
                                "country": cname,
                                "value": float(val),
                                "indicator": indicator_key,
                                "source": "backend",
                            }
                        )
            if records:
                return pd.DataFrame(records)

    # Fallback: deterministic synthetic.
    records = []
    for iso3 in iso_codes:
        meta = COUNTRY_META.get(iso3, {"name": iso3, "flag": ""})
        values = _synth_series(iso3, indicator_key, years)
        for year, value in zip(years, values):
            records.append(
                {
                    "year": year,
                    "iso3": iso3,
                    "country": meta["name"],
                    "value": value,
                    "indicator": indicator_key,
                    "source": "synthetic",
                }
            )
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# KPI helpers (iteration 3)
# ---------------------------------------------------------------------------

def latest_value_per_country(df: pd.DataFrame) -> pd.DataFrame:
    """Return the most-recent (year, value) per country, with YoY change.

    Input: long-format DataFrame from ``get_indicator_timeseries``.
    Output columns: iso3, country, year, value, prev_value, yoy_pct.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["iso3", "country", "year", "value", "prev_value", "yoy_pct"])

    sorted_df = df.sort_values(["iso3", "year"])
    rows: list[dict[str, Any]] = []
    for iso3, group in sorted_df.groupby("iso3", sort=False):
        if group.empty:
            continue
        latest = group.iloc[-1]
        prev = group.iloc[-2] if len(group) >= 2 else None
        prev_value = float(prev["value"]) if prev is not None else None
        latest_value = float(latest["value"])
        yoy = None
        if prev_value not in (None, 0):
            yoy = round(((latest_value - prev_value) / abs(prev_value)) * 100.0, 2)
        rows.append(
            {
                "iso3": iso3,
                "country": str(latest["country"]),
                "year": int(latest["year"]),
                "value": latest_value,
                "prev_value": prev_value,
                "yoy_pct": yoy,
            }
        )
    return pd.DataFrame(rows)


def rank_countries(df_latest: pd.DataFrame, ascending: bool = False) -> pd.DataFrame:
    """Add a 1-based ``rank`` column based on ``value``.

    Default is descending (rank 1 = highest value).
    """
    if df_latest is None or df_latest.empty:
        return df_latest
    out = df_latest.copy()
    out["rank"] = (
        out["value"].rank(ascending=ascending, method="min").astype("Int64")
    )
    return out.sort_values("rank")
