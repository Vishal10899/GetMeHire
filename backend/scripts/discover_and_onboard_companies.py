import os
import sys
import time
import httpx
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath("backend"))

from app.core.database import SessionLocal
from app.models import Company, Source, IngestionRun, Job
from app.ingestion.runner import IngestionRunner

# Master Registry across 20 Global Categories and Supported ATS Providers
VERIFIED_DISCOVERY_REGISTRY = [
    # 1. Software & IT
    {
        "canonical_name": "Postman",
        "website": "https://www.postman.com",
        "career_page_url": "https://www.postman.com/careers",
        "industry": "Software & IT",
        "country": "United States",
        "operating_region": "North America & India",
        "ats_provider": "BAMBOOHR",
        "ats_board_id": "postman",
        "canonical_source_url": "https://postman.bamboohr.com/careers/list",
        "discovery_source": "Official Career Page",
        "configuration": {"company_slug": "postman", "max_pages": 50}
    },
    {
        "canonical_name": "GitLab",
        "website": "https://about.gitlab.com",
        "career_page_url": "https://about.gitlab.com/jobs",
        "industry": "Software & IT",
        "country": "United States",
        "operating_region": "Global Remote",
        "ats_provider": "GREENHOUSE",
        "ats_board_id": "gitlab",
        "canonical_source_url": "https://boards.greenhouse.io/gitlab",
        "discovery_source": "Official Career Page",
        "configuration": {"board_token": "gitlab", "max_pages": 50}
    },
    {
        "canonical_name": "Cloudflare",
        "website": "https://www.cloudflare.com",
        "career_page_url": "https://www.cloudflare.com/careers",
        "industry": "Software & IT",
        "country": "United States",
        "operating_region": "Global",
        "ats_provider": "GREENHOUSE",
        "ats_board_id": "cloudflare",
        "canonical_source_url": "https://boards.greenhouse.io/cloudflare",
        "discovery_source": "Official Career Page",
        "configuration": {"board_token": "cloudflare", "max_pages": 50}
    },
    {
        "canonical_name": "Elastic",
        "website": "https://www.elastic.co",
        "career_page_url": "https://www.elastic.co/careers",
        "industry": "Software & IT",
        "country": "United States",
        "operating_region": "Global Remote",
        "ats_provider": "GREENHOUSE",
        "ats_board_id": "elastic",
        "canonical_source_url": "https://boards.greenhouse.io/elastic",
        "discovery_source": "Official Career Page",
        "configuration": {"board_token": "elastic", "max_pages": 50}
    },

    # 2. Data Science & AI
    {
        "canonical_name": "OpenAI",
        "website": "https://openai.com",
        "career_page_url": "https://openai.com/careers",
        "industry": "Data Science & AI",
        "country": "United States",
        "operating_region": "North America & Europe",
        "ats_provider": "ASHBY",
        "ats_board_id": "openai",
        "canonical_source_url": "https://jobs.ashbyhq.com/openai",
        "discovery_source": "Official Career Page",
        "configuration": {"board_name": "openai", "max_pages": 50}
    },

    # 3. Finance & Banking
    {
        "canonical_name": "Visa",
        "website": "https://www.visa.com",
        "career_page_url": "https://corporate.visa.com/en/careers.html",
        "industry": "Finance & Banking",
        "country": "United States",
        "operating_region": "Global",
        "ats_provider": "SMARTRECRUITERS",
        "ats_board_id": "visa",
        "canonical_source_url": "https://jobs.smartrecruiters.com/visa",
        "discovery_source": "Official Career Page",
        "configuration": {"company_slug": "visa", "page_size": 50, "max_pages": 50}
    },
    {
        "canonical_name": "Affirm",
        "website": "https://www.affirm.com",
        "career_page_url": "https://www.affirm.com/careers",
        "industry": "Finance & Banking",
        "country": "United States",
        "operating_region": "North America",
        "ats_provider": "GREENHOUSE",
        "ats_board_id": "affirm",
        "canonical_source_url": "https://boards.greenhouse.io/affirm",
        "discovery_source": "Official Career Page",
        "configuration": {"board_token": "affirm", "max_pages": 50}
    },
    {
        "canonical_name": "Clark",
        "website": "https://www.clark.de",
        "career_page_url": "https://www.clark.de/karriere",
        "industry": "Finance & Banking",
        "country": "Germany",
        "operating_region": "Europe",
        "ats_provider": "PERSONIO",
        "ats_board_id": "clark",
        "canonical_source_url": "https://clark.jobs.personio.de/xml?language=en",
        "discovery_source": "Official Career Page",
        "configuration": {"company_slug": "clark", "feed_domain": "de"}
    },

    # 4. Healthcare & Pharmaceuticals
    # (Komodo Health already registered; updating metadata)

    # 5. E-commerce & Retail
    {
        "canonical_name": "IKEA",
        "website": "https://www.ikea.com",
        "career_page_url": "https://www.ikea.com/careers",
        "industry": "E-commerce & Retail",
        "country": "Sweden",
        "operating_region": "Global",
        "ats_provider": "SMARTRECRUITERS",
        "ats_board_id": "ikea",
        "canonical_source_url": "https://jobs.smartrecruiters.com/ikea",
        "discovery_source": "Official Career Page",
        "configuration": {"company_slug": "ikea", "page_size": 50, "max_pages": 50}
    },
    {
        "canonical_name": "Snocks",
        "website": "https://snocks.com",
        "career_page_url": "https://snocks.com/pages/karriere",
        "industry": "E-commerce & Retail",
        "country": "Germany",
        "operating_region": "Europe",
        "ats_provider": "PERSONIO",
        "ats_board_id": "snocks",
        "canonical_source_url": "https://snocks.jobs.personio.de/xml?language=en",
        "discovery_source": "Official Career Page",
        "configuration": {"company_slug": "snocks", "feed_domain": "de"}
    },

    # 6. Manufacturing
    {
        "canonical_name": "Bosch",
        "website": "https://www.bosch.com",
        "career_page_url": "https://www.bosch.com/careers",
        "industry": "Manufacturing",
        "country": "Germany",
        "operating_region": "Global",
        "ats_provider": "SMARTRECRUITERS",
        "ats_board_id": "bosch",
        "canonical_source_url": "https://jobs.smartrecruiters.com/bosch",
        "discovery_source": "Official Career Page",
        "configuration": {"company_slug": "bosch", "page_size": 50, "max_pages": 50}
    },

    # 7. Automotive
    {
        "canonical_name": "Alstom",
        "website": "https://www.alstom.com",
        "career_page_url": "https://jobsearch.alstom.com",
        "industry": "Automotive",
        "country": "France",
        "operating_region": "Global",
        "ats_provider": "SMARTRECRUITERS",
        "ats_board_id": "alstom",
        "canonical_source_url": "https://jobs.smartrecruiters.com/alstom",
        "discovery_source": "Official Career Page",
        "configuration": {"company_slug": "alstom", "page_size": 50, "max_pages": 50}
    },

    # 8. Telecommunications
    {
        "canonical_name": "Twilio",
        "website": "https://www.twilio.com",
        "career_page_url": "https://www.twilio.com/company/jobs",
        "industry": "Telecommunications",
        "country": "United States",
        "operating_region": "Global",
        "ats_provider": "GREENHOUSE",
        "ats_board_id": "twilio",
        "canonical_source_url": "https://boards.greenhouse.io/twilio",
        "discovery_source": "Official Career Page",
        "configuration": {"board_token": "twilio", "max_pages": 50}
    },

    # 9. Consulting
    {
        "canonical_name": "Thoughtbot",
        "website": "https://thoughtbot.com",
        "career_page_url": "https://thoughtbot.com/jobs",
        "industry": "Consulting",
        "country": "United States",
        "operating_region": "Global Remote",
        "ats_provider": "BAMBOOHR",
        "ats_board_id": "thoughtbot",
        "canonical_source_url": "https://thoughtbot.bamboohr.com/careers/list",
        "discovery_source": "Official Career Page",
        "configuration": {"company_slug": "thoughtbot", "max_pages": 50}
    },

    # 10. Education
    # (Coursera and Duolingo already registered; updating metadata)

    # 11. Media & Entertainment
    {
        "canonical_name": "Ubisoft",
        "website": "https://www.ubisoft.com",
        "career_page_url": "https://jobs.ubisoft.com",
        "industry": "Media & Entertainment",
        "country": "France",
        "operating_region": "Global",
        "ats_provider": "SMARTRECRUITERS",
        "ats_board_id": "ubisoft",
        "canonical_source_url": "https://jobs.smartrecruiters.com/ubisoft",
        "discovery_source": "Official Career Page",
        "configuration": {"company_slug": "ubisoft", "page_size": 50, "max_pages": 50}
    },
    {
        "canonical_name": "Spotify",
        "website": "https://www.spotify.com",
        "career_page_url": "https://www.lifeatspotify.com",
        "industry": "Media & Entertainment",
        "country": "Sweden",
        "operating_region": "Global",
        "ats_provider": "LEVER",
        "ats_board_id": "spotify",
        "canonical_source_url": "https://jobs.lever.co/spotify",
        "discovery_source": "Official Career Page",
        "configuration": {"company_slug": "spotify", "max_pages": 50}
    },

    # 12. Hospitality
    # (Toast, Sweetgreen, Airbnb already registered; updating metadata)

    # 13. Logistics & Supply Chain
    {
        "canonical_name": "Flexport",
        "website": "https://www.flexport.com",
        "career_page_url": "https://www.flexport.com/careers",
        "industry": "Logistics & Supply Chain",
        "country": "United States",
        "operating_region": "Global",
        "ats_provider": "GREENHOUSE",
        "ats_board_id": "flexport",
        "canonical_source_url": "https://boards.greenhouse.io/flexport",
        "discovery_source": "Official Career Page",
        "configuration": {"board_token": "flexport", "max_pages": 50}
    },
    {
        "canonical_name": "Instacart",
        "website": "https://www.instacart.com",
        "career_page_url": "https://careers.instacart.com",
        "industry": "Logistics & Supply Chain",
        "country": "United States",
        "operating_region": "North America",
        "ats_provider": "GREENHOUSE",
        "ats_board_id": "instacart",
        "canonical_source_url": "https://boards.greenhouse.io/instacart",
        "discovery_source": "Official Career Page",
        "configuration": {"board_token": "instacart", "max_pages": 50}
    },

    # 14. Energy
    {
        "canonical_name": "Siemens",
        "website": "https://www.siemens.com",
        "career_page_url": "https://jobs.siemens.com",
        "industry": "Energy",
        "country": "Germany",
        "operating_region": "Global",
        "ats_provider": "SMARTRECRUITERS",
        "ats_board_id": "siemens",
        "canonical_source_url": "https://jobs.smartrecruiters.com/siemens",
        "discovery_source": "Official Career Page",
        "configuration": {"company_slug": "siemens", "page_size": 50, "max_pages": 50}
    },
    {
        "canonical_name": "Engie",
        "website": "https://www.engie.com",
        "career_page_url": "https://www.engie.com/en/candidates",
        "industry": "Energy",
        "country": "France",
        "operating_region": "Europe & Global",
        "ats_provider": "SMARTRECRUITERS",
        "ats_board_id": "engie",
        "canonical_source_url": "https://jobs.smartrecruiters.com/engie",
        "discovery_source": "Official Career Page",
        "configuration": {"company_slug": "engie", "page_size": 50, "max_pages": 50}
    },

    # 15. Government & Public Organizations
    # (CERN already registered; updating metadata)

    # 16. Marketing and Advertising
    {
        "canonical_name": "Wistia",
        "website": "https://wistia.com",
        "career_page_url": "https://wistia.com/jobs",
        "industry": "Marketing and Advertising",
        "country": "United States",
        "operating_region": "North America",
        "ats_provider": "BAMBOOHR",
        "ats_board_id": "wistia",
        "canonical_source_url": "https://wistia.bamboohr.com/careers/list",
        "discovery_source": "Official Career Page",
        "configuration": {"company_slug": "wistia", "max_pages": 50}
    },

    # 17. Legal and Professional Services
    {
        "canonical_name": "Everlaw",
        "website": "https://www.everlaw.com",
        "career_page_url": "https://www.everlaw.com/careers",
        "industry": "Legal and Professional Services",
        "country": "United States",
        "operating_region": "North America & Europe",
        "ats_provider": "GREENHOUSE",
        "ats_board_id": "everlaw",
        "canonical_source_url": "https://boards.greenhouse.io/everlaw",
        "discovery_source": "Official Career Page",
        "configuration": {"board_token": "everlaw", "max_pages": 50}
    },

    # 18. Construction and Infrastructure
    {
        "canonical_name": "Samsara",
        "website": "https://www.samsara.com",
        "career_page_url": "https://www.samsara.com/company/careers",
        "industry": "Construction and Infrastructure",
        "country": "United States",
        "operating_region": "Global",
        "ats_provider": "GREENHOUSE",
        "ats_board_id": "samsara",
        "canonical_source_url": "https://boards.greenhouse.io/samsara",
        "discovery_source": "Official Career Page",
        "configuration": {"board_token": "samsara", "max_pages": 50}
    },

    # 19. Aerospace
    {
        "canonical_name": "Planet Labs",
        "website": "https://www.planet.com",
        "career_page_url": "https://www.planet.com/careers",
        "industry": "Aerospace",
        "country": "United States",
        "operating_region": "North America & Europe",
        "ats_provider": "GREENHOUSE",
        "ats_board_id": "planetlabs",
        "canonical_source_url": "https://boards.greenhouse.io/planetlabs",
        "discovery_source": "Official Career Page",
        "configuration": {"board_token": "planetlabs", "max_pages": 50}
    },

    # 20. Biotechnology
    {
        "canonical_name": "Ginkgo Bioworks",
        "website": "https://www.ginkgobioworks.com",
        "career_page_url": "https://www.ginkgobioworks.com/careers",
        "industry": "Biotechnology",
        "country": "United States",
        "operating_region": "North America",
        "ats_provider": "GREENHOUSE",
        "ats_board_id": "ginkgobioworks",
        "canonical_source_url": "https://boards.greenhouse.io/ginkgobioworks",
        "discovery_source": "Official Career Page",
        "configuration": {"board_token": "ginkgobioworks", "max_pages": 50}
    },
]

