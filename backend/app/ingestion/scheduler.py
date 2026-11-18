import datetime
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models import Source, IngestionRun
from app.ingestion.runner import IngestionRunner

class IngestionScheduler:
    """
    Automated Background Ingestion Scheduler (PRD §5.4 & §10.2).
    Determines synchronization eligibility based on source cron schedules,
    executes due ingestion runs, and performs stale-job lifecycle transitions.
    """

    @staticmethod
    def parse_cron_interval_seconds(cron_str: str) -> int:
        """
        Extracts interval in seconds from common cron schedule formats.
        Defaults to 4 hours (14400s) if parsing cannot determine a shorter interval.
        """
        if not cron_str:
            return 14400

        cron_str = cron_str.strip()
        parts = cron_str.split()
        if len(parts) == 5:
            minute_field, hour_field = parts[0], parts[1]
            if minute_field.startswith("*/"):
                try:
                    mins = int(minute_field[2:])
                    return max(60, mins * 60)
                except ValueError:
                    pass
            if hour_field.startswith("*/"):
                try:
                    hours = int(hour_field[2:])
                    return max(60, hours * 3600)
                except ValueError:
                    pass
            if hour_field.isdigit() and minute_field.isdigit():
                return 86400

        return 14400  # Default 4 hours

    @classmethod
    def is_source_due(cls, source: Source, now: Optional[datetime.datetime] = None) -> bool:
        if not source.is_active:
            return False
        if source.health_status in ["QUARANTINED"]:
            return False

        if now is None:
            now = datetime.datetime.now(datetime.timezone.utc)

        # If never attempted, it is immediately due
        if not source.last_attempted_at:
            return True

        interval_seconds = cls.parse_cron_interval_seconds(source.sync_schedule_cron)
        last_attempt = source.last_attempted_at
        if last_attempt.tzinfo is None:
            last_attempt = last_attempt.replace(tzinfo=datetime.timezone.utc)

        elapsed = (now - last_attempt).total_seconds()
        return elapsed >= interval_seconds

    @classmethod
    def get_due_sources(cls, db: Session, now: Optional[datetime.datetime] = None, limit: Optional[int] = None) -> List[Source]:
        active_sources = db.query(Source).filter(
            Source.is_active == True,
            Source.health_status != "QUARANTINED"
        ).order_by(Source.last_attempted_at.asc().nullsfirst()).all()
        due = [s for s in active_sources if cls.is_source_due(s, now)]
        if limit is not None:
            return due[:limit]
        return due

    @classmethod
    def run_due_sources(cls, db: Session, max_sources: int = 10, now: Optional[datetime.datetime] = None) -> Dict[str, Any]:
        due_sources = cls.get_due_sources(db, now)[:max_sources]
        results = []

        for source in due_sources:
            try:
                run = IngestionRunner.execute_sync(db, source.id)
                results.append({
                    "source_id": source.id,
                    "source_name": source.source_name,
                    "status": run.status,
                    "records_discovered": run.records_discovered,
                    "records_inserted": run.records_inserted,
                    "records_updated": run.records_updated,
                    "error": run.error_message
                })
            except Exception as exc:
                results.append({
                    "source_id": source.id,
                    "source_name": source.source_name,
                    "status": "FAILED",
                    "error": str(exc)
                })

        # Run maintenance: expire stale jobs older than 14 days
        expired_count = IngestionRunner.expire_stale_jobs(db, grace_days=14)

        return {
            "sources_evaluated": len(due_sources),
            "runs": results,
            "stale_jobs_expired": expired_count,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
