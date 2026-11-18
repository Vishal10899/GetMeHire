from typing import Tuple, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models import IngestionRun, Source, Job

class AnomalyDetector:
    @staticmethod
    def evaluate_run(
        db: Session,
        source: Source,
        discovered_count: int,
        rejected_count: int,
        inserted_count: int,
        updated_count: int,
        unchanged_count: int
    ) -> Tuple[bool, Dict[str, Any]]:
        anomaly_detected = False
        reasons = []

        total_processed = inserted_count + updated_count + unchanged_count + rejected_count

        # 1. High rejection rate check
        if total_processed > 0:
            rejection_rate = rejected_count / total_processed
            if rejection_rate > 0.25 and rejected_count >= 3:
                anomaly_detected = True
                reasons.append(f"High parsing rejection rate: {rejection_rate:.1%} of records rejected ({rejected_count}/{total_processed})")

        # 2. Historical comparison: check previous successful complete run
        last_complete_run = db.query(IngestionRun).filter(
            IngestionRun.source_id == source.id,
            IngestionRun.status == "SUCCESS"
        ).order_by(IngestionRun.end_time.desc()).first()

        if last_complete_run and last_complete_run.records_discovered > 10:
            prev_count = last_complete_run.records_discovered
            if discovered_count < (prev_count * 0.4):  # Drop greater than 60%
                anomaly_detected = True
                reasons.append(f"Sudden sharp drop in discovered job listings: from {prev_count} to {discovered_count} (-{((prev_count - discovered_count) / prev_count):.1%})")

        details = {
            "anomaly_detected": anomaly_detected,
            "reasons": reasons,
            "discovered": discovered_count,
            "rejected": rejected_count,
            "processed": total_processed
        }

        return anomaly_detected, details
