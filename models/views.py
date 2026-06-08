"""SQLAlchemy-compatible view queries for the dashboard."""
import sys
from pathlib import Path
from typing import Optional
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from models.base import SessionLocal


def execute_view(view_name: str, db=None, limit: int = 1000) -> list[dict]:
    """Execute a SQL view and return results as list of dicts."""
    close_db = db is None
    if db is None:
        db = SessionLocal()
    
    try:
        result = db.execute(text(f"SELECT * FROM {view_name} LIMIT :limit"), {"limit": limit})
        columns = result.keys()
        return [dict(zip(columns, row)) for row in result.fetchall()]
    finally:
        if close_db:
            db.close()


def get_latest_stats(country_iso3: Optional[str] = None) -> list[dict]:
    """Get latest stats, optionally filtered by country."""
    db = SessionLocal()
    try:
        if country_iso3:
            result = db.execute(
                text("SELECT * FROM v_latest_stats WHERE iso3 = :iso3"),
                {"iso3": country_iso3}
            )
        else:
            result = db.execute(text("SELECT * FROM v_latest_stats"))
        columns = result.keys()
        return [dict(zip(columns, row)) for row in result.fetchall()]
    finally:
        db.close()


def get_gdp_trend(country_iso3: Optional[str] = None) -> list[dict]:
    """Get GDP trend data."""
    db = SessionLocal()
    try:
        if country_iso3:
            result = db.execute(
                text("SELECT * FROM v_gdp_trend WHERE iso3 = :iso3"),
                {"iso3": country_iso3}
            )
        else:
            result = db.execute(text("SELECT * FROM v_gdp_trend"))
        columns = result.keys()
        return [dict(zip(columns, row)) for row in result.fetchall()]
    finally:
        db.close()


def get_country_comparison() -> list[dict]:
    """Get side-by-side comparison of latest values for all countries."""
    return execute_view("v_country_comparison")
