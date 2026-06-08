#!/usr/bin/env python3
"""Initialize the SQLite database - creates all tables."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.base import engine, Base
from models.models import Country, DataSource, Indicator, DataPoint, EtlRun

def init_db():
    """Create all tables if they don't exist."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Database initialized successfully")
    
    # Verify tables
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Tables created: {', '.join(tables)}")
    return tables

if __name__ == "__main__":
    init_db()
