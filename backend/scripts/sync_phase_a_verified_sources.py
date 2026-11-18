import sys
import os
from typing import Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal
from app.models import Company, Source, Job, IngestionRun
from app.ingestion.runner import IngestionRunner

VERIFIED_SOURCES = [
    {
        "company_name": "Arondite",
        "website": "https://www.arondite.com",
        "career_page_url": "https://apply.workable.com/arondite",
        "source_name": "Arondite Workable Board",
        "source_type": "WORKABLE",
        "canonical_source_url": "https://apply.workable.com/arondite",
        "external_board_id": "arondite",
        "access_classification": "PUBLIC_ATS",
        "rate_limit_rpm": 30,
        "configuration": {"company_slug": "arondite", "fetch_details": True}
    },
    {
        "company_name": "CERN",
        "website": "https://home.cern",
        "career_page_url": "https://jobs.smartrecruiters.com/CERN",
        "source_name": "CERN SmartRecruiters Postings",
        "source_type": "SMARTRECRUITERS",
        "canonical_source_url": "https://api.smartrecruiters.com/v1/companies/cern/postings",
        "external_board_id": "cern",
        "access_classification": "PUBLIC_ATS",
        "rate_limit_rpm": 60,
        "configuration": {"company_slug": "cern", "page_size": 100, "fetch_details": True}
    },
    {
        "company_name": "Personio",
        "website": "https://www.personio.com",
        "career_page_url": "https://personio.jobs.personio.de",
        "source_name": "Personio XML Job Feed",
        "source_type": "PERSONIO",
        "canonical_source_url": "https://personio.jobs.personio.de/xml?language=en",
        "external_board_id": "personio",
        "access_classification": "PUBLIC_ATS",
        "rate_limit_rpm": 30,
        "configuration": {"company_slug": "personio", "feed_domain": "de"}
    },
    {
        "company_name": "Everphone",
        "website": "https://www.everphone.com",
        "career_page_url": "https://everphone.jobs.personio.de",
        "source_name": "Everphone Personio Feed",
        "source_type": "PERSONIO",
        "canonical_source_url": "https://everphone.jobs.personio.de/xml?language=en",
        "external_board_id": "everphone",
        "access_classification": "PUBLIC_ATS",
        "rate_limit_rpm": 30,
        "configuration": {"company_slug": "everphone", "feed_domain": "de"}
    },
    {
        "company_name": "Remotive",
        "website": "https://remotive.com",
        "career_page_url": "https://remotive.com/api/remote-jobs",
        "source_name": "Remotive Public Remote Feed",
        "source_type": "REMOTIVE",
        "canonical_source_url": "https://remotive.com/api/remote-jobs",
        "external_board_id": "remotive-global",
        "access_classification": "PUBLIC_FEED",
        "rate_limit_rpm": 10,
        "configuration": {"limit": 25}
    }
]

def run_phase_a_sync():
    db = SessionLocal()
    print("=" * 70)
    print("PHASE A: VERIFIED MULTI-SOURCE INGESTION EXECUTION")
    print("=" * 70)

    # 1. Baseline verification
    baseline_sources = db.query(Source).count()
    baseline_jobs = db.query(Job).count()
    baseline_companies = db.query(Company).count()
    print(f"BASELINE: {baseline_sources} Sources, {baseline_companies} Companies, {baseline_jobs} Jobs")

    sync_results = []

    for item in VERIFIED_SOURCES:
        cname = item["company_name"]
        print(f"\nProcessing verified source: {item['source_name']} ({item['source_type']})")

        # 1. Company entity
        comp = db.query(Company).filter(Company.canonical_name == cname).first()
        if not comp:
            comp = Company(
                canonical_name=cname,
                website=item["website"],
                career_page_url=item["career_page_url"],
                identity_status="VERIFIED"
            )
            db.add(comp)
            db.flush()
            print(f"  Created Company: {cname} (ID: {comp.id})")
        else:
            print(f"  Existing Company: {cname} (ID: {comp.id})")

        # 2. Source entity
        source = db.query(Source).filter(
            Source.company_id == comp.id,
            Source.source_type == item["source_type"]
        ).first()

        if not source:
            source = Source(
                company_id=comp.id,
                source_name=item["source_name"],
                source_type=item["source_type"],
                canonical_source_url=item["canonical_source_url"],
                external_board_id=item["external_board_id"],
                access_classification=item["access_classification"],
                rate_limit_rpm=item["rate_limit_rpm"],
                configuration=item["configuration"],
                is_active=True,
                health_status="HEALTHY"
            )
            db.add(source)
            db.commit()
            db.refresh(source)
            print(f"  Registered Source: {source.source_name} (ID: {source.id})")
        else:
            print(f"  Found Source: {source.source_name} (ID: {source.id})")

        # 3. Execute safe sync via IngestionRunner
        try:
            print(f"  Executing ingestion sync for Source {source.id}...")
            run = IngestionRunner.execute_sync(db, source.id)
            print(f"  Sync Status: {run.status}")
            print(f"    Discovered: {run.records_discovered}")
            print(f"    Inserted:   {run.records_inserted}")
            print(f"    Updated:    {run.records_updated}")
            print(f"    Unchanged:  {run.records_unchanged}")
            print(f"    Rejected:   {run.records_rejected}")

            # Verify application URLs for inserted jobs
            source_jobs = db.query(Job).filter(Job.source_id == source.id).all()
            valid_urls = sum(1 for j in source_jobs if j.application_url and j.application_url.startswith("http"))
            url_pct = (valid_urls / len(source_jobs) * 100) if source_jobs else 100.0

            sync_results.append({
                "source_name": source.source_name,
                "source_type": source.source_type,
                "status": run.status,
                "discovered": run.records_discovered,
                "inserted": run.records_inserted,
                "unchanged": run.records_unchanged,
                "rejected": run.records_rejected,
                "total_source_jobs": len(source_jobs),
                "valid_url_pct": url_pct
            })
        except Exception as e:
            print(f"  FAILED to sync source {source.id}: {e}")
            sync_results.append({
                "source_name": source.source_name,
                "source_type": source.source_type,
                "status": "FAILED",
                "error": str(e)
            })

    # 4. Final Database Audit
    final_sources = db.query(Source).count()
    final_jobs = db.query(Job).count()
    final_active_jobs = db.query(Job).filter(Job.status == "ACTIVE").count()
    final_companies = db.query(Company).count()

    print("\n" + "=" * 70)
    print("FINAL DATABASE RECONCILIATION")
    print("=" * 70)
    print(f"Total Sources:   {final_sources} (New: +{final_sources - baseline_sources})")
    print(f"Total Companies: {final_companies} (New: +{final_companies - baseline_companies})")
    print(f"Total Jobs:      {final_jobs} (New: +{final_jobs - baseline_jobs})")
    print(f"Active Jobs:     {final_active_jobs}")

    # Verify original 15 sources are still intact and healthy
    orig_sources = db.query(Source).filter(Source.id <= 15).all()
    print(f"Original Sources Intact: {len(orig_sources)}/15 (All HEALTHY: {all(s.health_status == 'HEALTHY' for s in orig_sources)})")

    db.close()

if __name__ == "__main__":
    run_phase_a_sync()
