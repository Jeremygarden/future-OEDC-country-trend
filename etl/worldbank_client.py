#!/usr/bin/env python3
"""
World Bank Data360 API ETL Client.

Fetches macroeconomic indicators for US, China, Japan, Australia, Canada
from the World Bank Data360 API and stores them in the SQLite database.

API docs: https://data360.worldbank.org/en/api
Fallback: World Bank WDI API v2 https://api.worldbank.org/v2
"""
import sys
import time
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from models.base import SessionLocal
from models.models import Country, DataSource, Indicator, DataPoint, EtlRun

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# World Bank WDI API (most reliable public API)
WB_API_BASE = "https://api.worldbank.org/v2"
# World Bank Data360 API
WB_DATA360_BASE = "https://data360.worldbank.org/api"

# Target countries (World Bank uses ISO3 codes)
WB_COUNTRIES = ["USA", "CHN", "JPN", "AUS", "CAN"]

# Key indicators to fetch
WB_INDICATORS = [
    "NY.GDP.MKTP.CD",      # GDP current USD
    "NY.GDP.PCAP.CD",      # GDP per capita
    "NY.GDP.MKTP.KD.ZG",   # GDP growth %
    "SP.POP.TOTL",         # Population total
    "FP.CPI.TOTL.ZG",      # Inflation CPI %
    "SL.UEM.TOTL.ZS",      # Unemployment %
    "NE.TRD.GNFS.ZS",      # Trade % GDP
    "BX.KLT.DINV.WD.GD.ZS", # FDI net inflows % GDP
    "GC.DOD.TOTL.GD.ZS",   # Government debt % GDP
]

START_YEAR = 2015
END_YEAR = 2024


