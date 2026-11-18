"""
Live Ingestion Expansion - Batch 2:
Synchronizes high-capacity, verified cross-industry employers:
- Anduril Industries (Defense & Aerospace, Greenhouse)
- Roblox (Gaming & Metaverse, Greenhouse)
- Epic Games (Gaming & 3D, Greenhouse)
- Braze (Customer Engagement, Greenhouse)
- Klaviyo (Marketing Automation, Greenhouse)
- Ramp (Fintech, Ashby)
- OpenAI (AI, Ashby)
- Palantir Technologies (Enterprise Data, Lever)
- Gusto (Fintech & Payroll, Greenhouse)
- Carta (Fintech & Equity, Greenhouse)
- Ripple (Fintech & Crypto, Greenhouse)
- Relativity Space (Aerospace, Greenhouse)
- Checkr (HR & Compliance, Greenhouse)
"""

import os
import sys
import json
import time
import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models import Source, Company, IngestionRun, Job
from app.ingestion.runner import IngestionRunner


def main():
    print("=" * 80)
    print("GETMEHIRE LIVE ATS INGESTION & GLOBAL EXPANSION - BATCH 2")
    print("=" * 80)

    db = SessionLocal()
    start_time = time.time()

    target_slugs_b2 = [
        ("Gusto", "gusto", "GREENHOUSE"),
        ("Carta", "carta", "GREENHOUSE"),
        ("Ripple", "ripple", "GREENHOUSE"),
        ("Ramp", "ramp", "ASHBY"),
        ("Roblox", "roblox", "GREENHOUSE"),
        ("Epic Games", "epicgames", "GREENHOUSE"),
        ("Klaviyo", "klaviyo", "GREENHOUSE"),
        ("Braze", "braze", "GREENHOUSE"),
        ("OpenAI", "openai", "ASHBY"),
        ("Palantir Technologies", "palantir", "LEVER"),
        ("Relativity Space", "relativity", "GREENHOUSE"),
        ("Checkr", "checkr", "GREENHOUSE"),
        ("Anduril Industries", "andurilindustries", "GREENHOUSE"),
    ]

    print(f"Targeting {len(target_slugs_b2)} large-scale cross-industry employers for live synchronization...\n")

    summary_records = []
    total_discovered = 0
    total_inserted = 0
    total_updated = 0
    total_unchanged = 0
    successful_sources = 0
    failed_sources = 0

    for emp_name, slug, ats in target_slugs_b2:
        source = db.query(Source).filter(
            Source.source_type == ats,
            Source.external_board_id == slug
        ).first()

        if not source:
            print(f"[SKIP] Source not found for {emp_name} ({ats}, {slug})")
            continue

        print(f"--- Synchronizing #{source.id}: {emp_name} ({ats}) ---")
        t0 = time.time()
        try:
            run = IngestionRunner.execute_sync(db, source.id)
            dur = round(time.time() - t0, 2)
            
            sample_job = db.query(Job).filter(
                Job.source_id == source.id,
                Job.status == "ACTIVE"
            ).order_by(Job.id.desc()).first()

            sample_url = sample_job.application_url if sample_job else None
            sample_title = sample_job.title if sample_job else None
            sample_loc = sample_job.location if sample_job else None

            rec = {
                "source_id": source.id,
                "employer_name": emp_name,
                "ats_provider": ats,
                "status": run.status,
                "duration_seconds": dur,
                "records_discovered": run.records_discovered,
                "records_inserted": run.records_inserted,
                "records_updated": run.records_updated,
                "records_unchanged": run.records_unchanged,
                "records_rejected": run.records_rejected,
                "sample_job_title": sample_title,
                "sample_job_location": sample_loc,
                "sample_application_url": sample_url,
                "error": run.error_message
            }
            summary_records.append(rec)

            total_discovered += run.records_discovered
            total_inserted += run.records_inserted
            total_updated += run.records_updated
            total_unchanged += run.records_unchanged

            if run.status in ["SUCCESS", "PARTIAL"]:
                successful_sources += 1
                print(f"[SUCCESS] Discovered: {run.records_discovered} | Inserted: {run.records_inserted} | Updated: {run.records_updated} | Unchanged: {run.records_unchanged}")
                if sample_job:
                    print(f"  • Sample Job: '{sample_title}' ({sample_loc})")
                    print(f"  • Destination URL: {sample_url}")
            else:
                failed_sources += 1
                print(f"[FAILED] Error: {run.error_message}")

        except Exception as exc:
            failed_sources += 1
            print(f"[ERROR] Exception during sync of {emp_name}: {exc}")
            summary_records.append({
                "source_id": source.id,
                "employer_name": emp_name,
                "ats_provider": ats,
                "status": "FAILED",
                "error": str(exc)
            })

    total_db_jobs = db.query(Job).count()
    active_db_jobs = db.query(Job).filter(Job.status == "ACTIVE").count()
    total_db_companies = db.query(Company).count()

    overall_summary = {
        "execution_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_sources_attempted": len(summary_records),
        "successful_sources_crawled": successful_sources,
        "failed_sources": failed_sources,
        "total_jobs_discovered": total_discovered,
        "total_jobs_inserted": total_inserted,
        "total_jobs_updated": total_updated,
        "total_duplicates_skipped": total_unchanged,
        "database_active_vacancies_now": active_db_jobs,
        "database_total_vacancies_now": total_db_jobs,
        "database_companies_count": total_db_companies,
        "total_duration_seconds": round(time.time() - start_time, 2),
        "source_runs": summary_records
    }

    out_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "live_expansion_batch2_report.json"))
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(overall_summary, f, indent=2)

    print("\n" + "=" * 80)
    print("BATCH 2 INGESTION EXECUTION SUMMARY:")
    print(f"  • Sources Attempted: {len(summary_records)}")
    print(f"  • Sources Successfully Crawled: {successful_sources}")
    print(f"  • Failed Sources: {failed_sources}")
    print(f"  • Total Jobs Discovered: {total_discovered}")
    print(f"  • Total New Jobs Inserted: {total_inserted}")
    print(f"  • Total Jobs Updated: {total_updated}")
    print(f"  • Duplicates / Unchanged Skipped: {total_unchanged}")
    print(f"  • Current Active Vacancies in PostgreSQL: {active_db_jobs}")
    print(f"  • Total Vacancies in PostgreSQL: {total_db_jobs}")
    print(f"  • Total Employers in PostgreSQL: {total_db_companies}")
    print(f"  • Report Written to: {out_file}")
    print("=" * 80)

    db.close()


if __name__ == "__main__":
    main()
