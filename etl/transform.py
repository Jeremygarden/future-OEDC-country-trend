#!/usr/bin/env python3
"""
Data transformation and aggregation layer for the country stats dashboard.

Handles:
- Data normalization and cleaning
- Derived metrics computation (YoY change, CAGR, rank)
- Data quality flags
"""
import sys
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from models.base import SessionLocal
from models.models import Country, Indicator, DataPoint, DataSource

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Countries to rank
TARGET_COUNTRIES = ["USA", "CHN", "JPN", "AUS", "CAN"]


def normalize_value(value: float, indicator_code: str) -> Optional[float]:
    """
    Normalize raw values for display:
    - GDP values to trillions USD for readability
    - Percentages left as-is
    - Population to billions
    """
    if value is None:
        return None
    
    # GDP indicators - convert to trillions
    if indicator_code in ("NY.GDP.MKTP.CD", "NY.GDP.PCAP.CD"):
        return round(value / 1e12, 4) if abs(value) > 1e9 else value
    
    # Population - convert to billions
    if indicator_code == "SP.POP.TOTL":
        return round(value / 1e9, 4) if value > 1e6 else value
    
    # Percentages - round to 2 decimal places
    if indicator_code in ("NY.GDP.MKTP.KD.ZG", "FP.CPI.TOTL.ZG", 
                           "SL.UEM.TOTL.ZS", "NE.TRD.GNFS.ZS",
                           "BX.KLT.DINV.WD.GD.ZS", "GC.DOD.TOTL.GD.ZS",
                           "LRHUTTTT", "CPALTT01", "GGXWDG_NGDP", "CA_GDP"):
        return round(value, 2)
    
    return round(value, 4)


def compute_yoy_change(values: list[dict]) -> list[dict]:
    """
    Compute year-over-year percentage change for a time series.
    Input: list of {year, value} sorted by year ascending.
    Output: same list with 'yoy_change' field added.
    """
    if not values:
        return values
    
    # Sort by year
    sorted_vals = sorted(values, key=lambda x: x["year"])
    
    for i, item in enumerate(sorted_vals):
        if i == 0 or sorted_vals[i-1]["value"] is None or item["value"] is None:
            item["yoy_change"] = None
        else:
            prev_val = sorted_vals[i-1]["value"]
            if prev_val != 0:
                yoy = ((item["value"] - prev_val) / abs(prev_val)) * 100
                item["yoy_change"] = round(yoy, 2)
            else:
                item["yoy_change"] = None
    
    return sorted_vals


def compute_cagr(values: list[dict], n_years: int = 5) -> Optional[float]:
    """
    Compute Compound Annual Growth Rate over the last n_years.
    
    CAGR = (end_value / start_value) ^ (1/n_years) - 1
    """
    if not values or len(values) < 2:
        return None
    
    sorted_vals = sorted(values, key=lambda x: x["year"])
    
    # Find n_years-ago value
    latest = sorted_vals[-1]
    target_start_year = latest["year"] - n_years
    
    start_val_item = next(
        (v for v in reversed(sorted_vals) if v["year"] <= target_start_year),
        None
    )
    
    if not start_val_item or start_val_item["value"] is None or latest["value"] is None:
        return None
    
    start_val = start_val_item["value"]
    end_val = latest["value"]
    actual_years = latest["year"] - start_val_item["year"]
    
    if start_val <= 0 or actual_years <= 0:
        return None
    
    try:
        cagr = (end_val / start_val) ** (1 / actual_years) - 1
        return round(cagr * 100, 2)  # Return as percentage
    except (ZeroDivisionError, ValueError):
        return None


def compute_country_rank(values_by_country: dict[str, float], ascending: bool = False) -> dict[str, int]:
    """
    Rank countries by a metric value.
    ascending=False: highest value = rank 1 (e.g., GDP)
    ascending=True: lowest value = rank 1 (e.g., unemployment)
    """
    valid = {k: v for k, v in values_by_country.items() if v is not None}
    if not valid:
        return {}
    
    sorted_countries = sorted(valid.keys(), key=lambda x: valid[x], reverse=not ascending)
    return {country: rank + 1 for rank, country in enumerate(sorted_countries)}


