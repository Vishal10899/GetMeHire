"""
GlobalJobs Target 1 — Final Verified Source Onboarding & Sync Script
Expands verified public employer boards across underrepresented countries (Switzerland, UK)
and non-tech industries (Apparel/Retail, Education, Healthcare, Hospitality, Banking).
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal
from app.models import Company, Source, Job, IngestionRun
from app.ingestion.runner import IngestionRunner
from app.ingestion.normalizer import normalize_location_full, get_country_code

FINAL_VERIFIED_SOURCES = [
    {
        "company_name": "On Running",
        "website": "https://www.on.com",
        "career_page_url": "https://careers.on.com",
        "source_name": "On Running Greenhouse Board",
        "source_type": "GREENHOUSE",
        "canonical_source_url": "https://boards.greenhouse.io/onrunning",
        "external_board_id": "onrunning",
        "access_classification": "PUBLIC_ATS",
        "rate_limit_rpm": 60,
        "configuration": {"board_token": "onrunning", "board_name": "onrunning", "max_pages": 5}
    },
    {
        "company_name": "Duolingo",
        "website": "https://www.duolingo.com",
        "career_page_url": "https://careers.duolingo.com",
        "source_name": "Duolingo Greenhouse Board",
        "source_type": "GREENHOUSE",
        "canonical_source_url": "https://boards.greenhouse.io/duolingo",
        "external_board_id": "duolingo",
        "access_classification": "PUBLIC_ATS",
        "rate_limit_rpm": 60,
        "configuration": {"board_token": "duolingo", "board_name": "duolingo", "max_pages": 5}
    },
    {
        "company_name": "Komodo Health",
        "website": "https://www.komodohealth.com",
        "career_page_url": "https://www.komodohealth.com/careers",
        "source_name": "Komodo Health Greenhouse Board",
        "source_type": "GREENHOUSE",
        "canonical_source_url": "https://boards.greenhouse.io/komodohealth",
        "external_board_id": "komodohealth",
        "access_classification": "PUBLIC_ATS",
        "rate_limit_rpm": 60,
        "configuration": {"board_token": "komodohealth", "board_name": "komodohealth", "max_pages": 5}
    },
    {
        "company_name": "Toast",
        "website": "https://pos.toasttab.com",
        "career_page_url": "https://careers.toasttab.com",
        "source_name": "Toast Greenhouse Board",
        "source_type": "GREENHOUSE",
        "canonical_source_url": "https://boards.greenhouse.io/toast",
        "external_board_id": "toast",
        "access_classification": "PUBLIC_ATS",
        "rate_limit_rpm": 60,
        "configuration": {"board_token": "toast", "board_name": "toast", "max_pages": 5}
    },
    {
        "company_name": "Monzo",
        "website": "https://monzo.com",
        "career_page_url": "https://monzo.com/careers",
        "source_name": "Monzo Greenhouse Board",
        "source_type": "GREENHOUSE",
        "canonical_source_url": "https://boards.greenhouse.io/monzo",
        "external_board_id": "monzo",
        "access_classification": "PUBLIC_ATS",
        "rate_limit_rpm": 60,
        "configuration": {"board_token": "monzo", "board_name": "monzo", "max_pages": 5}
    }
]

def run_onboarding():
    db = SessionLocal()
    start_time = time.time()
    print("=" * 70)
    print("GLOBALJOBS TARGET 1: ONBOARDING FINAL VERIFIED EXPANSION SOURCES")
    print("=" * 70)

    base_srcs = db.query(Source).count()
    base_comps = db.query(Company).count()
    base_jobs = db.query(Job).count()
    print(f"BASELINE: {base_srcs} Sources | {base_comps} Companies | {base_jobs} Jobs\n")

    results = []

    for item in FINAL_VERIFIED_SOURCES:
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
            print(f"  [OK] Status: {run.status} | Discovered: {run.records_discovered} | Inserted: {run.records_inserted} | Updated: {run.records_updated} | Unchanged: {run.records_unchanged}")
            results.append({
                "company": cname,
                "source_id": src.id,
                "status": run.status,
                "discovered": run.records_discovered,
                "inserted": run.records_inserted,
                "updated": run.records_updated
            })
        except Exception as e:
            print(f"  [ERROR] Ingestion failed for {cname}: {e}")
            results.append({
                "company": cname,
                "source_id": src.id,
                "status": "FAILED",
                "error": str(e)
            })

    # 4. Post-sync location backfill for any new jobs
    new_jobs_without_code = db.query(Job).filter(Job.country_code.is_(None)).all()
    if new_jobs_without_code:
        print(f"\nNormalizing location metadata for {len(new_jobs_without_code)} records lacking country_code...")
        for j in new_jobs_without_code:
            _, city, region, country, code, remote = normalize_location_full(j.location, j.title)
            if country and not j.country:
                j.country = country
            if city and not j.city:
                j.city = city
            if region and not j.region:
                j.region = region
            if code and not j.country_code:
                j.country_code = code
            if remote != "ONSITE" and j.remote_type == "ONSITE":
                j.remote_type = remote
        db.commit()

    # 5. Final summary audit
    final_srcs = db.query(Source).count()
    final_comps = db.query(Company).count()
    final_jobs = db.query(Job).count()
    active_jobs = db.query(Job).filter(Job.status == "ACTIVE").count()

    print("\n" + "=" * 70)
    print("FINAL ONBOARDING AUDIT RESULTS")
    print("=" * 70)
    print(f"Sources:   {base_srcs} -> {final_srcs} (+{final_srcs - base_srcs})")
    print(f"Companies: {base_comps} -> {final_comps} (+{final_comps - base_comps})")
    print(f"Jobs:      {base_jobs} -> {final_jobs} (+{final_jobs - base_jobs} new genuine vacancies)")
    print(f"Active:    {active_jobs} Active listings")
    print(f"Elapsed:   {round(time.time() - start_time, 2)}s")

    for r in results:
        print(f"  - {r['company']}: {r.get('discovered', 0)} discovered, {r.get('inserted', 0)} inserted (Status: {r['status']})")

    db.close()

if __name__ == "__main__":
    run_onboarding()
