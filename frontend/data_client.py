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
SNAPSHOT_PATH = REPO_ROOT / "data" / "snapshots" / "country_stats.json"

# Cached snapshot payload (built by scripts/build_snapshot.py from World Bank
# WDI v2). Read once and held in module scope for fast repeated access in
# Streamlit's rerun model.
_SNAPSHOT_CACHE: dict[str, Any] | None = None


# Fallback copy of etl/dimension_catalog.py (trimmed to fields needed by frontend)
_FALLBACK_DIMENSIONS: list[dict[str, Any]] = [
    {"key": "gdp", "label": "GDP", "wb_code": "NY.GDP.MKTP.CD", "group": "economy", "group_label": "Economy", "unit": "T$", "decimals": 2, "good_when": "high", "description": "Gross domestic product, current USD"},
    {"key": "gdp_growth", "label": "GDP growth", "wb_code": "NY.GDP.MKTP.KD.ZG", "group": "economy", "group_label": "Economy", "unit": "%", "decimals": 2, "good_when": "high", "description": "Annual GDP growth (constant prices)"},
    {"key": "cpi", "label": "Inflation", "wb_code": "FP.CPI.TOTL.ZG", "group": "economy", "group_label": "Economy", "unit": "%", "decimals": 2, "good_when": "low", "description": "Inflation, consumer prices (annual %)"},
    {"key": "unemployment", "label": "Unemployment", "wb_code": "SL.UEM.TOTL.ZS", "group": "economy", "group_label": "Economy", "unit": "%", "decimals": 2, "good_when": "low", "description": "Unemployment, total (% of labor force)"},
    {"key": "debt", "label": "Govt debt %GDP", "wb_code": "GC.DOD.TOTL.GD.ZS", "group": "economy", "group_label": "Economy", "unit": "%", "decimals": 2, "good_when": "low", "description": "Central government debt, total (% of GDP)"},
    {"key": "trade", "label": "Trade %GDP", "wb_code": "NE.TRD.GNFS.ZS", "group": "trade_finance", "group_label": "Trade & Finance", "unit": "%", "decimals": 2, "good_when": "neutral", "description": "Trade (% of GDP)"},
    {"key": "fdi", "label": "FDI inflows %GDP", "wb_code": "BX.KLT.DINV.WD.GD.ZS", "group": "trade_finance", "group_label": "Trade & Finance", "unit": "%", "decimals": 2, "good_when": "neutral", "description": "Foreign direct investment, net inflows (% of GDP)"},
    {"key": "savings", "label": "Gross savings %GDP", "wb_code": "NY.GNS.ICTR.ZS", "group": "trade_finance", "group_label": "Trade & Finance", "unit": "%", "decimals": 2, "good_when": "high", "description": "Gross savings (% of GDP)"},
    {"key": "tax", "label": "Tax revenue %GDP", "wb_code": "GC.TAX.TOTL.GD.ZS", "group": "trade_finance", "group_label": "Trade & Finance", "unit": "%", "decimals": 2, "good_when": "neutral", "description": "Tax revenue (% of GDP)"},
    {"key": "reserves", "label": "Reserves", "wb_code": "FI.RES.TOTL.CD", "group": "trade_finance", "group_label": "Trade & Finance", "unit": "B$", "decimals": 2, "good_when": "high", "description": "Total reserves (includes gold), current USD"},
    {"key": "pop_total", "label": "Population", "wb_code": "SP.POP.TOTL", "group": "society", "group_label": "Society", "unit": "M", "decimals": 2, "good_when": "high", "description": "Population, total"},
    {"key": "pop_aging", "label": "65+ %", "wb_code": "SP.POP.65UP.TO.ZS", "group": "society", "group_label": "Society", "unit": "%", "decimals": 2, "good_when": "neutral", "description": "Population ages 65 and above (% of total)"},
    {"key": "urban", "label": "Urban population %", "wb_code": "SP.URB.TOTL.IN.ZS", "group": "society", "group_label": "Society", "unit": "%", "decimals": 2, "good_when": "high", "description": "Urban population (% of total)"},
    {"key": "life_exp", "label": "Life expectancy", "wb_code": "SP.DYN.LE00.IN", "group": "society", "group_label": "Society", "unit": "yrs", "decimals": 2, "good_when": "high", "description": "Life expectancy at birth, total (years)"},
    {"key": "health", "label": "Health expenditure %GDP", "wb_code": "SH.XPD.CHEX.GD.ZS", "group": "society", "group_label": "Society", "unit": "%", "decimals": 2, "good_when": "high", "description": "Current health expenditure (% of GDP)"},
    {"key": "rd", "label": "R&D expenditure %GDP", "wb_code": "GB.XPD.RSDV.GD.ZS", "group": "innovation_environment", "group_label": "Innovation & Environment", "unit": "%", "decimals": 2, "good_when": "high", "description": "Research and development expenditure (% of GDP)"},
    {"key": "internet", "label": "Internet users %", "wb_code": "IT.NET.USER.ZS", "group": "innovation_environment", "group_label": "Innovation & Environment", "unit": "%", "decimals": 2, "good_when": "high", "description": "Individuals using the Internet (% of population)"},
    {"key": "education", "label": "Education spending %GDP", "wb_code": "SE.XPD.TOTL.GD.ZS", "group": "innovation_environment", "group_label": "Innovation & Environment", "unit": "%", "decimals": 2, "good_when": "high", "description": "Government expenditure on education, total (% of GDP)"},
    {"key": "energy", "label": "Energy use kgoe/cap", "wb_code": "EG.USE.PCAP.KG.OE", "group": "innovation_environment", "group_label": "Innovation & Environment", "unit": "kgoe", "decimals": 2, "good_when": "neutral", "description": "Energy use (kg of oil equivalent per capita)"},
    {"key": "co2", "label": "CO2 per capita", "wb_code": "EN.GHG.CO2.PC.CE.AR5", "group": "innovation_environment", "group_label": "Innovation & Environment", "unit": "tCO2", "decimals": 2, "good_when": "low", "description": "CO2 emissions (metric tons per capita, AR5 methodology)"},
]

