#!/usr/bin/env python3
"""
Full end-to-end pipeline:
1. Initialize database
2. Seed countries, data sources, indicators
3. Fetch World Bank data
4. Fetch OECD data
5. Run transformations
6. Warm up cache
"""
import sys
import logging
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


def run_full_pipeline(skip_etl: bool = False):
    print("\n" + "="*60)
    print("FULL DATA PIPELINE - Country Stats Dashboard")
    print(f"Started: {datetime.utcnow().isoformat()}")
    print("="*60)
    
    start = datetime.utcnow()
    steps = {}
    
    # Step 1: Database init
    print("\n[1/5] Initializing database...")
    try:
        from db.init_db import init_db
        tables = init_db()
        steps["db_init"] = {"status": "ok", "tables": tables}
        print(f"  ✓ Database initialized: {len(tables)} tables")
    except Exception as e:
        steps["db_init"] = {"status": "error", "error": str(e)}
        print(f"  ✗ DB init failed: {e}")
        return steps
    
    # Step 2: Create SQL views
    print("\n[2/5] Creating SQL views...")
    try:
        from models.base import engine
        from sqlalchemy import text
        
        views_path = Path(__file__).parent.parent / "db" / "views.sql"
        if views_path.exists():
            with open(views_path) as f:
                sql = f.read()
            
            # Execute each statement
            with engine.connect() as conn:
                for stmt in sql.split(";"):
                    stmt = stmt.strip()
                    if stmt:
                        try:
                            conn.execute(text(stmt))
                        except Exception as e:
                            logger.debug(f"View stmt note: {e}")
                conn.commit()
        
        steps["views"] = {"status": "ok"}
        print("  ✓ SQL views created")
    except Exception as e:
        steps["views"] = {"status": "error", "error": str(e)}
        print(f"  ✗ Views creation failed: {e}")
    
    # Step 3: Seed data
    print("\n[3/5] Seeding data...")
    try:
        from scripts.seed import main as seed_main
        seed_main()
        steps["seed"] = {"status": "ok"}
        print("  ✓ Seed complete")
    except Exception as e:
        steps["seed"] = {"status": "error", "error": str(e)}
        print(f"  ✗ Seed failed: {e}")
    
    if not skip_etl:
        # Step 4: ETL
        print("\n[4/5] Running ETL pipelines...")
        try:
            from scripts.run_etl import run_etl_pipeline
            etl_results = run_etl_pipeline()
            steps["etl"] = {"status": "ok", "details": etl_results}
            print("  ✓ ETL complete")
        except Exception as e:
            steps["etl"] = {"status": "error", "error": str(e)}
            print(f"  ✗ ETL failed: {e}")
    else:
        print("\n[4/5] ETL skipped (skip_etl=True)")
        steps["etl"] = {"status": "skipped"}
    
    # Step 5: Cache warmup
    print("\n[5/5] Warming up query cache...")
    try:
        from db.cache import warmup_cache
        cache_stats = warmup_cache()
        steps["cache"] = {"status": "ok", **cache_stats}
        print(f"  ✓ Cache warmed: {cache_stats}")
    except Exception as e:
        steps["cache"] = {"status": "error", "error": str(e)}
        print(f"  ✗ Cache warmup failed (non-critical): {e}")
    
    # Summary
    elapsed = (datetime.utcnow() - start).total_seconds()
    ok_steps = sum(1 for s in steps.values() if s.get("status") in ("ok", "skipped"))
    
    print(f"\n{'='*60}")
    print(f"Pipeline Complete - {elapsed:.1f}s")
    print(f"Steps OK: {ok_steps}/{len(steps)}")
    
    # Database stats
    try:
        from models.base import SessionLocal
        from models.models import Country, Indicator, DataPoint
        db = SessionLocal()
        countries = db.query(Country).count()
        indicators = db.query(Indicator).count()
        data_points = db.query(DataPoint).count()
        db.close()
        print(f"Database: {countries} countries | {indicators} indicators | {data_points} data points")
    except Exception:
        pass
    
    return steps


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run full country stats pipeline")
    parser.add_argument("--skip-etl", action="store_true", help="Skip ETL API calls")
    args = parser.parse_args()
    
    results = run_full_pipeline(skip_etl=args.skip_etl)
    
    failed = [k for k, v in results.items() if v.get("status") == "error"]
    if failed:
        print(f"\n⚠️  Failed steps: {failed}")
        sys.exit(1)
    else:
        print("\n✅ All pipeline steps completed successfully!")
