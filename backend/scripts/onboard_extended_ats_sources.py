import os
import sys

sys.path.insert(0, os.path.abspath("backend"))

from app.core.database import SessionLocal
from app.models import Company, Source, Job
from app.ingestion.runner import IngestionRunner

EXTENDED_SOURCES = [
    # 1. Teamtailor
    {
        "company_name": "Teamtailor",
        "website": "https://www.teamtailor.com",
        "career_page_url": "https://career.teamtailor.com",
        "industry": "Software & IT",
        "country": "Sweden",
        "operating_region": "Europe & Global",
        "ats_provider": "TEAMTAILOR",
        "ats_board_id": "teamtailor",
        "canonical_source_url": "https://career.teamtailor.com/jobs.rss",
        "configuration": {"company_slug": "teamtailor", "feed_url": "https://career.teamtailor.com/jobs.rss"}
    },
    # 2. Workable: Fortanix
    {
        "company_name": "Fortanix",
        "website": "https://www.fortanix.com",
        "career_page_url": "https://apply.workable.com/fortanix",
        "industry": "Software & IT",
        "country": "United States",
        "operating_region": "North America & India",
        "ats_provider": "WORKABLE",
        "ats_board_id": "fortanix",
        "canonical_source_url": "https://apply.workable.com/fortanix",
        "configuration": {"company_slug": "fortanix", "max_pages": 5, "fetch_details": True}
    },
    # 3. Workable: Propeller Aero
    {
        "company_name": "Propeller Aero",
        "website": "https://www.propelleraero.com",
        "career_page_url": "https://apply.workable.com/propeller",
        "industry": "Construction and Infrastructure",
        "country": "Australia",
        "operating_region": "Global",
        "ats_provider": "WORKABLE",
        "ats_board_id": "propeller",
        "canonical_source_url": "https://apply.workable.com/propeller",
        "configuration": {"company_slug": "propeller", "max_pages": 5, "fetch_details": True}
    },
    # 4. Breezy HR: Helpware
    {
        "company_name": "Helpware",
        "website": "https://www.helpware.com",
        "career_page_url": "https://helpware-inc.breezy.hr",
        "industry": "Consulting",
        "country": "United States",
        "operating_region": "Global",
        "ats_provider": "BREEZY",
        "ats_board_id": "helpware-inc",
        "canonical_source_url": "https://helpware-inc.breezy.hr/json",
        "configuration": {"company_slug": "helpware-inc"}
    },
    # 5. Breezy HR: Anovia Payments
    {
        "company_name": "Anovia Payments",
        "website": "https://anoviapayments.com",
        "career_page_url": "https://anovia.breezy.hr",
        "industry": "Finance & Banking",
        "country": "United States",
        "operating_region": "North America",
        "ats_provider": "BREEZY",
        "ats_board_id": "anovia",
        "canonical_source_url": "https://anovia.breezy.hr/json",
        "configuration": {"company_slug": "anovia"}
    },
    # 6. SmartRecruiters: Eurofins
    {
        "company_name": "Eurofins Scientific",
        "website": "https://www.eurofins.com",
        "career_page_url": "https://careers.eurofins.com",
        "industry": "Biotechnology",
        "country": "Luxembourg",
        "operating_region": "Europe & Global",
        "ats_provider": "SMARTRECRUITERS",
        "ats_board_id": "eurofins",
        "canonical_source_url": "https://jobs.smartrecruiters.com/eurofins",
        "configuration": {"company_slug": "eurofins", "page_size": 50, "max_pages": 5, "fetch_details": True}
    },
    # 7. SmartRecruiters: Delivery Hero
    {
        "company_name": "Delivery Hero",
        "website": "https://www.deliveryhero.com",
        "career_page_url": "https://careers.deliveryhero.com",
        "industry": "Logistics & Supply Chain",
        "country": "Germany",
        "operating_region": "Global",
        "ats_provider": "SMARTRECRUITERS",
        "ats_board_id": "deliveryhero",
        "canonical_source_url": "https://jobs.smartrecruiters.com/deliveryhero",
        "configuration": {"company_slug": "deliveryhero", "page_size": 50, "max_pages": 5, "fetch_details": True}
    },
]