_FALLBACK_GROUPS: list[dict[str, Any]] = [
    {"key": "economy", "label": "Economy", "indicators": ["gdp", "gdp_growth", "cpi", "unemployment", "debt"]},
    {"key": "trade_finance", "label": "Trade & Finance", "indicators": ["trade", "fdi", "savings", "tax", "reserves"]},
    {"key": "society", "label": "Society", "indicators": ["pop_total", "pop_aging", "urban", "life_exp", "health"]},
    {"key": "innovation_environment", "label": "Innovation & Environment", "indicators": ["rd", "internet", "education", "energy", "co2"]},
]


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


def load_snapshot() -> dict[str, Any] | None:
    """Return the offline World Bank snapshot, or None if unavailable.

    Built by ``scripts/build_snapshot.py``; baked into the repo so the
    Streamlit Cloud deployment has real numbers even without a backend.

    The result is memoized in module scope (``_SNAPSHOT_CACHE``) so repeated
    Streamlit reruns hit a hot cache instead of re-parsing JSON.
    """
    global _SNAPSHOT_CACHE
    if _SNAPSHOT_CACHE is not None:
        return _SNAPSHOT_CACHE
    if not SNAPSHOT_PATH.exists():
        return None
    try:
        _SNAPSHOT_CACHE = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        return _SNAPSHOT_CACHE
    except (OSError, ValueError):
        return None


def _catalog_dimensions() -> list[dict[str, Any]]:
    snap = load_snapshot()
    if snap and isinstance(snap.get("dimensions"), list) and snap["dimensions"]:
        return list(snap["dimensions"])
    return [dict(row) for row in _FALLBACK_DIMENSIONS]


