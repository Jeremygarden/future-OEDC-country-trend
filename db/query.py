#!/usr/bin/env python3
"""
Query layer for the country stats dashboard.

Provides high-level functions to query the database for dashboard data.
All functions return JSON-serializable dicts.
"""
import sys
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from models.base import SessionLocal
from models.models import Country, Indicator, DataPoint, DataSource, EtlRun
from etl.transform import normalize_value, compute_yoy_change, compute_cagr

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TARGET_COUNTRIES = ["USA", "CHN", "JPN", "AUS", "CAN"]


def get_country_stats(iso3: str, years: Optional[list[int]] = None) -> dict:
    """
    Get all indicators for a specific country.
    
    Args:
        iso3: 3-letter ISO country code (USA, CHN, JPN, AUS, CAN)
        years: Optional list of years to filter; None = all years
    
    Returns:
        {
          "country": {iso3, name, region},
          "indicators": {
            "NY.GDP.MKTP.CD": {
              "name": "GDP (current USD)",
              "unit": "USD",
              "values": [{year, value, yoy_change}, ...]
            },
            ...
          }
        }
    """
    db = SessionLocal()
    try:
        country = db.query(Country).filter_by(iso3=iso3.upper()).first()
        if not country:
            raise ValueError(f"Country not found: {iso3}")
        
        indicators = db.query(Indicator).all()
        result = {
            "country": {
                "iso3": country.iso3,
                "iso2": country.iso2,
                "name": country.name,
                "region": country.region,
                "income_group": country.income_group
            },
            "indicators": {},
            "last_updated": datetime.utcnow().isoformat()
        }
        
        for indicator in indicators:
            query = db.query(DataPoint).filter_by(
                country_id=country.id,
                indicator_id=indicator.id
            ).order_by(DataPoint.year)
            
            if years:
                query = query.filter(DataPoint.year.in_(years))
            
            points = query.all()
            if not points:
                continue
            
            values = [
                {"year": p.year, "value": normalize_value(p.value, indicator.code)}
                for p in points
            ]
            values_with_yoy = compute_yoy_change(values)
            cagr = compute_cagr(values, n_years=5)
            
            result["indicators"][indicator.code] = {
                "name": indicator.name,
                "unit": indicator.unit,
                "category": indicator.category,
                "values": values_with_yoy,
                "cagr_5y": cagr,
                "latest": values_with_yoy[-1] if values_with_yoy else None
            }
        
        return result
    finally:
        db.close()


def get_indicator_trend(indicator_code: str, 
                        countries: Optional[list[str]] = None,
                        start_year: int = 2015,
                        end_year: int = 2024) -> dict:
    """
    Get time-series data for a specific indicator across countries.
    
    Args:
        indicator_code: Indicator code (e.g., 'NY.GDP.MKTP.CD')
        countries: List of ISO3 codes; None = all 5 target countries
        start_year: Start year (inclusive)
        end_year: End year (inclusive)
    
    Returns:
        {
          "indicator": {code, name, unit, category},
          "countries": {
            "USA": [{year, value, yoy_change}, ...],
            "CHN": [...],
            ...
          }
        }
    """
    if countries is None:
        countries = TARGET_COUNTRIES
    
    db = SessionLocal()
    try:
        indicator = db.query(Indicator).filter_by(code=indicator_code).first()
        if not indicator:
            raise ValueError(f"Indicator not found: {indicator_code}")
        
        result = {
            "indicator": {
                "code": indicator.code,
                "name": indicator.name,
                "unit": indicator.unit,
                "category": indicator.category,
                "description": indicator.description
            },
            "countries": {}
        }
        
        for iso3 in countries:
            country = db.query(Country).filter_by(iso3=iso3.upper()).first()
            if not country:
                continue
            
            points = db.query(DataPoint).filter(
                DataPoint.country_id == country.id,
                DataPoint.indicator_id == indicator.id,
                DataPoint.year.between(start_year, end_year)
            ).order_by(DataPoint.year).all()
            
            if not points:
                continue
            
            values = [
                {"year": p.year, "value": normalize_value(p.value, indicator_code)}
                for p in points
            ]
            result["countries"][iso3] = compute_yoy_change(values)
        
        return result
    finally:
        db.close()