def main():
    db = SessionLocal()
    print("=" * 65)
    print("ONBOARDING EXTENDED ATS SOURCES (TEAMTAILOR, BREEZY, WORKABLE, SMARTRECRUITERS)")
    print("=" * 65)

    synced = []

    for item in EXTENDED_SOURCES:
        c_name = item["company_name"]
        print(f"\nProcessing: {c_name} [{item['ats_provider']}]...")

        comp = db.query(Company).filter(Company.canonical_name == c_name).first()
        if not comp:
            comp = Company(
                canonical_name=c_name,
                website=item["website"],
                career_page_url=item["career_page_url"],
                identity_status="VERIFIED",
                industry=item["industry"],
                country=item["country"],
                operating_region=item["operating_region"],
                ats_provider=item["ats_provider"],
                ats_board_id=item["ats_board_id"],
                discovery_source="Official Career Page"
            )
            db.add(comp)
            db.flush()
            print(f"  ✓ Created Company: {c_name} (ID: {comp.id})")
        else:
            comp.website = item["website"]
            comp.career_page_url = item["career_page_url"]
            comp.identity_status = "VERIFIED"
            comp.industry = item["industry"]
            comp.country = item["country"]
            comp.operating_region = item["operating_region"]
            comp.ats_provider = item["ats_provider"]
            comp.ats_board_id = item["ats_board_id"]
            db.flush()
            print(f"  ✓ Updated Company: {c_name} (ID: {comp.id})")

        src = db.query(Source).filter(
            Source.company_id == comp.id,
            Source.external_board_id == item["ats_board_id"]
        ).first()

        if not src:
            src = Source(
                company_id=comp.id,
                source_name=f"{c_name} {item['ats_provider'].capitalize()} Board",
                source_type=item["ats_provider"],
                canonical_source_url=item["canonical_source_url"],
                external_board_id=item["ats_board_id"],
                access_classification="PUBLIC_API",
                sync_schedule_cron="0 */4 * * *",
                rate_limit_rpm=60,
                concurrency_limit=1,
                is_active=True,
                health_status="HEALTHY",
                configuration=item["configuration"]
            )
            db.add(src)
            db.flush()
            print(f"  ✓ Created Source: {src.source_name} (ID: {src.id})")
        else:
            src.is_active = True
            src.health_status = "HEALTHY"
            src.configuration = item["configuration"]
            src.canonical_source_url = item["canonical_source_url"]
            db.flush()
            print(f"  ✓ Updated Source: {src.source_name} (ID: {src.id})")

        db.commit()

        # Trigger sync
        print(f"  Executing ingestion sync for {src.source_name} (ID: {src.id})...")
        try:
            run = IngestionRunner.execute_sync(db=db, source_id=src.id)
            print(f"  ✓ Sync result: Status={run.status}, Discovered={run.records_discovered}, Inserted={run.records_inserted}, Unchanged={run.records_unchanged}, Error={run.error_message}")
            synced.append((c_name, item["ats_provider"], run.status, run.records_discovered, run.records_inserted))
        except Exception as e:
            print(f"  ✗ Sync error: {e}")
            synced.append((c_name, item["ats_provider"], "FAILED", 0, 0))

    print("\n" + "=" * 65)
    print("EXTENDED ATS SOURCES SYNC COMPLETE")
    print("=" * 65)
    for c_name, ats, status, disc, ins in synced:
        print(f"  [{status:<7}] {c_name:<24} | {ats:<15} | Discovered: {disc:<4} | Inserted: {ins:<4}")

    total_jobs = db.query(Job).filter(Job.status == "ACTIVE").count()
    print(f"\nTotal Active Jobs in Database: {total_jobs}")
    db.close()

if __name__ == "__main__":
    main()
