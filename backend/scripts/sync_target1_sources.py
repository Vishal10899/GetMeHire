"""
GlobalJobs Target 1 — Verified Worldwide Source Expansion Script
Registers and synchronizes verified public employer boards across Greenhouse, Ashby, and Recruitee,
expanding global coverage across UK, Europe, and Remote Worldwide while preserving 100% of existing data.
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal
from app.models import Company, Source, Job, IngestionRun
from app.ingestion.runner import IngestionRunner
from app.ingestion.normalizer import normalize_location_full, get_country_code

TARGET_1_VERIFIED_SOURCES = [
    {
        "company_name": "Canonical",
        "website": "https://canonical.com",
        "career_page_url": "https://canonical.com/careers",
        "source_name": "Canonical Greenhouse Board",
        "source_type": "GREENHOUSE",
        "canonical_source_url": "https://boards.greenhouse.io/canonical",
        "external_board_id": "canonical",
        "access_classification": "PUBLIC_ATS",
        "rate_limit_rpm": 60,
        "configuration": {"board_token": "canonical", "board_name": "canonical", "max_pages": 5}
    },
    {
        "company_name": "Bunq",
        "website": "https://www.bunq.com",
        "career_page_url": "https://jobs.bunq.com",
        "source_name": "Bunq Recruitee Board",
        "source_type": "RECRUITEE",
        "canonical_source_url": "https://bunq.recruitee.com",
        "external_board_id": "bunq",
        "access_classification": "PUBLIC_ATS",
        "rate_limit_rpm": 30,
        "configuration": {"company_slug": "bunq"}
    },
    {
        "company_name": "Channable",
        "website": "https://www.channable.com",
        "career_page_url": "https://careers.channable.com",
        "source_name": "Channable Recruitee Board",
        "source_type": "RECRUITEE",
        "canonical_source_url": "https://channable.recruitee.com",
        "external_board_id": "channable",
        "access_classification": "PUBLIC_ATS",
        "rate_limit_rpm": 30,
        "configuration": {"company_slug": "channable"}
    },
    {
        "company_name": "Linear",
        "website": "https://linear.app",
        "career_page_url": "https://linear.app/careers",
        "source_name": "Linear Ashby Board",
        "source_type": "ASHBY",
        "canonical_source_url": "https://jobs.ashbyhq.com/linear",
        "external_board_id": "linear",
        "access_classification": "PUBLIC_ATS",
        "rate_limit_rpm": 30,
        "configuration": {"company_slug": "linear", "board_name": "linear"}
    },
    {
        "company_name": "Mozilla",
        "website": "https://www.mozilla.org",
        "career_page_url": "https://www.mozilla.org/en-US/careers/",
        "source_name": "Mozilla Greenhouse Board",
        "source_type": "GREENHOUSE",
        "canonical_source_url": "https://boards.greenhouse.io/mozilla",
        "external_board_id": "mozilla",
        "access_classification": "PUBLIC_ATS",
        "rate_limit_rpm": 60,
        "configuration": {"board_token": "mozilla", "board_name": "mozilla", "max_pages": 5}
    }
]

def run_sync():
    db = SessionLocal()
    start_time = time.time()
    print("=" * 70)
    print("GLOBALJOBS TARGET 1: EXPANDING WORLDWIDE VERIFIED SOURCES")
    print("=" * 70)

    # Baseline audit
    base_srcs = db.query(Source).count()
    base_comps = db.query(Company).count()
    base_jobs = db.query(Job).count()
    print(f"BASELINE: {base_srcs} Sources | {base_comps} Companies | {base_jobs} Jobs\n")

    synced_sources = []

    for item in TARGET_1_VERIFIED_SOURCES:
        cname = item["company_name"]
        print(f"Processing: {cname} ({item['source_type']})...")

        # 1. Company entity resolution
        comp = db.query(Company).filter(Company.canonical_name.ilike(cname)).first()
        if not comp:
            comp = Company(
                canonical_name=cname,
                website=item["website"],
                career_page_url=item["career_page_url"],
                identity_status="VERIFIED"
            )
            db.add(comp)
            db.flush()
            print(f"  [+] Created Company record: {cname} (ID: {comp.id})")
        else:
            print(f"  [=] Resolved existing Company record: {cname} (ID: {comp.id})")

        # 2. Source entity resolution
        src = db.query(Source).filter(
            Source.company_id == comp.id,
            Source.source_type == item["source_type"]
        ).first()

        if not src:
            src = Source(
                company_id=comp.id,
                source_name=item["source_name"],
                source_type=item["source_type"],
                canonical_source_url=item["canonical_source_url"],
                external_board_id=item["external_board_id"],
                access_classification=item["access_classification"],
                rate_limit_rpm=item["rate_limit_rpm"],
                concurrency_limit=1,
                configuration=item["configuration"],
                health_status="HEALTHY",
                is_active=True
            )
            db.add(src)
            db.commit()
            db.refresh(src)
            print(f"  [+] Registered Source: {src.source_name} (ID: {src.id})")
        else:
            print(f"  [=] Source already registered: {src.source_name} (ID: {src.id})")

        # 3. Synchronize jobs
        try:
            print(f"  [*] Executing ingestion sync for Source #{src.id}...")
            run = IngestionRunner.execute_sync(db, src.id)
            print(f"  [OK] Status: {run.status} | Discovered: {run.records_discovered} | Inserted: {run.records_inserted} | Updated: {run.records_updated}")
            synced_sources.append({
                "source_id": src.id,
                "company": cname,
                "status": run.status,
                "discovered": run.records_discovered,
                "inserted": run.records_inserted
            })
        except Exception as e:
            print(f"  [ERROR] Ingestion failed: {e}")

    # Post-sync location backfill on any newly ingested records lacking country_code
    new_jobs_without_code = db.query(Job).filter(Job.country_code.is_(None)).all()
    if new_jobs_without_code:
        print(f"\nNormalizing location metadata for {len(new_jobs_without_code)} new records...")
        for j in new_jobs_without_code:
            _, city, region, country, code, remote = normalize_location_full(j.location, j.title)
            if country:
                j.country = country
            if city:
                j.city = city
            if region:
                j.region = region
            if code:
                j.country_code = code
            if remote != "ONSITE" and j.remote_type == "ONSITE":
                j.remote_type = remote
        db.commit()

    # Final summary audit
    final_srcs = db.query(Source).count()
    final_comps = db.query(Company).count()
    final_jobs = db.query(Job).count()
    active_jobs = db.query(Job).filter(Job.status == "ACTIVE").count()

    print("\n" + "=" * 70)
    print("EXPANSION AUDIT RESULTS")
    print("=" * 70)
    print(f"Sources:   {base_srcs} -> {final_srcs} (+{final_srcs - base_srcs})")
    print(f"Companies: {base_comps} -> {final_comps} (+{final_comps - base_comps})")
    print(f"Jobs:      {base_jobs} -> {final_jobs} (+{final_jobs - base_jobs} new genuine vacancies)")
    print(f"Active:    {active_jobs} Active listings")
    print(f"Elapsed:   {round(time.time() - start_time, 2)}s")
    db.close()

if __name__ == "__main__":
    run_sync()