# Existing company industry and geography mappings for backfill
EXISTING_COMPANY_METADATA = {
    "Stripe": ("Finance & Banking", "United States", "Global", "GREENHOUSE", "stripe"),
    "Airbnb": ("Hospitality", "United States", "Global", "GREENHOUSE", "airbnb"),
    "Anthropic": ("Data Science & AI", "United States", "North America & Europe", "GREENHOUSE", "anthropic"),
    "Datadog": ("Data Science & AI", "United States", "Global", "GREENHOUSE", "datadog"),
    "Scale AI": ("Data Science & AI", "United States", "North America", "GREENHOUSE", "scaleai"),
    "Palantir": ("Consulting", "United States", "Global", "LEVER", "palantir"),
    "Ramp": ("Finance & Banking", "United States", "North America", "ASHBY", "ramp"),
    "Sweetgreen": ("Hospitality", "United States", "North America", "GREENHOUSE", "sweetgreen"),
    "Coursera": ("Education", "United States", "Global", "GREENHOUSE", "coursera"),
    "Razorpay": ("Finance & Banking", "India", "Asia-Pacific", "GREENHOUSE", "razorpaysoftwareprivatelimited"),
    "CRED": ("Finance & Banking", "India", "Asia-Pacific", "LEVER", "cred"),
    "Groww": ("Finance & Banking", "India", "Asia-Pacific", "GREENHOUSE", "groww"),
    "InMobi": ("Marketing and Advertising", "India", "Global", "GREENHOUSE", "inmobi"),
    "Sarvam AI": ("Data Science & AI", "India", "Asia-Pacific", "ASHBY", "sarvam"),
    "CertifyOS": ("Legal and Professional Services", "United States", "North America", "ASHBY", "certifyos"),
    "Arondite": ("Software & IT", "United Kingdom", "Europe", "WORKABLE", "arondite"),
    "CERN": ("Government and public organizations", "Switzerland", "Europe", "SMARTRECRUITERS", "cern"),
    "Personio": ("Software & IT", "Germany", "Europe", "PERSONIO", "personio"),
    "Everphone": ("Telecommunications", "Germany", "Europe", "PERSONIO", "everphone"),
    "Remotive": ("Software & IT", "France", "Global Remote", "REMOTIVE", "remotive-global"),
    "Canonical": ("Software & IT", "United Kingdom", "Global Remote", "GREENHOUSE", "canonical"),
    "Bunq": ("Finance & Banking", "Netherlands", "Europe", "RECRUITEE", "bunq"),
    "Channable": ("E-commerce & Retail", "Netherlands", "Europe", "RECRUITEE", "channable"),
    "Linear": ("Software & IT", "United States", "Global Remote", "ASHBY", "linear"),
    "Mozilla": ("Software & IT", "United States", "Global Remote", "GREENHOUSE", "mozilla"),
    "On Running": ("E-commerce & Retail", "Switzerland", "Global", "GREENHOUSE", "onrunning"),
    "Duolingo": ("Education", "United States", "Global", "GREENHOUSE", "duolingo"),
    "Komodo Health": ("Healthcare & Pharmaceuticals", "United States", "North America", "GREENHOUSE", "komodohealth"),
    "Toast": ("Hospitality", "United States", "North America & Europe", "GREENHOUSE", "toast"),
    "Monzo": ("Finance & Banking", "United Kingdom", "Europe", "GREENHOUSE", "monzo"),
}

