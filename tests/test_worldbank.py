"""Tests for World Bank ETL client (with mocked HTTP responses)."""
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).parent.parent))


# Sample WDI API response
MOCK_WDI_RESPONSE = [
    {"page": 1, "pages": 1, "per_page": 50, "total": 5},
    [
        {"country": {"id": "USA", "value": "United States"}, "date": "2023", "value": "27360000000000.0", "indicator": {"id": "NY.GDP.MKTP.CD"}},
        {"country": {"id": "USA", "value": "United States"}, "date": "2022", "value": "25744900000000.0", "indicator": {"id": "NY.GDP.MKTP.CD"}},
        {"country": {"id": "CHN", "value": "China"}, "date": "2023", "value": "17794782000000.0", "indicator": {"id": "NY.GDP.MKTP.CD"}},
        {"country": {"id": "JPN", "value": "Japan"}, "date": "2023", "value": "4213000000000.0", "indicator": {"id": "NY.GDP.MKTP.CD"}},
        {"country": {"id": "AUS", "value": "Australia"}, "date": "2023", "value": "1723000000000.0", "indicator": {"id": "NY.GDP.MKTP.CD"}},
    ]
]


@pytest.fixture
def mock_session():
    mock = MagicMock()
    return mock


def test_worldbank_client_parse_response():
    """Test parsing of WDI API response format."""
    from etl.worldbank_client import WorldBankClient
    
    client = WorldBankClient()
    
    with patch.object(client, '_get_with_retry', return_value=MOCK_WDI_RESPONSE):
        records = client.fetch_wdi_indicator("NY.GDP.MKTP.CD", ["USA", "CHN", "JPN", "AUS", "CAN"], 2020, 2023)
    
    assert len(records) == 5
    
    usa_record = next((r for r in records if r["iso3"] == "USA" and r["year"] == 2023), None)
    assert usa_record is not None
    assert abs(usa_record["value"] - 27360000000000.0) < 1


def test_worldbank_client_handles_null_values():
    """Test that null values are excluded from results."""
    from etl.worldbank_client import WorldBankClient
    
    mock_response = [
        {"page": 1, "pages": 1, "per_page": 10, "total": 3},
        [
            {"country": {"id": "USA"}, "date": "2023", "value": "100.0"},
            {"country": {"id": "CHN"}, "date": "2023", "value": None},   # null value
            {"country": {"id": "JPN"}, "date": "2023", "value": "200.0"},
        ]
    ]
    
    client = WorldBankClient()
    with patch.object(client, '_get_with_retry', return_value=mock_response):
        records = client.fetch_wdi_indicator("NY.GDP.MKTP.CD", ["USA", "CHN", "JPN"], 2020, 2023)
    
    # China's null value should be excluded
    assert len(records) == 2
    iso3s = [r["iso3"] for r in records]
    assert "USA" in iso3s
    assert "JPN" in iso3s
    assert "CHN" not in iso3s


def test_worldbank_client_retry_on_rate_limit():
    """Test retry logic on 429 response."""
    import requests
    from etl.worldbank_client import WorldBankClient
    
    client = WorldBankClient()
    
    # Mock HTTP 429 followed by success
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_WDI_RESPONSE
    
    mock_429 = MagicMock()
    mock_429.status_code = 429
    
    with patch.object(client.session, 'get', side_effect=[mock_429, mock_response]) as mock_get:
        with patch('time.sleep'):  # Don't actually wait
            result = client._get_with_retry("https://api.worldbank.org/test")
    
    assert result == MOCK_WDI_RESPONSE


def test_worldbank_etl_upsert_logic():
    """Test ETL upsert logic with in-memory DB."""
    import os
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    
    from models.base import engine, Base
    from models.models import Country, DataSource, Indicator, DataPoint, EtlRun
    Base.metadata.create_all(bind=engine)
    
    from models.base import SessionLocal
    db = SessionLocal()
    
    # Set up test data
    country = Country(iso2="US", iso3="USA", name="United States")
    source = DataSource(name="World Bank Data360", url="http://test", api_type="worldbank")
    db.add_all([country, source])
    db.flush()
    
    indicator = Indicator(code="NY.GDP.MKTP.CD", name="GDP", source_id=source.id)
    db.add(indicator)
    db.commit()
    
    from etl.worldbank_client import WorldBankETL
    etl = WorldBankETL(db=db)
    
    # Test upsert
    result = etl._upsert_data_point(country.id, indicator.id, 2023, 27360000000000.0, source.id)
    db.commit()
    assert result == True
    
    # Verify it's in DB
    dp = db.query(DataPoint).filter_by(country_id=country.id, year=2023).first()
    assert dp is not None
    assert dp.value == 27360000000000.0
    
    # Test update (same year, different value)
    result = etl._upsert_data_point(country.id, indicator.id, 2023, 28000000000000.0, source.id)
    db.commit()
    assert result == True
    
    dp = db.query(DataPoint).filter_by(country_id=country.id, year=2023).first()
    assert dp.value == 28000000000000.0
    
    db.close()
