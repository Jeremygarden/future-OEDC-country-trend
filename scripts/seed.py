#!/usr/bin/env python3
"""Seed the database with countries and data sources."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.init_db import init_db
from models.base import SessionLocal
from models.models import Country, DataSource, Indicator
from datetime import datetime

COUNTRIES = [
    {"iso2": "US", "iso3": "USA", "name": "United States", "region": "North America", "income_group": "High income"},
    {"iso2": "CN", "iso3": "CHN", "name": "China", "region": "East Asia & Pacific", "income_group": "Upper middle income"},
    {"iso2": "JP", "iso3": "JPN", "name": "Japan", "region": "East Asia & Pacific", "income_group": "High income"},
    {"iso2": "AU", "iso3": "AUS", "name": "Australia", "region": "East Asia & Pacific", "income_group": "High income"},
    {"iso2": "CA", "iso3": "CAN", "name": "Canada", "region": "North America", "income_group": "High income"},
]

DATA_SOURCES = [
    {
        "name": "World Bank Data360",
        "url": "https://data360.worldbank.org/api",
        "api_type": "worldbank",
        "description": "World Bank Data360 API providing macroeconomic indicators for 200+ countries"
    },
    {
        "name": "World Bank WDI",
        "url": "https://api.worldbank.org/v2",
        "api_type": "worldbank",
        "description": "World Bank World Development Indicators API (fallback)"
    },
    {
        "name": "OECD SDMX REST",
        "url": "https://sdmx.oecd.org/public/rest",
        "api_type": "oecd",
        "description": "OECD SDMX REST API for economic statistics and indicators"
    },
]

WORLDBANK_INDICATORS = [
    {"code": "NY.GDP.MKTP.CD", "name": "GDP (current USD)", "unit": "USD", "category": "GDP", "description": "GDP at purchaser's prices in current US dollars"},
    {"code": "NY.GDP.PCAP.CD", "name": "GDP per capita (current USD)", "unit": "USD", "category": "GDP", "description": "GDP divided by midyear population"},
    {"code": "NY.GDP.MKTP.KD.ZG", "name": "GDP growth (annual %)", "unit": "%", "category": "GDP", "description": "Annual percentage growth rate of GDP at market prices"},
    {"code": "SP.POP.TOTL", "name": "Population, total", "unit": "persons", "category": "Demographics", "description": "Total population based on de facto definition"},
    {"code": "FP.CPI.TOTL.ZG", "name": "Inflation, consumer prices (annual %)", "unit": "%", "category": "Prices", "description": "CPI annual percentage change"},
    {"code": "SL.UEM.TOTL.ZS", "name": "Unemployment, total (% of labor force)", "unit": "%", "category": "Employment", "description": "Share of labor force that is without work"},
    {"code": "NE.TRD.GNFS.ZS", "name": "Trade (% of GDP)", "unit": "%", "category": "Trade", "description": "Sum of exports and imports of goods and services"},
    {"code": "BX.KLT.DINV.WD.GD.ZS", "name": "FDI, net inflows (% of GDP)", "unit": "%", "category": "Investment", "description": "Foreign direct investment net inflows"},
    {"code": "GC.DOD.TOTL.GD.ZS", "name": "Central government debt (% of GDP)", "unit": "%", "category": "Fiscal", "description": "Central government debt as % of GDP"},
]

OECD_INDICATORS = [
    {"code": "LRHUTTTT", "name": "Unemployment Rate (OECD MEI)", "unit": "%", "category": "Employment", "description": "Harmonised unemployment rate from OECD MEI dataset"},
    {"code": "CPALTT01", "name": "CPI Total (OECD MEI)", "unit": "index", "category": "Prices", "description": "Consumer price index total from OECD MEI dataset"},
    {"code": "NAEXKP01", "name": "GDP Expenditure Approach (OECD QNA)", "unit": "USD", "category": "GDP", "description": "GDP via expenditure approach from OECD QNA"},
    {"code": "GGXWDG_NGDP", "name": "General Government Debt (% GDP)", "unit": "%", "category": "Fiscal", "description": "General government gross debt as % of GDP"},
    {"code": "CA_GDP", "name": "Current Account Balance (% GDP)", "unit": "%", "category": "Trade", "description": "Current account balance as % of GDP"},
]


def seed_countries(db):
    print("\nSeeding countries...")
    for c_data in COUNTRIES:
        existing = db.query(Country).filter_by(iso3=c_data["iso3"]).first()
        if not existing:
            country = Country(**c_data)
            db.add(country)
            print(f"  Added: {c_data['name']} ({c_data['iso3']})")
        else:
            print(f"  Exists: {c_data['name']}")
    db.commit()


def seed_data_sources(db):
    print("\nSeeding data sources...")
    sources = {}
    for s_data in DATA_SOURCES:
        existing = db.query(DataSource).filter_by(name=s_data["name"]).first()
        if not existing:
            source = DataSource(**s_data)
            db.add(source)
            db.flush()
            sources[s_data["name"]] = source.id
            print(f"  Added: {s_data['name']}")
        else:
            sources[s_data["name"]] = existing.id
            print(f"  Exists: {s_data['name']}")
    db.commit()
    return sources


def seed_indicators(db, sources):
    print("\nSeeding indicators...")
    wb_source_id = sources.get("World Bank Data360") or sources.get("World Bank WDI")
    oecd_source_id = sources.get("OECD SDMX REST")
    
    for ind_data in WORLDBANK_INDICATORS:
        existing = db.query(Indicator).filter_by(code=ind_data["code"], source_id=wb_source_id).first()
        if not existing:
            ind = Indicator(**ind_data, source_id=wb_source_id)
            db.add(ind)
            print(f"  Added WB: {ind_data['code']}")
        else:
            print(f"  Exists WB: {ind_data['code']}")
    
    for ind_data in OECD_INDICATORS:
        existing = db.query(Indicator).filter_by(code=ind_data["code"], source_id=oecd_source_id).first()
        if not existing:
            ind = Indicator(**ind_data, source_id=oecd_source_id)
            db.add(ind)
            print(f"  Added OECD: {ind_data['code']}")
        else:
            print(f"  Exists OECD: {ind_data['code']}")
    
    db.commit()


def main():
    print("🌱 Seeding database...")
    
    # Initialize tables
    init_db()
    
    # Seed data
    db = SessionLocal()
    try:
        seed_countries(db)
        sources = seed_data_sources(db)
        seed_indicators(db, sources)
        
        # Summary
        countries = db.query(Country).count()
        data_sources = db.query(DataSource).count()
        indicators = db.query(Indicator).count()
        print(f"\n✅ Seed complete!")
        print(f"   Countries: {countries}")
        print(f"   Data sources: {data_sources}")
        print(f"   Indicators: {indicators}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
