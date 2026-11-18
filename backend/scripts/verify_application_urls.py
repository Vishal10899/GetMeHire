"""
Audited Application URL Verification Script.

Inspects original employer application URLs across active jobs in PostgreSQL.
Categorizes links into VALID, REDIRECTED, TEMPORARILY_UNAVAILABLE, CONFIRMED_BROKEN.
Never fabricates replacement URLs and never marks temporary failures as closed.
"""

import os
import sys
import time
import argparse
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models import Job, Source, Company
from app.services.url_verifier import UrlVerifierService


def main():
    parser = argparse.ArgumentParser(description="Verify original employer application URLs")
    parser.add_argument("--sample-per-source", type=int, default=5, help="Number of jobs to sample per source")
    parser.add_argument("--max-total", type=int, default=150, help="Maximum total URLs to check in this audit")
    parser.add_argument("--commit-verified-at", action="store_true", help="Update Job.last_verified_at timestamp in database")
    args = parser.parse_args()

    db = SessionLocal()
    print("=" * 70)
    print("GLOBALJOBS — ORIGINAL EMPLOYER APPLICATION URL AUDIT")
    print("=" * 70)

    sources = db.query(Source).filter(Source.is_active == True).all()
    print(f"Active sources in platform: {len(sources)}")

    sampled_jobs = []
    for src in sources:
        jobs = (
            db.query(Job)
            .filter(Job.source_id == src.id, Job.status == "ACTIVE")
            .order_by(Job.id.desc())
            .limit(args.sample_per_source)
            .all()
        )
        sampled_jobs.extend(jobs)
        if len(sampled_jobs) >= args.max_total:
            sampled_jobs = sampled_jobs[:args.max_total]
            break

    print(f"Total representative jobs sampled across sources: {len(sampled_jobs)}")
    print("-" * 70)

    stats = {
        "VALID": 0,
        "REDIRECTED": 0,
        "TEMPORARILY_UNAVAILABLE": 0,
        "CONFIRMED_BROKEN": 0,
        "INVALID_URL": 0,
    }

    now = datetime.now(timezone.utc)
    verified_ids = []

    for idx, job in enumerate(sampled_jobs, 1):
        url = job.application_url
        res = UrlVerifierService.verify_single_url(url, timeout=5.0)
        status = res["status"]
        stats[status] = stats.get(status, 0) + 1

        company_name = job.company.canonical_name if job.company else "Unknown"
        http_code = res.get("http_status") or "N/A"
        latency = res.get("latency_ms", 0)

        marker = "✓" if status in ("VALID", "REDIRECTED") else ("?" if status == "TEMPORARILY_UNAVAILABLE" else "✗")
        print(f"[{idx}/{len(sampled_jobs)}] {marker} [{status}] HTTP {http_code} ({latency}ms) — {company_name}: {job.title[:35]}")
        print(f"     URL: {url}")

        if status in ("VALID", "REDIRECTED") and args.commit_verified_at:
            job.last_verified_at = now
            verified_ids.append(job.id)

        # Gentle throttle to respect source rate limits
        time.sleep(0.15)

    if verified_ids and args.commit_verified_at:
        db.commit()
        print(f"\nUpdated last_verified_at timestamp for {len(verified_ids)} verified jobs.")

    print("\n" + "=" * 70)
    print("URL VERIFICATION AUDIT SUMMARY")
    print("=" * 70)
    total_checked = len(sampled_jobs)
    for st, count in stats.items():
        pct = (count / total_checked * 100) if total_checked else 0
        print(f"  {st:25}: {count:4d} ({pct:5.1f}%)")

    functional_links = stats["VALID"] + stats["REDIRECTED"]
    functional_pct = (functional_links / total_checked * 100) if total_checked else 0
    print("-" * 70)
    print(f"  TOTAL ACCESSIBLE (Valid + Redirected): {functional_links}/{total_checked} ({functional_pct:.1f}%)")
    print(f"  TEMPORARILY UNAVAILABLE (Rate limit / timeout): {stats['TEMPORARILY_UNAVAILABLE']}")
    print(f"  CONFIRMED BROKEN (404/410): {stats['CONFIRMED_BROKEN']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
