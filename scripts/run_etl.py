#!/usr/bin/env python3
"""
ETL orchestrator - runs World Bank and OECD ETL pipelines in sequence.
"""
import sys
import logging
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


def run_etl_pipeline():
    print("\n" + "="*60)
    print("ETL PIPELINE - Country Stats Dashboard")
    print("="*60)
    start_time = datetime.utcnow()
    
    results = {}
    
    # Step 1: World Bank ETL
    print("\n[1/2] Running World Bank ETL...")
    try:
        from etl.worldbank_client import run_worldbank_etl
        wb_stats = run_worldbank_etl()
        results["worldbank"] = {"status": "success", **wb_stats}
        print(f"  ✓ World Bank ETL: {wb_stats}")
    except Exception as e:
        logger.error(f"World Bank ETL failed: {e}")
        results["worldbank"] = {"status": "error", "error": str(e)}
        print(f"  ✗ World Bank ETL failed: {e}")
    
    # Step 2: OECD ETL
    print("\n[2/2] Running OECD ETL...")
    try:
        from etl.oecd_client import run_oecd_etl
        oecd_stats = run_oecd_etl()
        results["oecd"] = {"status": "success", **oecd_stats}
        print(f"  ✓ OECD ETL: {oecd_stats}")
    except Exception as e:
        logger.error(f"OECD ETL failed: {e}")
        results["oecd"] = {"status": "error", "error": str(e)}
        print(f"  ✗ OECD ETL failed: {e}")
    
    # Summary
    elapsed = (datetime.utcnow() - start_time).total_seconds()
    print(f"\n{'='*60}")
    print(f"ETL Pipeline Complete - {elapsed:.1f}s")
    
    total_fetched = sum(r.get("fetched", 0) for r in results.values())
    total_upserted = sum(r.get("upserted", 0) for r in results.values())
    print(f"  Total records fetched:  {total_fetched}")
    print(f"  Total records upserted: {total_upserted}")
    
    return results


if __name__ == "__main__":
    results = run_etl_pipeline()
    # Exit with error if any pipeline failed
    if any(r.get("status") == "error" for r in results.values()):
        sys.exit(1)