def get_latest_comparison() -> dict:
    """
    Get latest values for all 5 countries across all indicators.
    
    Returns side-by-side comparison dict:
    {
      "updated_at": "...",
      "countries": {
        "USA": {
          "name": "United States",
          "indicators": {
            "NY.GDP.MKTP.CD": {"value": 27.36, "year": 2023, "unit": "USD"},
            ...
          }
        }
      },
      "rankings": {
        "NY.GDP.MKTP.CD": {"USA": 1, "CHN": 2, ...}
      }
    }
    """
    db = SessionLocal()
    try:
        from etl.transform import compute_country_rank
        
        result = {
            "updated_at": datetime.utcnow().isoformat(),
            "countries": {},
            "rankings": {}
        }
        
        indicators = db.query(Indicator).all()
        
        # Initialize country entries
        for iso3 in TARGET_COUNTRIES:
            country = db.query(Country).filter_by(iso3=iso3).first()
            if country:
                result["countries"][iso3] = {
                    "name": country.name,
                    "iso2": country.iso2,
                    "region": country.region,
                    "indicators": {}
                }
        
        # Collect latest values per indicator
        for indicator in indicators:
            indicator_values = {}
            
            for iso3 in TARGET_COUNTRIES:
                if iso3 not in result["countries"]:
                    continue
                
                country = db.query(Country).filter_by(iso3=iso3).first()
                if not country:
                    continue
                
                # Get latest year's data
                latest_point = db.query(DataPoint).filter(
                    DataPoint.country_id == country.id,
                    DataPoint.indicator_id == indicator.id
                ).order_by(DataPoint.year.desc()).first()
                
                if latest_point and latest_point.value is not None:
                    normalized = normalize_value(latest_point.value, indicator.code)
                    result["countries"][iso3]["indicators"][indicator.code] = {
                        "value": normalized,
                        "raw_value": latest_point.value,
                        "year": latest_point.year,
                        "unit": indicator.unit,
                        "name": indicator.name
                    }
                    indicator_values[iso3] = normalized
            
            # Compute rankings for this indicator
            if indicator_values:
                ascending = indicator.code in ("SL.UEM.TOTL.ZS", "FP.CPI.TOTL.ZG", "LRHUTTTT")
                result["rankings"][indicator.code] = compute_country_rank(
                    indicator_values, ascending=ascending
                )
        
        return result
    finally:
        db.close()


def search_indicators(keyword: str) -> list[dict]:
    """
    Search for indicators by keyword in code, name, or description.
    
    Args:
        keyword: Search term
    
    Returns:
        List of matching indicator dicts
    """
    db = SessionLocal()
    try:
        keyword_lower = f"%{keyword.lower()}%"
        
        indicators = db.query(Indicator).filter(
            text(
                "LOWER(code) LIKE :kw OR LOWER(name) LIKE :kw OR LOWER(description) LIKE :kw OR LOWER(category) LIKE :kw"
            )
        ).params(kw=keyword_lower).all()
        
        results = []
        for ind in indicators:
            source = db.query(DataSource).filter_by(id=ind.source_id).first()
            results.append({
                "code": ind.code,
                "name": ind.name,
                "description": ind.description,
                "unit": ind.unit,
                "category": ind.category,
                "source": source.name if source else None
            })
        
        return results
    finally:
        db.close()


def get_etl_status() -> list[dict]:
    """Get recent ETL run history."""
    db = SessionLocal()
    try:
        runs = db.query(EtlRun).order_by(EtlRun.started_at.desc()).limit(20).all()
        result = []
        for run in runs:
            source = db.query(DataSource).filter_by(id=run.source_id).first()
            result.append({
                "id": run.id,
                "source": source.name if source else "unknown",
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                "status": run.status,
                "records_fetched": run.records_fetched,
                "records_upserted": run.records_upserted,
                "error_msg": run.error_msg
            })
        return result
    finally:
        db.close()


if __name__ == "__main__":
    # Quick demo
    import json
    
    print("Testing query layer...")
    
    # Search for GDP indicators
    gdp_inds = search_indicators("gdp")
    print(f"\
GDP indicators ({len(gdp_inds)}):")
    for ind in gdp_inds[:3]:
        print(f"  {ind['code']}: {ind['name']}")
    
    # Try comparison
    try:
        comp = get_latest_comparison()
        print(f"\
Countries with data: {list(comp['countries'].keys())}")
    except Exception as e:
        print(f"Comparison failed (expected if no data): {e}")
