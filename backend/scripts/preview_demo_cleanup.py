"""
GlobalJobs - Database Demo & Test Data Preview and Cleanup Tool

Safely identifies and previews synthetic demo seed jobs and automated test artifact
accounts in the database without performing unapproved destructive mutations.

Usage:
    python backend/scripts/preview_demo_cleanup.py --dry-run
    python backend/scripts/preview_demo_cleanup.py --execute --confirm-cleanup
"""
import sys
import os
import argparse
from typing import Dict, Any, List

# Ensure backend path is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models import Job, User, Profile, VisitedJob, SavedJob, IngestionRun, Source, Company
from sqlalchemy import or_

AUTHENTIC_USERS = {
    "admin@jobplatform.com",
    "candidate@example.com",
    "vishalchaudhary74096@gmail.com"
}

def analyze_database(db) -> Dict[str, Any]:
    # 1. Job inventory
    all_jobs = db.query(Job).all()
    seed_jobs = [
        j for j in all_jobs
        if (j.raw_source_data and isinstance(j.raw_source_data, dict) and j.raw_source_data.get("seed") is True)
        or j.id <= 7
    ]
    authentic_jobs = [j for j in all_jobs if j not in seed_jobs]

    # 2. User inventory
    all_users = db.query(User).all()
    test_users = [
        u for u in all_users
        if u.email not in AUTHENTIC_USERS
        and (
            u.email.startswith(("user_", "candidate_b_", "candidate_c_", "qa_candidate_", "e2e_candidate_", "playwright_candidate_", "api_candidate_"))
            or "@example.com" in u.email
            or "@testplatform.com" in u.email
            or "@e2etest.com" in u.email
            or u.email in ("test@test.com", "cand_real_123@test.com")
        )
    ]
    preserved_users = [u for u in all_users if u not in test_users]

    # 3. Associated telemetry on seed jobs
    seed_job_ids = [j.id for j in seed_jobs]
    visited_seed_count = db.query(VisitedJob).filter(VisitedJob.job_id.in_(seed_job_ids)).count() if seed_job_ids else 0
    saved_seed_count = db.query(SavedJob).filter(SavedJob.job_id.in_(seed_job_ids)).count() if seed_job_ids else 0

    return {
        "total_jobs": len(all_jobs),
        "seed_jobs": seed_jobs,
        "authentic_jobs_count": len(authentic_jobs),
        "total_users": len(all_users),
        "test_users": test_users,
        "preserved_users": preserved_users,
        "visited_seed_count": visited_seed_count,
        "saved_seed_count": saved_seed_count
    }

def print_preview(analysis: Dict[str, Any]):
    print("=" * 80)
    print(" GLOBALJOBS DATABASE INVENTORY & DEMO CLEANUP PREVIEW (DRY-RUN)")
    print("=" * 80)
    print(f"\n1. JOB INVENTORY:")
    print(f"   - Total Jobs in Database:        {analysis['total_jobs']}")
    print(f"   - Synthetic / Seed Demo Jobs:    {len(analysis['seed_jobs'])}")
    print(f"   - Authentic Employer Vacancies:  {analysis['authentic_jobs_count']}")

    print("\n   [Identified Synthetic Seed Jobs (IDs <= 7)]:")
    for j in analysis["seed_jobs"]:
        print(f"     * ID {j.id:2d}: {j.title:<50} | URL: {j.application_url}")

    print(f"\n2. USER INVENTORY:")
    print(f"   - Total Users in Database:       {analysis['total_users']}")
    print(f"   - Automated Test Run Accounts:   {len(analysis['test_users'])}")
    print(f"   - Protected Production Accounts: {len(analysis['preserved_users'])}")

    print("\n   [Protected Real / Production Accounts]:")
    for u in analysis["preserved_users"]:
        print(f"     * ID {u.id:2d}: {u.email:<45} | Role: {u.role}")

    print(f"\n3. ASSOCIATED TELEMETRY ON SEED JOBS:")
    print(f"   - Visited Job Events linked to seed jobs: {analysis['visited_seed_count']}")
    print(f"   - Saved Job Records linked to seed jobs:  {analysis['saved_seed_count']}")

    print("\n4. NON-DESTRUCTIVE CLEANUP PLAN (RECOMMENDED):")
    print("   Instead of irreversible hard deletes, execute safe status transitions:")
    print("   a) Transition seed jobs status to 'DEMO_ARCHIVED' or soft-filter in discovery.")
    print("   b) Retain test user records in test database, isolated from production.")
    print("   c) Retain all genuine candidate accounts and real employer records.")

    print("\n5. SQL ROLLBACK SCRIPT PREVIEW:")
    print("   -- Revert soft-archive of seed jobs:")
    print("   UPDATE jobs SET status = 'ACTIVE' WHERE id <= 7;")
    print("=" * 80)

def main():
    parser = argparse.ArgumentParser(description="Preview or safely clean demo data.")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Preview cleanup actions without mutating database.")
    parser.add_argument("--execute", action="store_true", help="Execute the cleanup (requires --confirm-cleanup).")
    parser.add_argument("--confirm-cleanup", action="store_true", help="Explicit confirmation for cleanup mutation.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        analysis = analyze_database(db)
        print_preview(analysis)

        if args.execute:
            if not args.confirm_cleanup:
                print("\n[ERROR] Execution aborted: must specify --confirm-cleanup along with --execute.")
                sys.exit(1)
            print("\n[MUTATION] Executing safe status transition for seed jobs...")
            for j in analysis["seed_jobs"]:
                j.status = "ARCHIVED_DEMO"
            db.commit()
            print("[SUCCESS] Seed jobs safely transitioned to ARCHIVED_DEMO status.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
