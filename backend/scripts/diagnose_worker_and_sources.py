"""
Diagnostic script for inspecting the background job ingestion worker, source registry,
scheduling logic, next scheduled synchronization times, advisory locks, and recent runs.
"""

import os
import sys
import datetime
from sqlalchemy import text, func

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models import Source, IngestionRun, Job, Company
from app.ingestion.scheduler import IngestionScheduler


def main():
    print("=" * 80)
    print("GETMEHIRE INGESTION SCHEDULER & WORKER DIAGNOSTIC")
    print("=" * 80)

    db = SessionLocal()
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    print(f"Current System Time (UTC): {now_utc.isoformat()}")

    try:
        # 1. Total Registered Sources
        total_sources = db.query(Source).count()
        print(f"\n1. SOURCE REGISTRY OVERVIEW")
        print(f"   Total Registered Sources: {total_sources}")

        # Active / Inactive breakdown
        active_count = db.query(Source).filter(Source.is_active == True).count()
        inactive_count = db.query(Source).filter(Source.is_active == False).count()
        print(f"   • Enabled / Active (is_active=True): {active_count}")
        print(f"   • Disabled (is_active=False): {inactive_count}")

        # Health status breakdown
        health_breakdown = db.query(Source.health_status, func.count(Source.id)).group_by(Source.health_status).all()
        print("   • Health Status Breakdown:")
        for h_status, count in health_breakdown:
            print(f"     - {h_status}: {count}")

        # 2. Inspect IngestionScheduler Logic & Due Sources
        due_sources = IngestionScheduler.get_due_sources(db, now=now_utc)
        print(f"\n2. DUE SOURCE EVALUATION")
        print(f"   IngestionScheduler found {len(due_sources)} due source(s) at current time.")

        if due_sources:
            print("   Due Source Details:")
            for s in due_sources:
                interval_secs = IngestionScheduler.parse_cron_interval_seconds(s.sync_schedule_cron)
                elapsed = (now_utc - s.last_attempted_at.replace(tzinfo=datetime.timezone.utc)).total_seconds() if s.last_attempted_at else None
                print(f"     • Source #{s.id} ('{s.source_name}') | Type: {s.source_type} | Health: {s.health_status}")
                print(f"       - Cron: '{s.sync_schedule_cron}' (Interval: {interval_secs}s / {interval_secs/3600:.1f}h)")
                print(f"       - Last Attempted At: {s.last_attempted_at} (Elapsed: {f'{elapsed:.1f}s' if elapsed else 'NEVER'})")
                print(f"       - Last Successful At: {s.last_successful_sync_at}")

        # 3. Inspect All Sources Scheduling & Next Run Times
        print(f"\n3. DETAILED SOURCE SCHEDULE AUDIT (All {active_count} Active Sources)")
        active_sources = db.query(Source).filter(Source.is_active == True).order_by(Source.id).all()
        
        # Categorize active sources
        never_attempted = []
        overdue_sources = []
        future_scheduled = []
        quarantined = []

        for s in active_sources:
            if s.health_status == "QUARANTINED":
                quarantined.append(s)
                continue
                
            interval_secs = IngestionScheduler.parse_cron_interval_seconds(s.sync_schedule_cron)
            
            if not s.last_attempted_at:
                never_attempted.append(s)
            else:
                last_att = s.last_attempted_at
                if last_att.tzinfo is None:
                    last_att = last_att.replace(tzinfo=datetime.timezone.utc)
                elapsed = (now_utc - last_att).total_seconds()
                next_due = last_att + datetime.timedelta(seconds=interval_secs)
                remaining = (next_due - now_utc).total_seconds()

                if elapsed >= interval_secs:
                    overdue_sources.append((s, elapsed, interval_secs))
                else:
                    future_scheduled.append((s, remaining, interval_secs, next_due))

        print(f"   • Never Attempted: {len(never_attempted)}")
        print(f"   • Overdue / Due Now: {len(overdue_sources)}")
        print(f"   • Future Scheduled (Waiting for interval): {len(future_scheduled)}")
        print(f"   • Quarantined (Excluded from scheduling): {len(quarantined)}")

        if future_scheduled:
            # Sort by remaining time until next run
            future_scheduled.sort(key=lambda x: x[1])
            print("\n   Next 5 Sources Scheduled to Run:")
            for s, rem, interval, next_due in future_scheduled[:5]:
                print(f"     - Source #{s.id} ('{s.source_name}', {s.source_type}): in {rem/60:.1f} mins ({rem/3600:.2f} hrs) at {next_due.isoformat()} (Interval: {interval/3600:.1f}h)")

            # Show the furthest scheduled
            furthest_s, furthest_rem, furthest_interval, furthest_due = future_scheduled[-1]
            print(f"   Furthest Scheduled Source: Source #{furthest_s.id} in {furthest_rem/3600:.2f} hrs (Interval: {furthest_interval/3600:.1f}h)")

        # 4. Recent Ingestion Runs (Last 10)
        print(f"\n4. RECENT INGESTION RUNS (Last 10)")
        recent_runs = db.query(IngestionRun).order_by(IngestionRun.id.desc()).limit(10).all()
        for r in recent_runs:
            src = db.query(Source).filter(Source.id == r.source_id).first()
            src_name = src.source_name if src else f"Source #{r.source_id}"
            print(f"   • Run #{r.id} | Source #{r.source_id} ('{src_name}') | Status: {r.status} | Start: {r.start_time} | Discovered: {r.records_discovered}, Inserted: {r.records_inserted}, Updated: {r.records_updated}")
            if r.error_message:
                print(f"     Error: {r.error_message[:100]}")

        # 5. Advisory Locks Check
        print(f"\n5. POSTGRESQL ADVISORY LOCKS")
        locks = db.execute(text("SELECT pid, mode, granted, classid, objid FROM pg_locks WHERE locktype = 'advisory';")).fetchall()
        print(f"   Active Advisory Locks Count: {len(locks)}")
        for l in locks:
            print(f"   • PID: {l[0]}, Mode: {l[1]}, Granted: {l[2]}, classid: {l[3]}, objid: {l[4]}")

        # 6. Check Worker Health File
        health_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "storage", "worker_health.json"))
        print(f"\n6. WORKER HEALTH FILE: {health_file}")
        if os.path.exists(health_file):
            with open(health_file, "r") as f:
                print(f"   {f.read()}")
        else:
            print("   File does not exist.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
