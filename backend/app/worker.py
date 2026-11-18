"""
GetMeHire Standalone Background Ingestion Scheduler Worker.

Runs independently of the FastAPI web server to execute scheduled job synchronizations
and stale-job lifecycle transitions. Employs PostgreSQL advisory locking (key: 884920)
to guarantee strictly one worker executes synchronization at any given time across
multiple replicas or cluster nodes.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import time
import argparse
import signal
import datetime
import json
from pathlib import Path
from sqlalchemy import text
from app.core.config import settings
from app.core.database import SessionLocal
from app.ingestion.scheduler import IngestionScheduler
from app.ingestion.runner import IngestionRunner

ADVISORY_LOCK_KEY = 884920
HEALTH_STATUS_FILE = Path(__file__).resolve().parent.parent / "storage" / "worker_health.json"

class StandaloneWorker:
    def __init__(self, interval_seconds: int = 300, max_sources_per_tick: int = 10):
        self.interval = interval_seconds
        self.max_sources = max_sources_per_tick
        self._running = True

        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        print(f"\n[WORKER] Received shutdown signal ({signum}). Finishing current task and exiting...", flush=True)
        self._running = False

    def execute_tick(self) -> dict:
        """
        Executes a single scheduler tick with PostgreSQL advisory locking.
        Returns execution summary dict with 'locked', 'due_count', 'executed_count'.
        """
        result = {
            "lock_acquired": False,
            "due_count": 0,
            "executed_count": 0,
            "expired_stale_count": 0,
            "details": []
        }

        with SessionLocal() as db:
            # 1. Attempt non-blocking PostgreSQL session advisory lock
            lock_acquired = db.execute(
                text(f"SELECT pg_try_advisory_lock({ADVISORY_LOCK_KEY})")
            ).scalar()

            if not lock_acquired:
                print(f"[WORKER] Advisory lock ({ADVISORY_LOCK_KEY}) is currently held by another worker. Skipping tick.", flush=True)
                return result

            result["lock_acquired"] = True
            print(f"[WORKER] Advisory lock ({ADVISORY_LOCK_KEY}) acquired. Evaluating due sources...", flush=True)

            try:
                # 2. Check due sources
                due_sources = IngestionScheduler.get_due_sources(db, limit=self.max_sources)
                result["due_count"] = len(due_sources)

                if due_sources:
                    print(f"[WORKER] Found {len(due_sources)} source(s) due for synchronization.", flush=True)
                    summary = IngestionScheduler.run_due_sources(db, max_sources=self.max_sources)
                    runs = summary.get("runs", [])
                    result["executed_count"] = len(runs)
                    result["details"] = runs
                    for r in runs:
                        print(f"  • Source #{r.get('source_id')} ({r.get('source_name')}): {r.get('status')} (Discovered: {r.get('records_discovered')}, Inserted: {r.get('records_inserted')}, Updated: {r.get('records_updated')})", flush=True)
                else:
                    print("[WORKER] No sources currently due for synchronization.", flush=True)

                # 3. Expire stale jobs past grace period
                stale_expired = IngestionRunner.expire_stale_jobs(db, grace_days=14)
                result["expired_stale_count"] = stale_expired
                if stale_expired > 0:
                    print(f"[WORKER] Transitioned {stale_expired} stale job(s) past grace period to CLOSED.", flush=True)

            finally:
                # 4. Strictly release advisory lock
                db.execute(text(f"SELECT pg_advisory_unlock({ADVISORY_LOCK_KEY})"))
                print(f"[WORKER] Advisory lock ({ADVISORY_LOCK_KEY}) released cleanly.", flush=True)

            # 5. Record operational heartbeat and status
            try:
                HEALTH_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
                with open(HEALTH_STATUS_FILE, "w", encoding="utf-8") as f:
                    json.dump({
                        "last_tick_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        "status": "HEALTHY",
                        "due_count": result["due_count"],
                        "executed_count": result["executed_count"],
                        "expired_stale_count": result["expired_stale_count"],
                        "advisory_lock_key": ADVISORY_LOCK_KEY
                    }, f, indent=2)
            except Exception:
                pass

        return result

    def run_loop(self):
        print("==================================================================", flush=True)
        print(f"  GetMeHire Standalone Ingestion Worker Initialized", flush=True)
        print(f"  • Polling Interval: {self.interval} seconds", flush=True)
        print(f"  • Max Sources Per Tick: {self.max_sources}", flush=True)
        print(f"  • Advisory Lock ID: {ADVISORY_LOCK_KEY}", flush=True)
        print("==================================================================", flush=True)

        # Run immediately on boot
        self.execute_tick()

        while self._running:
            for _ in range(self.interval):
                if not self._running:
                    break
                time.sleep(1)

            if self._running:
                self.execute_tick()

        print("[WORKER] Standalone worker loop terminated cleanly.", flush=True)


def main():
    parser = argparse.ArgumentParser(description="GetMeHire Standalone Ingestion Scheduler Worker")
    parser.add_argument("--single-run", action="store_true", help="Execute a single tick and exit immediately (useful for cron/CI)")
    parser.add_argument("--interval", type=int, default=settings.SCHEDULER_INTERVAL_SECONDS, help="Worker loop interval in seconds (default: 300)")
    parser.add_argument("--max-sources", type=int, default=10, help="Maximum number of sources to synchronize per tick (default: 10)")
    args = parser.parse_args()

    worker = StandaloneWorker(interval_seconds=args.interval, max_sources_per_tick=args.max_sources)
    if args.single_run:
        print("[WORKER] Executing single-run tick...", flush=True)
        res = worker.execute_tick()
        print(f"[WORKER] Single-run completed. Summary: Lock={res['lock_acquired']}, Due={res['due_count']}, Executed={res['executed_count']}", flush=True)
    else:
        worker.run_loop()


if __name__ == "__main__":
    main()
