"""Tests for OECD ETL client (with mocked HTTP responses)."""
import pytest
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).parent.parent))

# Sample OECD SDMX-JSON response
MOCK_SDMX_JSON = {
    "data": {
        "structure": {
            "dimensions": {
                "observation": [
                    {
                        "id": "TIME_PERIOD",
                        "name": "Time period",
                        "values": [
                            {"id": "2023-Q1"}, {"id": "2023-Q2"},
                            {"id": "2023-Q3"}, {"id": "2023-Q4"},
                            {"id": "2022-Q1"}, {"id": "2022-Q2"},
                            {"id": "2022-Q3"}, {"id": "2022-Q4"},
                        ]
                    }
                ]
            }
        },
        "dataSets": [
            {
                "series": {
                    "0:0:0:0": {
                        "observations": {
                            "0": [2.5],  "1": [2.4],  "2": [2.3],  "3": [2.2],
                            "4": [3.1],  "5": [3.0],  "6": [2.9],  "7": [2.8],
                        }
                    }
                }
            }
        ]
    }
}


def test_oecd_client_parse_sdmx_json():
    """Test parsing of OECD SDMX-JSON response."""
    from etl.oecd_client import OECDClient
    
    client = OECDClient()
    records = client._parse_sdmx_json(MOCK_SDMX_JSON, "USA", "Q")
    
    assert len(records) == 2  # 2 years
    
    record_2023 = next((r for r in records if r["year"] == 2023), None)
    assert record_2023 is not None
    assert record_2023["value"] == 2.2  # Q4 value
    assert record_2023["iso3"] == "USA"
    
    record_2022 = next((r for r in records if r["year"] == 2022), None)
    assert record_2022 is not None
    assert record_2022["value"] == 2.8  # Q4 value


def test_period_to_year():
    """Test period string to year conversion."""
    from etl.oecd_client import OECDClient
    
    client = OECDClient()
    
    assert client._period_to_year("2023") == 2023
    assert client._period_to_year("2023-Q1") == 2023
    assert client._period_to_year("2023-Q4") == 2023
    assert client._period_to_year("2023-01") == 2023
    assert client._period_to_year("2023M12") == 2023
    assert client._period_to_year("invalid") is None
    assert client._period_to_year("") is None


def test_oecd_client_handles_missing_data():
    """Test graceful handling of missing or null data."""
    from etl.oecd_client import OECDClient
    
    empty_response = {"data": {"structure": {}, "dataSets": []}}
    
    client = OECDClient()
    records = client._parse_sdmx_json(empty_response, "USA", "Q")
    
    assert records == []


def test_oecd_client_fetch_with_mock():
    """Test fetch with mocked HTTP response."""
    from etl.oecd_client import OECDClient
    
    client = OECDClient()
    
    with patch.object(client, '_get_with_retry', return_value=MOCK_SDMX_JSON):
        records = client.fetch_sdmx_json(
            "MEI", "USA", "LRHUTTTT.{country}.STSA.M", "M", "2022-01", "2023-12"
        )
    
    assert len(records) > 0
    assert all("iso3" in r and "year" in r and "value" in r for r in records)


def test_oecd_etl_upsert():
    """Test OECD ETL upsert logic."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models.base import Base
    from models.models import Country, DataSource, Indicator, DataPoint
    
    test_engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=test_engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestSession()
    
    country = Country(iso2="US", iso3="USA", name="United States")
    source = DataSource(name="OECD", url="http://test", api_type="oecd")
    db.add_all([country, source])
    db.flush()
    
    indicator = Indicator(code="LRHUTTTT", name="Unemployment", source_id=source.id)
    db.add(indicator)
    db.commit()
    
    from etl.oecd_client import OECDETL
    etl = OECDETL(db=db)
    
    # Insert
    result = etl._upsert_data_point(country.id, indicator.id, 2023, 3.5, source.id)
    db.commit()
    assert result == True
    
    dp = db.query(DataPoint).filter_by(country_id=country.id, year=2023).first()
    assert dp.value == 3.5
    
    # Update  
    result = etl._upsert_data_point(country.id, indicator.id, 2023, 3.7, source.id)
    db.commit()
    assert result == True
    
    dp = db.query(DataPoint).filter_by(country_id=country.id, year=2023).first()
    assert dp.value == 3.7
    
    db.close()