class WorldBankClient:
    def __init__(self, session=None):
        self.session = session or requests.Session()
        self.session.headers.update({
            "User-Agent": "CountryStatsDashboard/1.0",
            "Accept": "application/json"
        })
    
    def _get_with_retry(self, url: str, params: dict = None, max_retries: int = 3) -> Optional[dict]:
        """Make a GET request with exponential backoff retry."""
        for attempt in range(max_retries):
            try:
                resp = self.session.get(url, params=params, timeout=30)
                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code == 429:
                    wait = (2 ** attempt) * 5
                    logger.warning(f"Rate limited. Waiting {wait}s...")
                    time.sleep(wait)
                elif resp.status_code == 404:
                    logger.warning(f"Not found: {url}")
                    return None
                else:
                    logger.error(f"HTTP {resp.status_code}: {url}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
            except requests.RequestException as e:
                logger.error(f"Request failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
        return None
    
    def fetch_wdi_indicator(self, indicator_code: str, countries: list[str], 
                            start_year: int, end_year: int) -> list[dict]:
        """
        Fetch indicator data from World Bank WDI API v2.
        Returns list of {iso3, year, value} dicts.
        """
        country_str = ";".join(countries)
        url = f"{WB_API_BASE}/country/{country_str}/indicator/{indicator_code}"
        params = {
            "format": "json",
            "date": f"{start_year}:{end_year}",
            "per_page": 1000,
            "mrv": end_year - start_year + 1
        }
        
        logger.info(f"Fetching WB WDI: {indicator_code} for {countries}")
        
        data = self._get_with_retry(url, params)
        if not data or len(data) < 2:
            logger.warning(f"No data returned for {indicator_code}")
            return []
        
        # WDI API returns [metadata, data_array]
        records = []
        for item in data[1] or []:
            if item.get("value") is not None:
                try:
                    records.append({
                        "iso3": item["country"]["id"],
                        "year": int(item["date"]),
                        "value": float(item["value"])
                    })
                except (ValueError, KeyError, TypeError) as e:
                    logger.debug(f"Skipping malformed record: {e}")
        
        logger.info(f"  Got {len(records)} data points for {indicator_code}")
        return records
    
    def fetch_all_indicators(self) -> dict[str, list[dict]]:
        """Fetch all WB indicators for all target countries."""
        results = {}
        for indicator in WB_INDICATORS:
            records = self.fetch_wdi_indicator(
                indicator, WB_COUNTRIES, START_YEAR, END_YEAR
            )
            results[indicator] = records
            time.sleep(0.5)  # Be polite to the API
        return results


class WorldBankETL:
    def __init__(self, db=None):
        self.db = db or SessionLocal()
        self.client = WorldBankClient()
        self._own_session = db is None
    
    def _get_country_id(self, iso3: str) -> Optional[int]:
        country = self.db.query(Country).filter_by(iso3=iso3).first()
        return country.id if country else None
    
    def _get_indicator_id(self, code: str) -> Optional[int]:
        indicator = self.db.query(Indicator).filter_by(code=code).first()
        return indicator.id if indicator else None
    
    def _get_source_id(self) -> Optional[int]:
        source = self.db.query(DataSource).filter_by(api_type="worldbank").first()
        return source.id if source else None
    
    def _upsert_data_point(self, country_id: int, indicator_id: int, 
                           year: int, value: float, source_id: int) -> bool:
        """Insert or update a data point. Returns True if upserted."""
        existing = self.db.query(DataPoint).filter_by(
            country_id=country_id,
            indicator_id=indicator_id,
            year=year
        ).first()
        
        if existing:
            if existing.value != value:
                existing.value = value
                existing.fetched_at = datetime.utcnow()
                return True
            return False
        else:
            dp = DataPoint(
                country_id=country_id,
                indicator_id=indicator_id,
                year=year,
                value=value,
                source_id=source_id
            )
            self.db.add(dp)
            return True
    
    def run(self) -> dict:
        """Execute the full World Bank ETL pipeline."""
        source_id = self._get_source_id()
        if not source_id:
            raise ValueError("World Bank data source not found in DB. Run seed.py first.")
        
        # Log ETL run start
        etl_run = EtlRun(source_id=source_id, status="running")
        self.db.add(etl_run)
        self.db.commit()
        
        stats = {"fetched": 0, "upserted": 0, "errors": 0}
        
        try:
            logger.info("Starting World Bank ETL run...")
            all_data = self.client.fetch_all_indicators()
            
            for indicator_code, records in all_data.items():
                indicator_id = self._get_indicator_id(indicator_code)
                if not indicator_id:
                    logger.warning(f"Indicator not in DB: {indicator_code}")
                    continue
                
                stats["fetched"] += len(records)
                
                for record in records:
                    country_id = self._get_country_id(record["iso3"])
                    if not country_id:
                        logger.debug(f"Country not in DB: {record['iso3']}")
                        continue
                    
                    if self._upsert_data_point(
                        country_id, indicator_id, 
                        record["year"], record["value"], source_id
                    ):
                        stats["upserted"] += 1
                
                self.db.commit()
            
            # Update ETL run
            etl_run.status = "success"
            etl_run.records_fetched = stats["fetched"]
            etl_run.records_upserted = stats["upserted"]
            etl_run.finished_at = datetime.utcnow()
            
            # Update data source last_sync
            source = self.db.query(DataSource).filter_by(id=source_id).first()
            if source:
                source.last_sync = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"✅ World Bank ETL complete: {stats}")
            return stats
        
        except Exception as e:
            logger.error(f"ETL run failed: {e}")
            etl_run.status = "error"
            etl_run.error_msg = str(e)
            etl_run.finished_at = datetime.utcnow()
            self.db.commit()
            stats["errors"] += 1
            raise
        
        finally:
            if self._own_session:
                self.db.close()


def run_worldbank_etl():
    """Convenience function to run the World Bank ETL."""
    etl = WorldBankETL()
    return etl.run()


if __name__ == "__main__":
    stats = run_worldbank_etl()
    print(f"World Bank ETL complete: {stats}")
