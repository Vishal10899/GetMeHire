import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models import Source, Job
from app.ingestion.runner import IngestionRunner
from sqlalchemy import text

db = SessionLocal()

target_ids = [151, 293, 309, 310, 97, 298, 297, 87, 311, 213]

print("=" * 80)
print("EXECUTING TARGETED EARLY-CAREER & CROSS-INDUSTRY INGESTION")
print("=" * 80)

total_discovered = 0
total_inserted = 0
total_updated = 0

for sid in target_ids:
    source = db.query(Source).filter(Source.id == sid).first()
    if not source:
        print(f"[SKIP] Source {sid} not found")
        continue

    print(f"\n[SYNC START] Source #{source.id} - {source.source_name} ({source.source_type})")
    t0 = time.time()
    try:
        run = IngestionRunner.execute_sync(db, source.id)
        elapsed = round(time.time() - t0, 2)
        if run:
            disc = run.records_discovered or 0
            ins = run.records_inserted or 0
            upd = run.records_updated or 0
            total_discovered += disc
            total_inserted += ins
            total_updated += upd
            print(f"[SYNC DONE] Discovered: {disc}, Inserted: {ins}, Updated: {upd} in {elapsed}s (Status: {run.status})")
        else:
            print(f"[SYNC DONE] Run completed with no record in {elapsed}s")
    except Exception as e:
        print(f"[SYNC ERROR] Source #{source.id}: {e}")

# Post-sync fresher friendly count
fresher_cnt = db.execute(text("""
    SELECT count(*) FROM jobs 
    WHERE status IN ('ACTIVE', 'POSSIBLY_STALE') AND (early_career_metadata->>'is_fresher_friendly')::boolean = TRUE;
""")).scalar()

total_active = db.execute(text("""
    SELECT count(*) FROM jobs 
    WHERE status IN ('ACTIVE', 'POSSIBLY_STALE');
""")).scalar()

print("\n" + "=" * 80)
print("EXPANSION INGESTION SUMMARY:")
print(f"Total Discovered across targets: {total_discovered}")
print(f"Total Newly Inserted:           {total_inserted}")
print(f"Total Updated:                  {total_updated}")
print(f"Current Total Active Jobs:      {total_active}")
print(f"Current Total Fresher-Friendly: {fresher_cnt}")
print("=" * 80)

db.close()
