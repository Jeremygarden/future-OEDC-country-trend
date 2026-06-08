"""Additional query/data-layer tests for edge cases and missing-data handling."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.base import Base
from models.models import Country, DataSource, Indicator, DataPoint
import db.query as query_module


@pytest.fixture()
def session_factory(monkeypatch):
    """Build a fresh in-memory DB and patch db.query.SessionLocal to use it."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    monkeypatch.setattr(query_module, "SessionLocal", Session)
    return Session


def _seed_minimal_dataset(Session):
    db = Session()
    try:
        usa = Country(iso2="US", iso3="USA", name="United States", region="North America")
        chn = Country(iso2="CN", iso3="CHN", name="China", region="East Asia")
        source = DataSource(name="World Bank", url="http://test", api_type="worldbank")
        db.add_all([usa, chn, source])
        db.flush()

        gdp = Indicator(code="NY.GDP.MKTP.CD", name="GDP (current USD)", unit="USD", category="GDP", source_id=source.id)
        cpi = Indicator(code="FP.CPI.TOTL.ZG", name="CPI Inflation", unit="%", category="Prices", source_id=source.id)
        db.add_all([gdp, cpi])
        db.flush()

        db.add_all(
            [
                # Missing historical value + valid current value for USA GDP
                DataPoint(country_id=usa.id, indicator_id=gdp.id, year=2022, value=None, source_id=source.id),
                DataPoint(country_id=usa.id, indicator_id=gdp.id, year=2023, value=27.36e12, source_id=source.id),
                # CPI trend for range filtering tests
                DataPoint(country_id=usa.id, indicator_id=cpi.id, year=2020, value=1.2, source_id=source.id),
                DataPoint(country_id=usa.id, indicator_id=cpi.id, year=2021, value=4.7, source_id=source.id),
                DataPoint(country_id=usa.id, indicator_id=cpi.id, year=2022, value=8.0, source_id=source.id),
            ]
        )

        db.commit()
    finally:
        db.close()


def test_get_country_stats_handles_missing_data(session_factory):
    _seed_minimal_dataset(session_factory)

    payload = query_module.get_country_stats("USA")

    assert payload["country"]["iso3"] == "USA"
    assert "NY.GDP.MKTP.CD" in payload["indicators"]

    gdp = payload["indicators"]["NY.GDP.MKTP.CD"]
    assert gdp["latest"]["year"] == 2023
    assert gdp["latest"]["value"] == pytest.approx(27.36, rel=0.01)
    # Previous datapoint was missing -> YoY should remain None, not crash
    assert gdp["latest"]["yoy_change"] is None


def test_get_indicator_trend_filters_years_and_skips_unknown_countries(session_factory):
    _seed_minimal_dataset(session_factory)

    trend = query_module.get_indicator_trend(
        "FP.CPI.TOTL.ZG",
        countries=["USA", "ZZZ"],
        start_year=2021,
        end_year=2022,
    )

    assert trend["indicator"]["code"] == "FP.CPI.TOTL.ZG"
    assert set(trend["countries"].keys()) == {"USA"}
    years = [row["year"] for row in trend["countries"]["USA"]]
    assert years == [2021, 2022]


def test_search_indicators_is_case_insensitive_and_handles_no_matches(session_factory):
    _seed_minimal_dataset(session_factory)

    hits = query_module.search_indicators("gDp")
    assert any(item["code"] == "NY.GDP.MKTP.CD" for item in hits)

    assert query_module.search_indicators("definitely-no-match") == []


def test_get_country_stats_raises_for_unknown_country(session_factory):
    _seed_minimal_dataset(session_factory)

    with pytest.raises(ValueError, match="Country not found"):
        query_module.get_country_stats("XXX")
