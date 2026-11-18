import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal, engine
from app.core.config import settings
from sqlalchemy import text, create_engine

def main():
    print("=" * 80)
    print("GETMEHIRE — DATABASE RECORD COUNT RECONCILIATION")
    print("=" * 80)

    db = SessionLocal()

    try:
        # Master Database counts
        total_master = db.execute(text("SELECT count(*) FROM jobs;")).scalar()
        active_master = db.execute(text("SELECT count(*) FROM jobs WHERE status IN ('ACTIVE', 'POSSIBLY_STALE');")).scalar()
        strictly_active = db.execute(text("SELECT count(*) FROM jobs WHERE status = 'ACTIVE';")).scalar()
        stale_master = db.execute(text("SELECT count(*) FROM jobs WHERE status = 'POSSIBLY_STALE';")).scalar()
        inactive_master = db.execute(text("SELECT count(*) FROM jobs WHERE status NOT IN ('ACTIVE', 'POSSIBLY_STALE');")).scalar()
        classified_master = db.execute(text("SELECT count(*) FROM jobs WHERE early_career_category IS NOT NULL;")).scalar()
        unclassified_master = db.execute(text("SELECT count(*) FROM jobs WHERE early_career_category IS NULL;")).scalar()

        print("\n1. MASTER DATABASE (job_discovery_master):")
        print(f"   Total Records       : {total_master}")
        print(f"   - Active (Total)    : {active_master} (Strict Active: {strictly_active}, Stale: {stale_master})")
        print(f"   - Inactive Records  : {inactive_master}")
        print(f"   - Classified Records: {classified_master}")
        print(f"   - Unclassified      : {unclassified_master}")

        # Check breakdown by status
        status_rows = db.execute(text("SELECT status, count(*) FROM jobs GROUP BY status ORDER BY count(*) DESC;")).fetchall()
        print("\n   Status Breakdown:")
        for st, cnt in status_rows:
            print(f"     {st.ljust(20)}: {cnt}")

        # Test Database counts
        test_url = f"postgresql+psycopg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/job_discovery_test"
        test_eng = create_engine(test_url)
        with test_eng.connect() as t_conn:
            total_test = t_conn.execute(text("SELECT count(*) FROM jobs;")).scalar()
            active_test = t_conn.execute(text("SELECT count(*) FROM jobs WHERE status = 'ACTIVE';")).scalar()
            classified_test = t_conn.execute(text("SELECT count(*) FROM jobs WHERE early_career_category IS NOT NULL;")).scalar()
        print("\n2. TEST DATABASE (job_discovery_test):")
        print(f"   Total Records       : {total_test}")
        print(f"   Active Records      : {active_test}")
        print(f"   Classified Records  : {classified_test}")

        # Ingestion runs inspect
        print("\n3. RECENT INGESTION RUNS IN MASTER:")
        runs = db.execute(text("""
            SELECT ir.id, s.source_name, ir.status, ir.records_discovered, ir.records_inserted, ir.records_updated, ir.start_time, ir.end_time
            FROM ingestion_runs ir
            JOIN sources s ON s.id = ir.source_id
            ORDER BY ir.id DESC
            LIMIT 15;
        """)).fetchall()
        for r in runs:
            print(f"   Run #{r[0]}: {r[1]} | status={r[2]} | discovered={r[3]}, inserted={r[4]}, updated={r[5]} | start={r[6]}")

        # Analyze difference between 21,937 and 22,141
        # Check jobs inserted between the crawler run and the backfill run
        diff_jobs = db.execute(text("""
            SELECT id, title, company_id, source_id, created_at, first_seen_at
            FROM jobs
            ORDER BY id DESC
            LIMIT 210;
        """)).fetchall()
        print(f"\n4. MOST RECENTLY INSERTED JOBS IN MASTER (IDs {diff_jobs[-1][0]} to {diff_jobs[0][0]}):")
        print(f"   Total count inspected: {len(diff_jobs)}")
        print(f"   Earliest in batch: ID {diff_jobs[-1][0]} created at {diff_jobs[-1][4]}")
        print(f"   Latest in batch  : ID {diff_jobs[0][0]} created at {diff_jobs[0][4]}")

        # Check duplicate fingerprints or duplicate external_job_id
        dups = db.execute(text("""
            SELECT external_job_id, source_id, count(*)
            FROM jobs
            GROUP BY external_job_id, source_id
            HAVING count(*) > 1;
        """)).fetchall()
        print(f"\n5. DUPLICATE REQUISITIONS (same external_job_id + source_id): {len(dups)}")

    finally:
        db.close()

if __name__ == "__main__":
    main()
