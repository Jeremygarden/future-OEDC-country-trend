"""Tests for database initialization and seed data."""
import pytest
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def make_test_db():
    """Create a fresh in-memory test database."""
    import importlib
    # Force reload to get a fresh engine with new in-memory DB
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    
    # Reload modules to get fresh engine
    import models.base as base_mod
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    fresh_engine = create_engine("sqlite:///:memory:", echo=False)
    
    import models.models as models_mod
    from models.base import Base
    Base.metadata.create_all(bind=fresh_engine)
    
    FreshSession = sessionmaker(autocommit=False, autoflush=False, bind=fresh_engine)
    db = FreshSession()
    return db, fresh_engine


def test_tables_created():
    """Verify all required tables exist."""
    db, engine = make_test_db()
    try:
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        required_tables = ["countries", "indicators", "data_points", "data_sources", "etl_runs"]
        for table in required_tables:
            assert table in tables, f"Table '{table}' not found"
    finally:
        db.close()


def test_seed_countries():
    """Test that countries can be seeded."""
    db, engine = make_test_db()
    try:
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
            db.add(country)
        db.commit()
        
        assert db.query(Country).count() == 5
        usa = db.query(Country).filter_by(iso3="USA").first()
        assert usa is not None
        assert usa.name == "United States"
        assert usa.iso2 == "US"
    finally:
        db.close()


def test_seed_data_sources():
    """Test data source seeding."""
    db, engine = make_test_db()
    try:
        from models.models import DataSource
        
        sources = [
            {"name": "World Bank Data360", "url": "https://data360.worldbank.org/api", "api_type": "worldbank"},
            {"name": "OECD SDMX REST", "url": "https://sdmx.oecd.org/public/rest", "api_type": "oecd"},
        ]
        
        for s in sources:
            source = DataSource(**s)
            db.add(source)
        db.commit()
        
        assert db.query(DataSource).count() == 2
        wb = db.query(DataSource).filter_by(api_type="worldbank").first()
        assert wb is not None
    finally:
        db.close()


def test_seed_indicators():
    """Test indicator seeding."""
    db, engine = make_test_db()
    try:
        from models.models import Indicator, DataSource
        
        source = DataSource(name="World Bank", url="http://test", api_type="worldbank")
        db.add(source)
        db.flush()
        
        ind = Indicator(
            code="NY.GDP.MKTP.CD",
            name="GDP (current USD)",
            unit="USD",
            category="GDP",
            source_id=source.id
        )
        db.add(ind)
        db.commit()
        
        assert db.query(Indicator).count() >= 1
        gdp = db.query(Indicator).filter_by(code="NY.GDP.MKTP.CD").first()
        assert gdp is not None
        assert gdp.unit == "USD"
    finally:
        db.close()


def test_data_point_unique_constraint():
    """Test unique constraint on data_points."""
    db, engine = make_test_db()
    try:
        from models.models import Country, Indicator, DataPoint, DataSource
        from sqlalchemy.exc import IntegrityError
        
        country = Country(iso2="US", iso3="USA", name="United States")
        source = DataSource(name="World Bank", url="http://test", api_type="worldbank")
        db.add_all([country, source])
        db.flush()
        
        indicator = Indicator(code="NY.GDP.MKTP.CD", name="GDP", source_id=source.id)
        db.add(indicator)
        db.flush()
        
        # Add a data point
        dp = DataPoint(
            country_id=country.id,
            indicator_id=indicator.id,
            year=2023,
            value=27360000000000.0,
            source_id=source.id
        )
        db.add(dp)
        db.commit()
        
        # Try to add duplicate
        dp2 = DataPoint(
            country_id=country.id,
            indicator_id=indicator.id,
            year=2023,
            value=99999.0,
            source_id=source.id
        )
        db.add(dp2)
        
        with pytest.raises(IntegrityError):
            db.commit()
        
        db.rollback()
    finally:
        db.close()


def test_etl_run_tracking():
    """Test ETL run logging."""
    db, engine = make_test_db()
    try:
        from models.models import EtlRun, DataSource
        from datetime import datetime
        
        source = DataSource(name="World Bank", url="http://test", api_type="worldbank")
        db.add(source)
        db.flush()
        
        run = EtlRun(
            source_id=source.id,
            status="running",
            records_fetched=0
        )
        db.add(run)
        db.commit()
        
        # Update to success
        run.status = "success"
        run.records_fetched = 350
        run.records_upserted = 350
        run.finished_at = datetime.utcnow()
        db.commit()
        
        completed_run = db.query(EtlRun).filter_by(status="success").first()
        assert completed_run is not None
        assert completed_run.records_fetched == 350
    finally:
        db.close()
