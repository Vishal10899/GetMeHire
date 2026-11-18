"""
GlobalJobs — Idempotent Location & Country Normalization Backfill Script
Fixes country=NULL, backfills city, region, country, country_code, remote_type,
and refreshes search_vector with location tokens.

Preserves all original raw location strings in job.location.
"""
import sys
import os
import time
from typing import Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy.orm import joinedload
from sqlalchemy import func
from app.core.database import SessionLocal
from app.models import Job, Company
from app.ingestion.normalizer import normalize_location_full, get_country_code

def run_backfill(batch_size: int = 500):
    db = SessionLocal()
    start_time = time.time()
    
    print("=" * 70)
    print("GLOBALJOBS: LOCATION & COUNTRY NORMALIZATION BACKFILL")
    print("=" * 70)

    total_jobs = db.query(Job).count()
    null_country_before = db.query(Job).filter(Job.country.is_(None)).count()
    null_code_before = db.query(Job).filter(Job.country_code.is_(None)).count()
    print(f"Total jobs in database: {total_jobs}")
    print(f"Jobs with country = NULL before: {null_country_before}")
    print(f"Jobs with country_code = NULL before: {null_code_before}")

    processed = 0
    updated_countries = 0
    updated_codes = 0
    updated_cities = 0
    
    offset = 0
    while offset < total_jobs:
        jobs_batch = (
            db.query(Job)
            .options(joinedload(Job.company))
            .order_by(Job.id.asc())
            .offset(offset)
            .limit(batch_size)
            .all()
        )
        if not jobs_batch:
            break

        for job in jobs_batch:
            processed += 1
            company_name = job.company.canonical_name if job.company else ""
            
            clean_loc, city, region, country, country_code, detected_remote = normalize_location_full(
                raw_location=job.location,
                raw_title=job.title
            )

            changed = False
            
            if country and job.country != country:
                job.country = country
                updated_countries += 1
                changed = True

            if country_code and job.country_code != country_code:
                job.country_code = country_code
                updated_codes += 1
                changed = True
            elif not country_code and job.country:
                code = get_country_code(job.country)
                if code and job.country_code != code:
                    job.country_code = code
                    updated_codes += 1
                    changed = True

            if city and job.city != city:
                job.city = city
                updated_cities += 1
                changed = True

            if region and job.region != region:
                job.region = region
                changed = True

            # If job had generic onsite but title/location indicates remote/hybrid
            if detected_remote != "ONSITE" and job.remote_type == "ONSITE":
                job.remote_type = detected_remote
                changed = True

            # Refresh search vector with location and country tokens
            country_str = job.country or ""
            city_str = job.city or ""
            job.search_vector = func.to_tsvector(
                "english",
                f"{job.title} {company_name} {job.department or ''} {country_str} {city_str} {job.description[:2000]}"
            )

        db.commit()
        offset += len(jobs_batch)
        print(f"  Processed {processed}/{total_jobs} jobs...")

    # Post-backfill audit
    null_country_after = db.query(Job).filter(Job.country.is_(None)).count()
    null_code_after = db.query(Job).filter(Job.country_code.is_(None)).count()
    
    print("\n" + "=" * 70)
    print("BACKFILL AUDIT RESULTS")
    print("=" * 70)
    print(f"Total jobs processed: {processed}")
    print(f"Jobs with country = NULL: {null_country_before} -> {null_country_after} ({(null_country_before - null_country_after)} resolved)")
    print(f"Jobs with country_code populated: {total_jobs - null_code_after}/{total_jobs} ({round((total_jobs - null_code_after)/total_jobs*100, 1)}%)")
    
    # Country breakdown
    top_countries = (
        db.query(Job.country, Job.country_code, func.count(Job.id))
        .filter(Job.country.isnot(None))
        .group_by(Job.country, Job.country_code)
        .order_by(func.count(Job.id).desc())
        .limit(15)
        .all()
    )
    print("\nTop 15 Countries:")
    for c, code, count in top_countries:
        print(f"  - {c} ({code}): {count} jobs")

    # Workplace breakdown
    workplace_counts = (
        db.query(Job.remote_type, func.count(Job.id))
        .group_by(Job.remote_type)
        .all()
    )
    print("\nWorkplace Arrangement:")
    for r, count in workplace_counts:
        print(f"  - {r}: {count} jobs")

    elapsed = round(time.time() - start_time, 2)
    print(f"\nBackfill completed successfully in {elapsed}s.")
    db.close()

if __name__ == "__main__":
    run_backfill()
