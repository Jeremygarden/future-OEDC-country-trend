"""Integration tests for the full data pipeline."""
import pytest
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="module")
def test_db():
    """Set up a test database with seeded data."""
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    
    from models.base import engine, Base
    from models.models import Country, DataSource, Indicator, DataPoint, EtlRun
    Base.metadata.create_all(bind=engine)
    
    from models.base import SessionLocal
    db = SessionLocal()
    
    # Seed countries
    countries = [
        Country(iso2="US", iso3="USA", name="United States", region="North America"),
        Country(iso2="CN", iso3="CHN", name="China", region="East Asia"),
        Country(iso2="JP", iso3="JPN", name="Japan", region="East Asia"),
        Country(iso2="AU", iso3="AUS", name="Australia", region="Oceania"),
        Country(iso2="CA", iso3="CAN", name="Canada", region="North America"),
    ]
    db.add_all(countries)
    db.flush()
    
    # Seed source
    source = DataSource(name="World Bank Data360", url="http://test", api_type="worldbank")
    db.add(source)
    db.flush()
    
    # Seed indicators
    indicators = [
        Indicator(code="NY.GDP.MKTP.CD", name="GDP (current USD)", unit="USD", category="GDP", source_id=source.id),
        Indicator(code="NY.GDP.MKTP.KD.ZG", name="GDP growth", unit="%", category="GDP", source_id=source.id),
        Indicator(code="SL.UEM.TOTL.ZS", name="Unemployment", unit="%", category="Employment", source_id=source.id),
        Indicator(code="FP.CPI.TOTL.ZG", name="CPI Inflation", unit="%", category="Prices", source_id=source.id),
    ]
    db.add_all(indicators)
    db.flush()
    
    # Mock GDP data for all countries (2019-2023)
    gdp_data = {
        "USA": [19543, 20937, 22996, 25744, 27360],
        "CHN": [12238, 13894, 17734, 17963, 17794],
        "JPN": [4931, 5236, 4936, 4232, 4213],
        "AUS": [1376, 1536, 1617, 1724, 1723],
        "CAN": [1647, 1736, 1988, 2160, 2140],
    }
    
    gdp_ind = next(i for i in indicators if i.code == "NY.GDP.MKTP.CD")
    
    for country in countries:
        gdp_values = gdp_data.get(country.iso3, [])
        for i, year in enumerate(range(2019, 2024)):
            if i < len(gdp_values):
                dp = DataPoint(
                    country_id=country.id,
                    indicator_id=gdp_ind.id,
                    year=year,
                    value=gdp_values[i] * 1e9,  # Convert billions to USD
                    source_id=source.id
                )
                db.add(dp)
    
    # Unemployment data  
    unem_data = {
        "USA": [3.7, 8.1, 5.4, 3.6, 3.5],
        "CHN": [3.6, 4.2, 3.9, 4.0, 3.8],
        "JPN": [2.4, 2.8, 2.8, 2.6, 2.5],
        "AUS": [5.2, 6.5, 5.1, 3.5, 3.7],
        "CAN": [5.7, 9.6, 7.5, 5.2, 5.4],
    }
    
    unem_ind = next(i for i in indicators if i.code == "SL.UEM.TOTL.ZS")
    
    for country in countries:
        unem_values = unem_data.get(country.iso3, [])
        for i, year in enumerate(range(2019, 2024)):
            if i < len(unem_values):
                dp = DataPoint(
                    country_id=country.id,
                    indicator_id=unem_ind.id,
                    year=year,
                    value=unem_values[i],
                    source_id=source.id
                )
                db.add(dp)
    
    db.commit()
    yield db
    db.close()


def test_country_count(test_db):
    """Verify all 5 countries are in the database."""
    from models.models import Country
    count = test_db.query(Country).count()
    assert count == 5


def test_data_points_exist(test_db):
    """Verify data points were loaded."""
    from models.models import DataPoint
    count = test_db.query(DataPoint).count()
    assert count > 0


