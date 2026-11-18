import os
import sys
import datetime
from collections import Counter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models import Source, Job, IngestionRun, Company
from sqlalchemy import text

def main():
    print("=" * 80)
    print("GETMEHIRE — SOURCE HEALTH AUDIT & REVERSIBLE CLEANUP")
    print("=" * 80)

    db = SessionLocal()

    try:
        sources = db.query(Source).order_by(Source.id.asc()).all()
        total_sources = len(sources)
        print(f"Total Configured Sources in Registry: {total_sources}")

        health_counts = Counter(s.health_status for s in sources)
        active_counts = Counter(s.is_active for s in sources)
        type_counts = Counter(s.source_type for s in sources)

        print("\nInitial Source Breakdown:")
        print(f"  Active: {active_counts.get(True, 0)} | Disabled: {active_counts.get(False, 0)}")
        print("  By Health Status:")
        for hs, cnt in health_counts.most_common():
            print(f"    - {hs.ljust(15)}: {cnt}")
        print("  By Adapter Type:")
        for st, cnt in type_counts.most_common():
            print(f"    - {st.ljust(18)}: {cnt}")

        # Inspect failing sources
        failing_sources = [s for s in sources if s.health_status in ("FAILING", "DEGRADED")]
        print(f"\nTotal Sources with Errors: {len(failing_sources)}")

        speculative_404_count = 0
        preserved_with_jobs_count = 0
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        deactivated_ids = []

        for s in failing_sources:
            # Check how many jobs this source has
            job_count = db.query(Job).filter(Job.source_id == s.id).count()
            err_hist = s.error_history or []
            last_err = err_hist[-1] if err_hist else "No recorded error details"
            
            # Check if it's a 404 board not found
            is_404 = "404" in str(last_err) or "not found" in str(last_err).lower()

            if is_404 and job_count == 0:
                speculative_404_count += 1
                # Reversibly deactivate with persistent reason
                cfg = dict(s.configuration or {})
                cfg["deactivation_reason"] = f"Persistent HTTP 404 (Career board not found); verified speculative slug. Reversible via admin reactivation."
                cfg["deactivated_at"] = now_iso
                cfg["previous_health_status"] = s.health_status
                s.configuration = cfg
                s.is_active = False
                s.health_status = "QUARANTINED"
                deactivated_ids.append(s.id)
            else:
                preserved_with_jobs_count += 1
                # Mark as DEGRADED with scheduled backoff rather than hard failing
                s.health_status = "DEGRADED"

        db.commit()

        print("\nCleanup Actions Applied:")
        print(f"  • Speculative 404 sources reversibly quarantined: {speculative_404_count}")
        print(f"  • Failing sources preserved (have jobs or transient): {preserved_with_jobs_count}")

        # Post-cleanup tally
        updated_sources = db.query(Source).all()
        post_health = Counter(s.health_status for s in updated_sources)
        post_active = Counter(s.is_active for s in updated_sources)

        print("\nPost-Cleanup Status:")
        print(f"  Active Sources: {post_active.get(True, 0)}")
        print(f"  Quarantined / Inactive Sources: {post_active.get(False, 0)}")
        for hs, cnt in post_health.most_common():
            print(f"    - {hs.ljust(15)}: {cnt}")

    finally:
        db.close()

if __name__ == "__main__":
    main()
