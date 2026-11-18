import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models import Job, Source, IngestionRun

db = SessionLocal()
try:
    total_jobs = db.query(Job).filter(Job.source_id == 123).count()
    active_jobs = db.query(Job).filter(Job.source_id == 123, Job.status == "ACTIVE").count()
    print(f"Total jobs for Source #123 (Delivery Hero): {total_jobs} (Active: {active_jobs})")

    latest_jobs = db.query(Job).filter(Job.source_id == 123).order_by(Job.id.desc()).limit(5).all()
    print("\nLatest 5 Jobs Inserted from Source #123:")
    for j in latest_jobs:
        print(f"  • Job #{j.id}: '{j.title}' | Loc: '{j.location}' | Arrangement: {j.work_arrangement} | FirstSeen: {j.first_seen_at}")
        print(f"    URL: {j.application_url}")

    # Check Run 932
    r932 = db.query(IngestionRun).filter(IngestionRun.id == 932).first()
    if r932:
        print(f"\nRun #932 Details:")
        print(f"  Status: {r932.status}")
        print(f"  Duration: {r932.duration_seconds}s")
        print(f"  Discovered: {r932.records_discovered}")
        print(f"  Inserted: {r932.records_inserted}")
        print(f"  Updated: {r932.records_updated}")
        print(f"  Pagination Checkpoint: {r932.pagination_checkpoint}")
finally:
    db.close()
