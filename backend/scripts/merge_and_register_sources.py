"""
Merge discovered active career boards and register/update them in PostgreSQL database.
Covers:
- Healthcare & Biotech (Maven Clinic, Oscar Health, Headway, Ginkgo Bioworks)
- Fintech & Banking (Wise, Robinhood, Coinbase, Brex, Affirm, Chime, Gusto, Carta, Ripple, Ramp)
- Retail, Food & Hospitality (Toast, Sweetgreen, Glossier, Instacart, Coupang, Delivery Hero, Faire)
- Automotive, Aerospace & Defense (Lucid Motors, Redwood Materials, Anduril Industries, Relativity Space)
- Gaming & Media (Roblox, Epic Games, Reddit, Discord, Spotify)
- Education (Coursera, Duolingo, Khan Academy, Udemy)
- AI & Search (OpenAI, Perplexity AI, Palantir Technologies)
- Enterprise & HR (Braze, Klaviyo, Checkr)
"""

import os
import sys
import json
import datetime
from sqlalchemy import func

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models import Company, Source

def main():
    db = SessionLocal()
    
    # 1. Load discovered boards
    with open("backend/discovered_candidate_sources.json", "r") as f:
        r1 = json.load(f)
    with open("backend/discovered_candidate_sources_round2.json", "r") as f:
        r2 = json.load(f)
        
    all_discovered = r1 + r2
    print(f"Total Discovered Boards: {len(all_discovered)}")
    
    # Deduplicate by (ats, slug)
    seen = set()
    unique_discovered = []
    for d in all_discovered:
        key = (d["ats"], d["slug"].lower())
        if key not in seen:
            seen.add(key)
            unique_discovered.append(d)
            
    print(f"Unique Verified Boards: {len(unique_discovered)}")
    
    updated_sources = 0
    created_sources = 0
    created_companies = 0
    
    for item in unique_discovered:
        ats = item["ats"]
        slug = item["slug"]
        name = item["name"]
        industry = item["industry"]
        country = item["country"]
        raw_url = item["url"]
        
        # Build canonical source URL
        if ats == "GREENHOUSE":
            url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
            cfg = {"board_token": slug}
        elif ats == "LEVER":
            url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
            cfg = {"company_slug": slug}
        elif ats == "ASHBY":
            url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
            cfg = {"job_board_name": slug}
        elif ats == "SMARTRECRUITERS":
            url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
            cfg = {"company_slug": slug}
        else:
            url = raw_url
            cfg = {}

        # 1. Resolve Company
        company = db.query(Company).filter(
            func.lower(Company.canonical_name) == func.lower(name)
        ).first()
        
        if not company:
            company = Company(
                canonical_name=name,
                industry=industry,
                country=country,
                identity_status="VERIFIED",
                verification_status="ACTIVE_JOB_SOURCE",
                ats_provider=ats,
                ats_board_id=slug,
                discovery_source="CROSS_INDUSTRY_VERIFIED_DISCOVERY"
            )
            db.add(company)
            db.flush()
            created_companies += 1
            print(f"[NEW COMPANY] Created: {name} ({industry}, {country})")
        else:
            # Update industry / country if missing
            if not company.industry:
                company.industry = industry
            if not company.country:
                company.country = country
            if not company.ats_provider:
                company.ats_provider = ats
            if not company.ats_board_id:
                company.ats_board_id = slug

        # 2. Resolve Source
        source = db.query(Source).filter(
            Source.company_id == company.id,
            Source.source_type == ats
        ).first()
        
        # Also check by canonical_source_url
        if not source:
            source = db.query(Source).filter(
                Source.canonical_source_url == url
            ).first()

        if source:
            # Update existing source URL and configuration
            source.canonical_source_url = url
            source.external_board_id = slug
            source.configuration = cfg
            source.is_active = True
            source.health_status = "HEALTHY"
            source.sync_schedule_cron = "0 */4 * * *"
            updated_sources += 1
            print(f"[UPDATED SOURCE] #{source.id} for {name} ({ats}): URL={url}")
        else:
            # Create new source
            source = Source(
                company_id=company.id,
                source_name=f"{name} {ats.title()} Board",
                source_type=ats,
                canonical_source_url=url,
                external_board_id=slug,
                access_classification="PUBLIC_API",
                sync_schedule_cron="0 */4 * * *",
                rate_limit_rpm=60,
                concurrency_limit=1,
                is_active=True,
                health_status="HEALTHY",
                configuration=cfg,
                error_history=[]
            )
            db.add(source)
            created_sources += 1
            print(f"[NEW SOURCE] Created source for {name} ({ats}): URL={url}")

    db.commit()
    print("\n" + "=" * 60)
    print(f"REGISTRATION COMPLETE:")
    print(f"  • Companies Created: {created_companies}")
    print(f"  • Sources Created: {created_sources}")
    print(f"  • Sources Updated: {updated_sources}")
    print("=" * 60)
    db.close()

if __name__ == "__main__":
    main()