def test_get_country_stats_integration(test_db):
    """Integration test for get_country_stats query."""
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    
    from models.base import engine, Base
    Base.metadata.create_all(bind=engine)
    
    from models.base import SessionLocal
    from models.models import Country, DataSource, Indicator, DataPoint
    
    db = SessionLocal()
    
    # Quick seed
    country = Country(iso2="US", iso3="USA", name="United States", region="North America")
    source = DataSource(name="WB", url="http://test", api_type="worldbank")
    db.add_all([country, source])
    db.flush()
    
    indicator = Indicator(code="NY.GDP.MKTP.CD", name="GDP", unit="USD", source_id=source.id)
    db.add(indicator)
    db.flush()
    
    for year, value in [(2021, 23e12), (2022, 25.7e12), (2023, 27.36e12)]:
        dp = DataPoint(country_id=country.id, indicator_id=indicator.id, year=year, value=value, source_id=source.id)
        db.add(dp)
    db.commit()
    db.close()
    
    from db.query import get_country_stats
    stats = get_country_stats("USA")
    
    assert stats["country"]["iso3"] == "USA"
    assert stats["country"]["name"] == "United States"
    assert "NY.GDP.MKTP.CD" in stats["indicators"]
    
    gdp_data = stats["indicators"]["NY.GDP.MKTP.CD"]
    assert len(gdp_data["values"]) == 3
    assert gdp_data["latest"]["year"] == 2023


def test_get_indicator_trend_integration(test_db):
    """Integration test for get_indicator_trend."""
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    
    from models.base import engine, Base
    Base.metadata.create_all(bind=engine)
    
    from models.base import SessionLocal
    from models.models import Country, DataSource, Indicator, DataPoint
    
    db = SessionLocal()
    
    # Seed 2 countries
    usa = Country(iso2="US", iso3="USA", name="United States", region="North America")
    jpn = Country(iso2="JP", iso3="JPN", name="Japan", region="East Asia")
    source = DataSource(name="WB", url="http://test", api_type="worldbank")
    db.add_all([usa, jpn, source])
    db.flush()
    
    ind = Indicator(code="FP.CPI.TOTL.ZG", name="CPI Inflation", unit="%", source_id=source.id)
    db.add(ind)
    db.flush()
    
    test_data = [
        (usa.id, 2021, 4.7), (usa.id, 2022, 8.0), (usa.id, 2023, 4.1),
        (jpn.id, 2021, -0.2), (jpn.id, 2022, 2.5), (jpn.id, 2023, 3.3),
    ]
    for country_id, year, value in test_data:
        dp = DataPoint(country_id=country_id, indicator_id=ind.id, year=year, value=value, source_id=source.id)
        db.add(dp)
    db.commit()
    db.close()
    
    from db.query import get_indicator_trend
    trend = get_indicator_trend("FP.CPI.TOTL.ZG", countries=["USA", "JPN"])
    
    assert trend["indicator"]["code"] == "FP.CPI.TOTL.ZG"
    assert "USA" in trend["countries"]
    assert "JPN" in trend["countries"]
    assert len(trend["countries"]["USA"]) == 3


def test_search_indicators(test_db):
    """Integration test for indicator search."""
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    
    from models.base import engine, Base
    Base.metadata.create_all(bind=engine)
    
    from models.base import SessionLocal
    from models.models import DataSource, Indicator
    
    db = SessionLocal()
    source = DataSource(name="WB", url="http://test", api_type="worldbank")
    db.add(source)
    db.flush()
    
    indicators = [
        Indicator(code="NY.GDP.MKTP.CD", name="GDP (current USD)", category="GDP", source_id=source.id),
        Indicator(code="NY.GDP.PCAP.CD", name="GDP per capita", category="GDP", source_id=source.id),
        Indicator(code="SL.UEM.TOTL.ZS", name="Unemployment rate", category="Employment", source_id=source.id),
    ]
    db.add_all(indicators)
    db.commit()
    db.close()
    
    from db.query import search_indicators
    gdp_results = search_indicators("gdp")
    assert len(gdp_results) >= 2
    
    unem_results = search_indicators("unemployment")
    assert len(unem_results) >= 1


def test_cache_operations():
    """Test cache set/get/invalidate."""
    from db.cache import get_cached, set_cached, invalidate_cache
    
    key = "integration_test_key"
    data = {"test": "value", "number": 42}
    
    # Set
    set_cached(key, data, ttl=60)
    
    # Get
    result = get_cached(key)
    assert result == data
    
    # Invalidate
    count = invalidate_cache("integration_test_key")
    assert count >= 1
    
    # Verify gone
    result = get_cached(key)
    assert result is None
