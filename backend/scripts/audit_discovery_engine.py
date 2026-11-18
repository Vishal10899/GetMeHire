import os
import sys

sys.path.insert(0, os.path.abspath("backend"))

from app.core.database import SessionLocal
from app.models import Company, Source, Job, IngestionRun
from sqlalchemy import func

def audit():
    db = SessionLocal()
    print("=" * 60)
    print("GLOBALJOBS — COMPLETE DISCOVERY ENGINE AUDIT")
    print("=" * 60)

    total_companies = db.query(Company).count()
    verified_companies = db.query(Company).filter(Company.identity_status == "VERIFIED").count()
    total_sources = db.query(Source).count()
    active_sources = db.query(Source).filter(Source.is_active == True).count()
    healthy_sources = db.query(Source).filter(Source.health_status == "HEALTHY").count()
    total_jobs = db.query(Job).count()
    active_jobs = db.query(Job).filter(Job.status == "ACTIVE").count()
    stale_jobs = db.query(Job).filter(Job.status == "POSSIBLY_STALE").count()
    closed_jobs = db.query(Job).filter(Job.status == "CLOSED").count()
    total_runs = db.query(IngestionRun).count()

    print(f"Total Companies:        {total_companies} (Verified: {verified_companies})")
    print(f"Total Sources:          {total_sources} (Active: {active_sources}, Healthy: {healthy_sources})")
    print(f"Total Jobs:             {total_jobs} (Active: {active_jobs}, Stale: {stale_jobs}, Closed: {closed_jobs})")
    print(f"Total Ingestion Runs:   {total_runs}")

    print("\n--- SOURCES BREAKDOWN BY TYPE ---")
    type_counts = db.query(Source.source_type, func.count(Source.id)).group_by(Source.source_type).all()
    for st, count in type_counts:
        print(f"  {st:<18}: {count} sources")

    print("\n--- ALL SOURCES STATUS & VACANCY COUNT ---")
    sources = db.query(Source).order_by(Source.id).all()
    for s in sources:
        comp = db.query(Company).filter(Company.id == s.company_id).first()
        comp_name = comp.canonical_name if comp else "Unknown"
        jobs_count = db.query(Job).filter(Job.source_id == s.id, Job.status == "ACTIVE").count()
        last_sync = s.last_successful_sync_at.strftime('%Y-%m-%d %H:%M') if s.last_successful_sync_at else "Never"
        print(f"  [{s.id:2d}] {comp_name:<28} | {s.source_type:<14} | Board: {str(s.external_board_id):<18} | Active: {str(s.is_active):<5} | Health: {s.health_status:<7} | Active Jobs: {jobs_count:3d} | Last Sync: {last_sync}")

    print("\n--- RECENT INGESTION RUNS (LAST 10) ---")
    recent_runs = db.query(IngestionRun).order_by(IngestionRun.id.desc()).limit(10).all()
    for r in recent_runs:
        src = db.query(Source).filter(Source.id == r.source_id).first()
        src_name = src.source_name if src else "Unknown"
        print(f"  Run #{r.id:<3} | Source: {src_name:<25} | Status: {r.status:<10} | Discovered: {r.records_discovered:<3} | Inserted: {r.records_inserted:<3} | Updated: {r.records_updated:<3} | Error: {r.error_message or 'None'}")

    db.close()

if __name__ == "__main__":
    audit()
