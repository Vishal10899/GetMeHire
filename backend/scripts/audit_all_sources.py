"""
Comprehensive audit of all registered sources in GetMeHire PostgreSQL database.
Gathers:
- Employer canonical name
- Country
- Source type / ATS provider
- Source URL
- Adapter
- Active status
- Last successful crawl / last complete sync
- Last attempted crawl
- Next scheduled synchronization
- Total discovered records
- Total active vacancies in DB
- Failure reason / error history
- Source health status
"""

import os
import sys
import json
import datetime
from sqlalchemy import func

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models import Source, Company, IngestionRun, Job
from app.ingestion.scheduler import IngestionScheduler


def main():
    db = SessionLocal()
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    
    try:
        sources = db.query(Source).order_by(Source.id).all()
        print(f"Total Sources Registered: {len(sources)}")
        
        audit_records = []
        health_summary = {"HEALTHY": 0, "DEGRADED": 0, "FAILING": 0, "QUARANTINED": 0, "OTHER": 0}
        never_succeeded = []
        never_attempted = []
        active_vacancy_totals = {}
        
        # Precompute job counts per source
        job_counts = db.query(
            Job.source_id,
            func.count(Job.id).filter(Job.status == "ACTIVE").label("active_jobs"),
            func.count(Job.id).label("total_jobs")
        ).group_by(Job.source_id).all()
        
        job_count_map = {r[0]: {"active": r[1], "total": r[2]} for r in job_counts}

        for s in sources:
            company = db.query(Company).filter(Company.id == s.company_id).first()
            comp_name = company.canonical_name if company else (s.configuration or {}).get("company_name", "Unknown")
            comp_country = company.country if company else (s.configuration or {}).get("country", "Unknown")
            
            h_status = s.health_status or "UNKNOWN"
            health_summary[h_status] = health_summary.get(h_status, 0) + 1
            
            interval_secs = IngestionScheduler.parse_cron_interval_seconds(s.sync_schedule_cron)
            next_sync = None
            if s.last_attempted_at:
                last_att = s.last_attempted_at
                if last_att.tzinfo is None:
                    last_att = last_att.replace(tzinfo=datetime.timezone.utc)
                next_sync = (last_att + datetime.timedelta(seconds=interval_secs)).isoformat()
            
            jc = job_count_map.get(s.id, {"active": 0, "total": 0})
            
            # Extract last error
            last_error = None
            if s.error_history and len(s.error_history) > 0:
                last_error = s.error_history[-1].get("error")
                
            rec = {
                "source_id": s.id,
                "employer": comp_name,
                "country": comp_country,
                "ats_provider": s.source_type,
                "source_url": s.canonical_source_url,
                "adapter": f"{s.source_type.title()}Adapter",
                "is_active": s.is_active,
                "health_status": h_status,
                "cron": s.sync_schedule_cron,
                "interval_hours": interval_secs / 3600.0,
                "last_attempted_at": s.last_attempted_at.isoformat() if s.last_attempted_at else None,
                "last_successful_sync_at": s.last_successful_sync_at.isoformat() if s.last_successful_sync_at else None,
                "last_complete_sync_at": s.last_complete_sync_at.isoformat() if s.last_complete_sync_at else None,
                "next_scheduled_sync": next_sync,
                "active_vacancies_in_db": jc["active"],
                "total_vacancies_in_db": jc["total"],
                "last_error": last_error,
            }
            audit_records.append(rec)
            
            if not s.last_attempted_at:
                never_attempted.append(rec)
            elif not s.last_successful_sync_at:
                never_succeeded.append(rec)

        print("\n--- Health Summary ---")
        for k, v in health_summary.items():
            print(f"  {k}: {v}")

        print(f"\n--- Crawl Success Statistics ---")
        print(f"  Never Attempted: {len(never_attempted)}")
        print(f"  Attempted but Never Succeeded: {len(never_succeeded)}")
        print(f"  Successfully Crawled At Least Once: {len(sources) - len(never_succeeded) - len(never_attempted)}")

        # Print sample never succeeded
        if never_succeeded:
            print(f"\nSample Sources Failing / Never Succeeded ({len(never_succeeded)} total):")
            for ns in never_succeeded[:10]:
                print(f"  • Source #{ns['source_id']} ({ns['employer']}, {ns['ats_provider']}): Error: {str(ns['last_error'])[:80]}")

        # Save complete audit report to JSON
        out_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "source_audit_complete.json"))
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump({
                "audit_timestamp": now_utc.isoformat(),
                "total_sources": len(sources),
                "health_summary": health_summary,
                "never_attempted_count": len(never_attempted),
                "never_succeeded_count": len(never_succeeded),
                "successfully_crawled_count": len(sources) - len(never_succeeded) - len(never_attempted),
                "sources": audit_records
            }, f, indent=2)

        print(f"\n[OK] Complete audit saved to: {out_file}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