def run_discovery():
    db = SessionLocal()
    print("=" * 70)
    print("PHASE TWO: GLOBAL COMPANY DISCOVERY & ONBOARDING")
    print("=" * 70)

    # 1. Backfill metadata for existing companies
    print("\n[Step 1/3] Backfilling metadata for existing registered companies...")
    for comp_name, (ind, ctry, reg, ats, board) in EXISTING_COMPANY_METADATA.items():
        comp = db.query(Company).filter(Company.canonical_name == comp_name).first()
        if comp:
            comp.industry = ind
            comp.country = ctry
            comp.operating_region = reg
            comp.ats_provider = ats
            comp.ats_board_id = board
            comp.discovery_source = "Curated Employer Directory"
            comp.identity_status = "VERIFIED"
            print(f"  ✓ Updated metadata: {comp_name:<26} -> {ind:<32} ({ctry})")
    db.commit()

    # 2. Register newly discovered companies and sources
    print("\n[Step 2/3] Validating and registering newly discovered companies across 20 industries...")
    new_sources_to_sync = []

    client = httpx.Client(timeout=12.0, follow_redirects=True, headers={"User-Agent": "JobDiscoveryBot/2.0"})

    for rec in VERIFIED_DISCOVERY_REGISTRY:
        canonical_name = rec["canonical_name"]
        print(f"\n  Checking: {canonical_name} ({rec['industry']} | {rec['ats_provider']})...")

        # Validate ATS feed before onboarding
        probe_url = rec["canonical_source_url"]
        if rec["ats_provider"] == "GREENHOUSE":
            probe_url = f"https://boards-api.greenhouse.io/v1/boards/{rec['ats_board_id']}/jobs?content=true"
        elif rec["ats_provider"] == "SMARTRECRUITERS":
            probe_url = f"https://api.smartrecruiters.com/v1/companies/{rec['ats_board_id']}/postings?limit=5"
        elif rec["ats_provider"] == "ASHBY":
            probe_url = f"https://api.ashbyhq.com/posting-api/job-board/{rec['ats_board_id']}"
        elif rec["ats_provider"] == "BAMBOOHR":
            probe_url = f"https://{rec['ats_board_id']}.bamboohr.com/careers/list"
        elif rec["ats_provider"] == "PERSONIO":
            probe_url = rec["canonical_source_url"]
        elif rec["ats_provider"] == "LEVER":
            probe_url = f"https://api.lever.co/v0/postings/{rec['ats_board_id']}?mode=json"

        try:
            r = client.get(probe_url)
            if r.status_code != 200 or len(r.text) < 20:
                print(f"    ✗ Feed check failed with HTTP {r.status_code} ({probe_url})")
                continue
            print(f"    ✓ Feed validated (HTTP {r.status_code}, payload size: {len(r.text):,} bytes)")
        except Exception as e:
            print(f"    ✗ Error probing feed: {e}")
            continue

        # Create or update Company record
        comp = db.query(Company).filter(Company.canonical_name == canonical_name).first()
        if not comp:
            comp = Company(
                canonical_name=canonical_name,
                website=rec["website"],
                career_page_url=rec["career_page_url"],
                identity_status="VERIFIED",
                industry=rec["industry"],
                country=rec["country"],
                operating_region=rec["operating_region"],
                ats_provider=rec["ats_provider"],
                ats_board_id=rec["ats_board_id"],
                discovery_source=rec["discovery_source"]
            )
            db.add(comp)
            db.flush()
            print(f"    ✓ Created Company: {canonical_name} (ID: {comp.id})")
        else:
            comp.website = rec["website"]
            comp.career_page_url = rec["career_page_url"]
            comp.identity_status = "VERIFIED"
            comp.industry = rec["industry"]
            comp.country = rec["country"]
            comp.operating_region = rec["operating_region"]
            comp.ats_provider = rec["ats_provider"]
            comp.ats_board_id = rec["ats_board_id"]
            comp.discovery_source = rec["discovery_source"]
            db.flush()
            print(f"    ✓ Updated Company: {canonical_name} (ID: {comp.id})")

        # Create or update Source record
        source = db.query(Source).filter(
            Source.company_id == comp.id,
            Source.external_board_id == rec["ats_board_id"]
        ).first()

        if not source:
            source = Source(
                company_id=comp.id,
                source_name=f"{canonical_name} {rec['ats_provider'].capitalize()} Board",
                source_type=rec["ats_provider"],
                canonical_source_url=rec["canonical_source_url"],
                external_board_id=rec["ats_board_id"],
                access_classification="PUBLIC_API",
                sync_schedule_cron="0 */4 * * *",
                rate_limit_rpm=60,
                concurrency_limit=1,
                is_active=True,
                health_status="HEALTHY",
                configuration=rec["configuration"],
                config_version=1
            )
            db.add(source)
            db.flush()
            print(f"    ✓ Created Source: {source.source_name} (ID: {source.id})")
            new_sources_to_sync.append(source.id)
        else:
            source.is_active = True
            source.health_status = "HEALTHY"
            source.configuration = rec["configuration"]
            source.canonical_source_url = rec["canonical_source_url"]
            db.flush()
            print(f"    ✓ Existing Source active: {source.source_name} (ID: {source.id})")
            if not source.last_successful_sync_at:
                new_sources_to_sync.append(source.id)

    db.commit()
    print(f"\n[Step 2 Complete] {len(new_sources_to_sync)} new sources queued for initial deep crawl.")

    # 3. Synchronize On Running with updated Greenhouse parser
    on_running_src = db.query(Source).filter(Source.external_board_id == "onrunning").first()
    if on_running_src:
        print("\n[Step 3/3] Synchronizing On Running with updated unescaped HTML parser...")
        on_running_src.health_status = "HEALTHY"
        db.commit()
        try:
            run = IngestionRunner.execute_sync(db=db, source_id=on_running_src.id)
            print(f"  ✓ On Running sync complete: Status={run.status}, Discovered={run.records_discovered}, Inserted={run.records_inserted}, Updated={run.records_updated}")
        except Exception as e:
            print(f"  ✗ On Running sync error: {e}")

    # Synchronize newly onboarded sources
    for s_id in new_sources_to_sync:
        src = db.query(Source).filter(Source.id == s_id).first()
        if not src:
            continue
        print(f"\n  Executing initial deep crawl for: {src.source_name} (ID: {src.id})...")
        try:
            run = IngestionRunner.execute_sync(db=db, source_id=src.id)
            print(f"    ✓ Ingestion complete: Status={run.status}, Discovered={run.records_discovered}, Inserted={run.records_inserted}, Unchanged={run.records_unchanged}")
        except Exception as e:
            print(f"    ✗ Ingestion error: {e}")

    # Final summary
    total_comps = db.query(Company).count()
    verified_comps = db.query(Company).filter(Company.identity_status == "VERIFIED").count()
    total_sources = db.query(Source).count()
    active_sources = db.query(Source).filter(Source.is_active == True).count()
    total_jobs = db.query(Job).filter(Job.status == "ACTIVE").count()

    print("\n" + "=" * 70)
    print("GLOBAL COMPANY DISCOVERY & MULTI-LEVEL CRAWL SUMMARY")
    print("=" * 70)
    print(f"Total Companies in Registry: {total_comps} (Verified: {verified_comps})")
    print(f"Total Ingestion Sources:     {total_sources} (Active: {active_sources})")
    print(f"Total Active Jobs:           {total_jobs}")

    # Industries breakdown
    from sqlalchemy import func
    ind_counts = db.query(Company.industry, func.count(Company.id)).group_by(Company.industry).all()
    print("\nCompanies Breakdown by Industry:")
    for ind, c in sorted(ind_counts, key=lambda x: str(x[0])):
        print(f"  {str(ind or 'Uncategorized'):<35}: {c} companies")

    db.close()

if __name__ == "__main__":
    run_discovery()