def _build_indicators(dimensions: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indicators: dict[str, dict[str, Any]] = {}
    legacy_label_overrides = {
        "gdp": "GDP (USD trillions)",
        "cpi": "CPI inflation (%)",
        "unemployment": "Unemployment (%)",
        "debt": "Govt debt (% of GDP)",
        "tax": "Tax revenue (% of GDP)",
        "fdi": "FDI net inflows (% of GDP)",
        "health": "Health spending (% of GDP)",
    }
    for dim in dimensions:
        key = str(dim.get("key", "")).strip()
        if not key:
            continue
        indicators[key] = {
            "code": dim.get("wb_code") or dim.get("code") or "",
            "label": legacy_label_overrides.get(key, dim.get("label") or key),
            "unit": dim.get("unit") or "",
            "group": dim.get("group") or "",
            "group_label": dim.get("group_label") or "",
            "decimals": int(dim.get("decimals", 2)),
            "good_when": dim.get("good_when") or "neutral",
            "description": dim.get("description") or "",
        }
    return indicators


def _build_dimension_groups(
    dimensions: list[dict[str, Any]],
    indicators: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    snap = load_snapshot() or {}
    group_labels: dict[str, str] = {}
    if isinstance(snap.get("group_labels"), dict):
        group_labels = {str(k): str(v) for k, v in snap["group_labels"].items()}

    by_group: dict[str, list[str]] = {}
    order: list[str] = []
    for dim in dimensions:
        key = str(dim.get("key", "")).strip()
        group = str(dim.get("group", "")).strip()
        if not key or not group or key not in indicators:
            continue
        if group not in by_group:
            by_group[group] = []
            order.append(group)
        by_group[group].append(key)
        if group not in group_labels and dim.get("group_label"):
            group_labels[group] = str(dim["group_label"])

    out: list[dict[str, Any]] = []
    for group in order:
        out.append(
            {
                "key": group,
                "label": group_labels.get(group, group.replace("_", " ").title()),
                "indicators": by_group.get(group, []),
            }
        )

    if not out:
        return [dict(g) for g in _FALLBACK_GROUPS]
    return out


def _load_indicator_catalog() -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    dims = _catalog_dimensions()
    indicators = _build_indicators(dims)
    if not indicators:
        indicators = _build_indicators([dict(row) for row in _FALLBACK_DIMENSIONS])
        return indicators, [dict(g) for g in _FALLBACK_GROUPS]
    groups = _build_dimension_groups(dims, indicators)
    if not groups:
        groups = [dict(g) for g in _FALLBACK_GROUPS]
    return indicators, groups


INDICATORS, DIMENSION_GROUPS = _load_indicator_catalog()


def get_year_range() -> tuple[int, int]:
    snap = load_snapshot()
    if snap:
        years = snap.get("year_range")
        if isinstance(years, (list, tuple)) and len(years) == 2:
            try:
                start = int(years[0])
                end = int(years[1])
                return (start, end)
            except (TypeError, ValueError):
                pass
    return (2010, 2026)


def format_value(key: str, value: float | None) -> str:
    if value is None:
        return "—"
    meta = INDICATORS.get(key, {})
    decimals = int(meta.get("decimals", 2))
    unit = str(meta.get("unit", "")).strip()
    if key in {"pop_total", "reserves"}:
        return f"{value:,.{decimals}f} {unit}".strip()
    return f"{value:.{decimals}f} {unit}".strip()


def check_health(timeout: float = 1.5) -> HealthStatus:
    url = get_backend_url()
    try:
        resp = requests.get(f"{url}/health", timeout=timeout)
        if resp.ok:
            return HealthStatus(True, "Backend online", url)
        return HealthStatus(False, f"Backend returned HTTP {resp.status_code}", url)
    except requests.RequestException as exc:
        snap = load_snapshot()
        if snap:
            generated = snap.get("generated_at", "unknown")
            return HealthStatus(
                False,
                f"Offline mode — World Bank snapshot ({snap.get('row_count', 0)} rows, generated {generated[:10]})",
                url,
            )
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


def snapshot_rows_for(
    iso_codes: list[str],
    indicator_key: str,
    year_start: int,
    year_end: int,
) -> list[dict[str, Any]]:
    snap = load_snapshot()
    if not snap:
        return []
    wanted = set(iso_codes)
    out: list[dict[str, Any]] = []
    for row in snap.get("rows", []):
        if row.get("indicator") != indicator_key:
            continue
        iso3 = row.get("iso3")
        if iso3 not in wanted:
            continue
        year = int(row.get("year", 0))
        if not (year_start <= year <= year_end):
            continue
        value = float(row["value"])
        out.append(
            {
                "year": year,
                "iso3": iso3,
                "country": COUNTRY_META.get(iso3, {}).get("name", row.get("country", iso3)),
                "value": round(value, 4),
                "indicator": indicator_key,
                "source": "snapshot",
            }
        )
    out.sort(key=lambda r: (r["iso3"], r["year"]))
    return out


def get_country_table(prefer_backend: bool = True) -> tuple[pd.DataFrame, str]:
    """Return a DataFrame of countries plus the data source tag."""
    if prefer_backend:
        rows = fetch_countries()
        if rows:
            return pd.DataFrame(rows), "backend"

    # Synthesize a small country table from the snapshot's latest GDP rows so
    # the dashboard's overview cards have real numbers even in offline mode.
    year_start, year_end = get_year_range()
    snap_rows = snapshot_rows_for(list(COUNTRY_META.keys()), "gdp", year_start, year_end)
    if snap_rows:
        by_iso: dict[str, dict[str, Any]] = {}
        for r in snap_rows:
            cur = by_iso.get(r["iso3"])
            if cur is None or r["year"] > cur["year"]:
                by_iso[r["iso3"]] = r
        rows = []
        for iso3, r in by_iso.items():
            rows.append(
                {
                    "iso3": iso3,
                    "country": r["country"],
                    "region": COUNTRY_META[iso3]["region"],
                    "gdpTrillions": r["value"],
                    "latestYear": r["year"],
                    "source": "snapshot",
                }
            )
        return pd.DataFrame(rows), "snapshot"

    fixture_rows = load_fixture_countries()
    return pd.DataFrame(fixture_rows), "fixture"


def _synth_series(iso3: str, indicator_key: str, years: Iterable[int]) -> list[float]:
    """Deterministic synthetic time series for a (country, indicator) pair."""
    seed = abs(hash((iso3, indicator_key))) % (2**31)
    rng = random.Random(seed)
    base_by_indicator = {
        "gdp": {"USA": 23.0, "CHN": 17.5, "JPN": 4.2, "AUS": 1.6, "CAN": 2.0},
        "gdp_growth": {"USA": 2.0, "CHN": 5.0, "JPN": 1.0, "AUS": 2.3, "CAN": 2.1},
        "cpi": {"USA": 3.2, "CHN": 1.0, "JPN": 1.5, "AUS": 4.0, "CAN": 2.8},
        "unemployment": {"USA": 4.0, "CHN": 5.2, "JPN": 2.7, "AUS": 4.1, "CAN": 5.5},
        "debt": {"USA": 120.0, "CHN": 75.0, "JPN": 250.0, "AUS": 50.0, "CAN": 105.0},
        "trade": {"USA": 25.0, "CHN": 37.0, "JPN": 35.0, "AUS": 45.0, "CAN": 67.0},
        "fdi": {"USA": 2.0, "CHN": 1.5, "JPN": 0.8, "AUS": 3.0, "CAN": 2.5},
        "savings": {"USA": 18.0, "CHN": 45.0, "JPN": 30.0, "AUS": 24.0, "CAN": 20.0},
        "tax": {"USA": 11.0, "CHN": 9.0, "JPN": 12.0, "AUS": 23.0, "CAN": 14.0},
        "reserves": {"USA": 35.0, "CHN": 3200.0, "JPN": 1200.0, "AUS": 80.0, "CAN": 120.0},
        "pop_total": {"USA": 335.0, "CHN": 1410.0, "JPN": 124.0, "AUS": 26.0, "CAN": 40.0},
        "pop_aging": {"USA": 17.0, "CHN": 14.0, "JPN": 29.0, "AUS": 17.0, "CAN": 19.0},
        "urban": {"USA": 83.0, "CHN": 66.0, "JPN": 92.0, "AUS": 86.0, "CAN": 82.0},
        "life_exp": {"USA": 78.0, "CHN": 78.0, "JPN": 84.0, "AUS": 83.0, "CAN": 82.0},
        "health": {"USA": 17.5, "CHN": 5.5, "JPN": 11.0, "AUS": 9.5, "CAN": 11.5},
        "rd": {"USA": 3.4, "CHN": 2.6, "JPN": 3.2, "AUS": 1.8, "CAN": 1.7},
        "internet": {"USA": 93.0, "CHN": 78.0, "JPN": 94.0, "AUS": 96.0, "CAN": 95.0},
        "education": {"USA": 4.9, "CHN": 4.0, "JPN": 3.3, "AUS": 5.0, "CAN": 5.2},
        "energy": {"USA": 6800.0, "CHN": 2500.0, "JPN": 3400.0, "AUS": 5400.0, "CAN": 7500.0},
        "co2": {"USA": 14.0, "CHN": 8.0, "JPN": 8.5, "AUS": 15.0, "CAN": 14.5},
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
    year_end: int = 2026,
) -> pd.DataFrame:
    """Long-format DataFrame: year, iso3, country, value, indicator, source."""
    years = list(range(year_start, year_end + 1))

    # Priority order:
    #  1. Live backend /compare (when running locally with docker compose)
    #  2. Bundled World Bank snapshot (for Streamlit Cloud / offline mode)
    #  3. Deterministic synthetic series (last-resort UI safety net)
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

    # Snapshot (real data from World Bank, baked at deploy time).
    snap_rows = snapshot_rows_for(iso_codes, indicator_key, year_start, year_end)
    if snap_rows:
        return pd.DataFrame(snap_rows)

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