def flag_outliers(values: list[float], threshold_std: float = 3.0) -> list[bool]:
    """
    Flag values that are outliers using the IQR (interquartile range) method.
    More robust than mean+std because it's not affected by the outliers themselves.
    
    Values > Q3 + 1.5*IQR or < Q1 - 1.5*IQR are flagged as outliers.
    The threshold_std parameter scales the IQR multiplier (default 1.5).
    
    Returns a boolean list: True = outlier.
    """
    if len(values) < 3:
        return [False] * len(values)
    
    valid = sorted([v for v in values if v is not None])
    if not valid:
        return [False] * len(values)
    
    n = len(valid)
    
    # Compute quartiles
    q1_idx = n // 4
    q3_idx = 3 * n // 4
    q1 = valid[q1_idx]
    q3 = valid[min(q3_idx, n - 1)]
    iqr = q3 - q1
    
    if iqr == 0:
        # Fallback to mean+std if IQR is 0 (all same values)
        mean = sum(valid) / len(valid)
        variance = sum((v - mean) ** 2 for v in valid) / len(valid)
        std = variance ** 0.5
        if std == 0:
            return [False] * len(values)
        return [
            abs(v - mean) > threshold_std * std if v is not None else False
            for v in values
        ]
    
    # IQR multiplier: threshold_std=3 → multiplier=1.5, threshold_std=2 → multiplier=1.0
    multiplier = 1.5 * (threshold_std / 3.0)
    lower = q1 - multiplier * iqr
    upper = q3 + multiplier * iqr
    
    return [
        v < lower or v > upper if v is not None else False
        for v in values
    ]


class DataTransformer:
    def __init__(self, db=None):
        self.db = db or SessionLocal()
        self._own_session = db is None
    
    def get_country_time_series(self, iso3: str, indicator_code: str) -> list[dict]:
        """Get time series data for a country/indicator pair."""
        country = self.db.query(Country).filter_by(iso3=iso3).first()
        indicator = self.db.query(Indicator).filter_by(code=indicator_code).first()
        
        if not country or not indicator:
            return []
        
        points = self.db.query(DataPoint).filter_by(
            country_id=country.id,
            indicator_id=indicator.id
        ).order_by(DataPoint.year).all()
        
        return [
            {
                "year": p.year,
                "value": normalize_value(p.value, indicator_code)
            }
            for p in points
        ]
    
    def get_latest_value(self, iso3: str, indicator_code: str) -> Optional[float]:
        """Get the most recent value for a country/indicator."""
        series = self.get_country_time_series(iso3, indicator_code)
        if not series:
            return None
        return max(series, key=lambda x: x["year"])["value"]
    
    def compute_all_derived_metrics(self) -> dict:
        """
        Compute derived metrics for all countries and indicators.
        Returns a nested dict: {indicator_code: {iso3: {metrics}}}
        """
        logger.info("Computing derived metrics...")
        
        indicators = self.db.query(Indicator).all()
        results = {}
        
        for indicator in indicators:
            code = indicator.code
            results[code] = {}
            
            # Get latest values per country for ranking
            latest_by_country = {}
            
            for iso3 in TARGET_COUNTRIES:
                series = self.get_country_time_series(iso3, code)
                if not series:
                    continue
                
                # Add YoY change
                series_with_yoy = compute_yoy_change(series)
                
                # Get latest
                latest = max(series_with_yoy, key=lambda x: x["year"]) if series_with_yoy else None
                if latest:
                    latest_by_country[iso3] = latest["value"]
                
                # Compute CAGR
                cagr = compute_cagr(series, n_years=5)
                
                results[code][iso3] = {
                    "series": series_with_yoy,
                    "latest": latest,
                    "cagr_5y": cagr,
                    "indicator_name": indicator.name
                }
            
            # Compute ranks (GDP: higher = better; unemployment: lower = better)
            ascending = code in ("SL.UEM.TOTL.ZS", "FP.CPI.TOTL.ZG", "LRHUTTTT")
            ranks = compute_country_rank(latest_by_country, ascending=ascending)
            
            for iso3, rank in ranks.items():
                if iso3 in results[code]:
                    results[code][iso3]["rank"] = rank
        
        logger.info(f"Computed metrics for {len(results)} indicators")
        return results
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        if self._own_session:
            self.db.close()


def run_transformations():
    """Run all data transformations and return summary."""
    transformer = DataTransformer()
    metrics = transformer.compute_all_derived_metrics()
    
    # Summary
    total_series = sum(len(v) for v in metrics.values())
    logger.info(f"Transformation complete: {len(metrics)} indicators, {total_series} country series")
    
    return metrics


if __name__ == "__main__":
    metrics = run_transformations()
    print(f"Transformations complete: {len(metrics)} indicators processed")
