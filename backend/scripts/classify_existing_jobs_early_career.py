import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models import Job
from app.services.early_career_intelligence import EarlyCareerIntelligence
from sqlalchemy import func

def main():
    print("=" * 80)
    print("GETMEHIRE — EARLY CAREER INTELLIGENCE BATCH CLASSIFICATION & BACKFILL")
    print("=" * 80)

    db = SessionLocal()
    start_time = time.time()
    batch_size = 500

    try:
        total_jobs = db.query(Job).count()
        print(f"Total jobs in database to classify: {total_jobs}")

        category_counts = Counter()
        fresher_friendly_count = 0
        mislabelled_count = 0
        processed = 0

        # Process in batches ordered by ID
        last_id = 0
        while True:
            jobs = (
                db.query(Job)
                .filter(Job.id > last_id)
                .order_by(Job.id.asc())
                .limit(batch_size)
                .all()
            )
            if not jobs:
                break

            for job in jobs:
                cat, meta = EarlyCareerIntelligence.evaluate_job(
                    title=job.title,
                    description=job.description or "",
                    employment_type=job.employment_type,
                    source_min_years=job.min_experience_years
                )
                job.early_career_category = cat
                job.early_career_metadata = meta

                category_counts[cat] += 1
                if meta.get("is_fresher_friendly"):
                    fresher_friendly_count += 1
                if meta.get("is_mislabelled"):
                    mislabelled_count += 1

                last_id = job.id
                processed += 1

            db.commit()
            if processed % 2000 == 0 or processed == total_jobs:
                print(f"Progress: {processed}/{total_jobs} ({processed*100.0/total_jobs:.1f}%) processed...")

        elapsed = time.time() - start_time
        print("\n" + "=" * 80)
        print("CLASSIFICATION COMPLETE — SUMMARY REPORT")
        print("=" * 80)
        print(f"Total Jobs Classified: {processed}")
        print(f"Time Taken: {elapsed:.2f} seconds ({processed/max(elapsed, 0.001):.1f} jobs/sec)")
        print(f"Total Fresher-Friendly Jobs: {fresher_friendly_count} ({fresher_friendly_count*100.0/processed:.2f}%)")
        print(f"Total Mislabelled Entry-Level Postings: {mislabelled_count}")
        print("\nBreakdown by Canonical Category:")
        for cat, cnt in category_counts.most_common():
            print(f"  {cat.ljust(26)}: {cnt:6d} ({cnt*100.0/processed:5.2f}%)")
        print("=" * 80)

    finally:
        db.close()

if __name__ == "__main__":
    main()
