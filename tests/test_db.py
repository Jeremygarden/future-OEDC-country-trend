"""Tests for database initialization and seed data."""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="module")
def db_session():
    """Create an in-memory test database."""
    import os
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    
    from models.base import engine, Base
    from models.models import Country, DataSource, Indicator, DataPoint, EtlRun
    Base.metadata.create_all(bind=engine)
    
    from models.base import SessionLocal
    db = SessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


def test_tables_created(db_session):
    """Verify all required tables exist."""
    from sqlalchemy import inspect
    from models.base import engine
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    required_tables = ["countries", "indicators", "data_points", "data_sources", "etl_runs"]
    for table in required_tables:
        assert table in tables, f"Table '{table}' not found"


def test_seed_countries(db_session):
    """Test that countries can be seeded."""
    from models.models import Country
    
    countries_data = [
        {"iso2": "US", "iso3": "USA", "name": "United States", "region": "North America"},
        {"iso2": "CN", "iso3": "CHN", "name": "China", "region": "East Asia & Pacific"},
        {"iso2": "JP", "iso3": "JPN", "name": "Japan", "region": "East Asia & Pacific"},
        {"iso2": "AU", "iso3": "AUS", "name": "Australia", "region": "East Asia & Pacific"},
        {"iso2": "CA", "iso3": "CAN", "name": "Canada", "region": "North America"},
    ]
    
    for c in countries_data:
        country = Country(**c)
        db_session.add(country)
    db_session.commit()
    
    assert db_session.query(Country).count() == 5
    usa = db_session.query(Country).filter_by(iso3="USA").first()
    assert usa is not None
    assert usa.name == "United States"
    assert usa.iso2 == "US"


def test_seed_data_sources(db_session):
    """Test data source seeding."""
    from models.models import DataSource
    
    sources = [
        {"name": "World Bank Data360", "url": "https://data360.worldbank.org/api", "api_type": "worldbank"},
        {"name": "OECD SDMX REST", "url": "https://sdmx.oecd.org/public/rest", "api_type": "oecd"},
    ]
    
    for s in sources:
        source = DataSource(**s)
        db_session.add(source)
    db_session.commit()
    
    assert db_session.query(DataSource).count() == 2
    wb = db_session.query(DataSource).filter_by(api_type="worldbank").first()
    assert wb is not None


def test_seed_indicators(db_session):
    """Test indicator seeding."""
    from models.models import Indicator, DataSource
    
    source = db_session.query(DataSource).filter_by(api_type="worldbank").first()
    
    ind = Indicator(
        code="NY.GDP.MKTP.CD",
        name="GDP (current USD)",
        unit="USD",
        category="GDP",
        source_id=source.id
    )
    db_session.add(ind)
    db_session.commit()
    
    assert db_session.query(Indicator).count() >= 1
    gdp = db_session.query(Indicator).filter_by(code="NY.GDP.MKTP.CD").first()
    assert gdp is not None
    assert gdp.unit == "USD"


def test_data_point_unique_constraint(db_session):
    """Test unique constraint on data_points."""
    from models.models import Country, Indicator, DataPoint, DataSource
    from sqlalchemy.exc import IntegrityError
    
    country = db_session.query(Country).filter_by(iso3="USA").first()
    source = db_session.query(DataSource).filter_by(api_type="worldbank").first()
    indicator = db_session.query(Indicator).filter_by(code="NY.GDP.MKTP.CD").first()
    
    # Add a data point
    dp = DataPoint(
        country_id=country.id,
        indicator_id=indicator.id,
        year=2023,
        value=27360000000000.0,
        source_id=source.id
    )
    db_session.add(dp)
    db_session.commit()
    
    # Try to add duplicate
    dp2 = DataPoint(
        country_id=country.id,
        indicator_id=indicator.id,
        year=2023,
        value=99999.0,
        source_id=source.id
    )
    db_session.add(dp2)
    
    with pytest.raises(IntegrityError):
        db_session.commit()
    
    db_session.rollback()


def test_etl_run_tracking(db_session):
    """Test ETL run logging."""
    from models.models import EtlRun, DataSource
    from datetime import datetime
    
    source = db_session.query(DataSource).filter_by(api_type="worldbank").first()
    
    run = EtlRun(
        source_id=source.id,
        status="running",
        records_fetched=0
    )
    db_session.add(run)
    db_session.commit()
    
    # Update to success
    run.status = "success"
    run.records_fetched = 350
    run.records_upserted = 350
    run.finished_at = datetime.utcnow()
    db_session.commit()
    
    completed_run = db_session.query(EtlRun).filter_by(status="success").first()
    assert completed_run is not None
    assert completed_run.records_fetched == 350
