#!/usr/bin/env python3
"""
OECD SDMX REST API ETL Client.

Fetches macroeconomic indicators for US, China, Japan, Australia, Canada
from the OECD SDMX REST API and stores them in the SQLite database.

API docs: https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html
OECD SDMX REST: https://sdmx.oecd.org/public/rest/
"""
import sys
import time
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Union
import re

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from models.base import SessionLocal
from models.models import Country, DataSource, Indicator, DataPoint, EtlRun

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# OECD SDMX REST API base URL
OECD_API_BASE = "https://sdmx.oecd.org/public/rest"

# OECD country codes for target countries
OECD_COUNTRIES = {
    "USA": "USA",
    "CHN": "CHN",
    "JPN": "JPN",
    "AUS": "AUS",
    "CAN": "CAN",
}

# OECD datasets and indicators to fetch
# Format: (dataset_id, series_key, indicator_code_in_db, description)
OECD_QUERIES = [
    # MEI (Main Economic Indicators) dataset
    # Unemployment rate
    {
        "dataset": "MEI",
        "key": "LRHUTTTT.{country}.STSA.M",
        "indicator_code": "LRHUTTTT",
        "frequency": "M",
        "description": "Unemployment Rate"
    },
    # CPI Total
    {
        "dataset": "MEI",
        "key": "CPALTT01.{country}.IXOBSA.M",
        "indicator_code": "CPALTT01",
        "frequency": "M",
        "description": "CPI Total"
    },
    # QNA (Quarterly National Accounts) - GDP
    {
        "dataset": "QNA",
        "key": "NAEXKP01.{country}.GPSA.Q",
        "indicator_code": "NAEXKP01",
        "frequency": "Q",
        "description": "GDP Expenditure Approach"
    },
]

START_PERIOD = "2015-Q1"
END_PERIOD = "2024-Q4"
START_PERIOD_M = "2015-01"
END_PERIOD_M = "2024-12"
START_PERIOD_A = "2015"
END_PERIOD_A = "2024"


class OECDClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "CountryStatsDashboard/1.0 (contact: data@example.com)",
            "Accept": "application/json"
        })
    
    def _get_with_retry(self, url: str, params: dict = None, max_retries: int = 3) -> Optional[Union[dict, str]]:
        """Make a GET request with exponential backoff retry."""
        for attempt in range(max_retries):
            try:
                resp = self.session.get(url, params=params, timeout=60)
                if resp.status_code == 200:
                    ct = resp.headers.get("Content-Type", "")
                    if "json" in ct:
                        return resp.json()
                    elif "xml" in ct or "sdmx" in ct:
                        return resp.text  # Return XML as string
                    else:
                        try:
                            return resp.json()
                        except Exception:
                            return resp.text
                elif resp.status_code == 429:
                    wait = (2 ** attempt) * 10
                    logger.warning(f"Rate limited. Waiting {wait}s...")
                    time.sleep(wait)
                elif resp.status_code in [404, 400]:
                    logger.warning(f"HTTP {resp.status_code}: {url}")
                    return None
                elif resp.status_code == 503:
                    logger.warning(f"Service unavailable, waiting...")
                    time.sleep(30)
                else:
                    logger.error(f"HTTP {resp.status_code}: {url}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
            except requests.RequestException as e:
                logger.error(f"Request error (attempt {attempt+1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
        return None
    
    def fetch_sdmx_json(self, dataset_id: str, country: str, 
                         series_key_template: str, frequency: str,
                         start_period: str, end_period: str) -> list[dict]:
        """
        Fetch data from OECD SDMX REST API in JSON format.
        Returns list of {iso3, year, value, period} dicts.
        """
        key = series_key_template.format(country=country)
        url = f"{OECD_API_BASE}/data/{dataset_id}/{key}/all"
        
        params = {
            "format": "jsondata",
            "startPeriod": start_period,
            "endPeriod": end_period,
        }
        
        logger.info(f"Fetching OECD: {dataset_id}/{key}")
        
        data = self._get_with_retry(url, params)
        if not data:
            logger.warning(f"No data for {dataset_id}/{key}")
            return []
        
        # Parse SDMX-JSON format
        return self._parse_sdmx_json(data, country, frequency)
    
    def _parse_sdmx_json(self, data: Union[dict, str], country: str, frequency: str) -> list[dict]:
        """Parse OECD SDMX-JSON response and return annual data points."""
        if isinstance(data, str):
            # Try to parse as JSON anyway
            try:
                data = json.loads(data)
            except Exception:
                return []
        
        if not isinstance(data, dict):
            return []
        
        try:
            # SDMX-JSON structure
            structure = data.get("data", {}).get("structure", {}) or data.get("structure", {})
            datasets = data.get("data", {}).get("dataSets", []) or data.get("dataSets", [])
            
            if not datasets:
                return []
            
            dataset = datasets[0]
            series_dict = dataset.get("series", {})
            
            if not series_dict:
                return []
            
            # Get time dimension values
            dimensions = structure.get("dimensions", {})
            obs_dims = dimensions.get("observation", []) if isinstance(dimensions, dict) else []
            time_dim = None
            for dim in obs_dims:
                if dim.get("id") in ("TIME_PERIOD", "PERIOD"):
                    time_dim = dim
                    break
            
            records = []
            annual_data = {}  # year -> list of values for averaging
            
            for series_key, series_data in series_dict.items():
                observations = series_data.get("observations", {})
                
                if not observations:
                    continue
                
                for obs_idx, obs_values in observations.items():
                    value = obs_values[0] if obs_values else None
                    if value is None:
                        continue
                    
                    # Get period from time dimension
                    period = None
                    if time_dim:
                        values_list = time_dim.get("values", [])
                        try:
                            idx = int(obs_idx)
                            if idx < len(values_list):
                                period = values_list[idx].get("id")
                        except (ValueError, IndexError):
                            pass
                    
                    if not period:
                        continue
                    
                    # Convert period to year
                    year = self._period_to_year(period)
                    if not year:
                        continue
                    
                    if year not in annual_data:
                        annual_data[year] = []
                    annual_data[year].append(float(value))
            
            # For quarterly/monthly data, use Q4 or Dec value as annual representation
            # Or average if preferred
            for year, values in annual_data.items():
                if values:
                    # Use last value (Q4 or Dec) as most representative annual figure
                    records.append({
                        "iso3": country,
                        "year": year,
                        "value": values[-1]  # Last observation of the year
                    })
            
            return sorted(records, key=lambda x: x["year"])
        
        except Exception as e:
            logger.error(f"Error parsing SDMX-JSON: {e}")
            return []
    
    def _period_to_year(self, period: str) -> Optional[int]:
        """Convert OECD period format to year integer."""
        try:
            if re.match(r'^\d{4}$', period):
                return int(period)
            elif re.match(r'^\d{4}-Q\d$', period):
                return int(period[:4])
            elif re.match(r'^\d{4}-\d{2}$', period):
                return int(period[:4])
            elif re.match(r'^\d{4}M\d{2}$', period):
                return int(period[:4])
        except (ValueError, AttributeError):
            pass
        return None
    
    def fetch_oecd_indicators(self) -> dict[str, list[dict]]:
        """Fetch all OECD indicators for all target countries."""
        results = {}
        
        for query in OECD_QUERIES:
            indicator_code = query["indicator_code"]
            if indicator_code not in results:
                results[indicator_code] = []
            
            freq = query["frequency"]
            if freq == "Q":
                start_p, end_p = START_PERIOD, END_PERIOD
            elif freq == "M":
                start_p, end_p = START_PERIOD_M, END_PERIOD_M
            else:
                start_p, end_p = START_PERIOD_A, END_PERIOD_A
            
            for country_iso3 in OECD_COUNTRIES.values():
                records = self.fetch_sdmx_json(
                    query["dataset"],
                    country_iso3,
                    query["key"],
                    freq,
                    start_p,
                    end_p
                )
                results[indicator_code].extend(records)
                time.sleep(1)  # Be polite
        
        return results


class OECDETL:
    def __init__(self, db=None):
        self.db = db or SessionLocal()
        self.client = OECDClient()
        self._own_session = db is None
    
    def _get_country_id(self, iso3: str) -> Optional[int]:
        country = self.db.query(Country).filter_by(iso3=iso3).first()
        return country.id if country else None
    
    def _get_indicator_id(self, code: str) -> Optional[int]:
        indicator = self.db.query(Indicator).filter_by(code=code).first()
        return indicator.id if indicator else None
    
    def _get_source_id(self) -> Optional[int]:
        source = self.db.query(DataSource).filter_by(api_type="oecd").first()
        return source.id if source else None
    
    def _upsert_data_point(self, country_id: int, indicator_id: int,
                           year: int, value: float, source_id: int) -> bool:
        """Insert or update data point. Returns True if modified."""
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
        """Execute the full OECD ETL pipeline."""
        source_id = self._get_source_id()
        if not source_id:
            raise ValueError("OECD data source not found in DB. Run seed.py first.")
        
        etl_run = EtlRun(source_id=source_id, status="running")
        self.db.add(etl_run)
        self.db.commit()
        
        stats = {"fetched": 0, "upserted": 0, "errors": 0}
        
        try:
            logger.info("Starting OECD ETL run...")
            all_data = self.client.fetch_oecd_indicators()
            
            for indicator_code, records in all_data.items():
                indicator_id = self._get_indicator_id(indicator_code)
                if not indicator_id:
                    logger.warning(f"Indicator not in DB: {indicator_code}")
                    continue
                
                stats["fetched"] += len(records)
                
                for record in records:
                    country_id = self._get_country_id(record["iso3"])
                    if not country_id:
                        continue
                    
                    if self._upsert_data_point(
                        country_id, indicator_id,
                        record["year"], record["value"], source_id
                    ):
                        stats["upserted"] += 1
                
                self.db.commit()
            
            etl_run.status = "success"
            etl_run.records_fetched = stats["fetched"]
            etl_run.records_upserted = stats["upserted"]
            etl_run.finished_at = datetime.utcnow()
            
            source = self.db.query(DataSource).filter_by(id=source_id).first()
            if source:
                source.last_sync = datetime.utcnow()
            
            self.db.commit()
            logger.info(f"✅ OECD ETL complete: {stats}")
            return stats
        
        except Exception as e:
            logger.error(f"OECD ETL failed: {e}")
            etl_run.status = "error"
            etl_run.error_msg = str(e)
            etl_run.finished_at = datetime.utcnow()
            self.db.commit()
            stats["errors"] += 1
            raise
        
        finally:
            if self._own_session:
                self.db.close()


def run_oecd_etl():
    """Convenience function to run OECD ETL."""
    etl = OECDETL()
    return etl.run()


if __name__ == "__main__":
    stats = run_oecd_etl()
    print(f"OECD ETL complete: {stats}")
