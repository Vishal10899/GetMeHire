import datetime
import hashlib
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from fastapi import HTTPException
from app.models import Alert, AlertDelivery, Job, User
from app.schemas.alert import AlertCreate, AlertUpdate, AlertResponse, AlertDeliveryItem

class AlertService:
    @staticmethod
    def create_alert(db: Session, user: User, alert_in: AlertCreate) -> Alert:
        criteria_dict = alert_in.criteria.model_dump()
        alert = Alert(
            user_id=user.id,
            title=alert_in.title,
            criteria=criteria_dict,
            frequency=alert_in.frequency.upper(),
            is_active=True
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert

    @staticmethod
    def get_user_alerts(db: Session, user: User) -> List[AlertResponse]:
        alerts = db.query(Alert).filter(Alert.user_id == user.id).order_by(desc(Alert.created_at)).all()
        result = []
        for a in alerts:
            deliv_count = db.query(AlertDelivery).filter(AlertDelivery.alert_id == a.id).count()
            resp = AlertResponse(
                id=a.id,
                user_id=a.user_id,
                title=a.title,
                criteria=a.criteria,
                frequency=a.frequency,
                is_active=a.is_active,
                last_evaluated_at=a.last_evaluated_at,
                created_at=a.created_at,
                deliveries_count=deliv_count
            )
            result.append(resp)
        return result

    @staticmethod
    def update_alert(db: Session, user: User, alert_id: int, alert_in: AlertUpdate) -> AlertResponse:
        alert = db.query(Alert).filter(Alert.id == alert_id, Alert.user_id == user.id).first()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        if alert_in.title is not None:
            alert.title = alert_in.title
        if alert_in.criteria is not None:
            alert.criteria = alert_in.criteria.model_dump()
        if alert_in.frequency is not None:
            alert.frequency = alert_in.frequency.upper()
        if alert_in.is_active is not None:
            alert.is_active = alert_in.is_active

        alert.updated_at = datetime.datetime.now(datetime.timezone.utc)
        db.commit()
        db.refresh(alert)
        
        deliv_count = db.query(AlertDelivery).filter(AlertDelivery.alert_id == alert.id).count()
        return AlertResponse(
            id=alert.id,
            user_id=alert.user_id,
            title=alert.title,
            criteria=alert.criteria,
            frequency=alert.frequency,
            is_active=alert.is_active,
            last_evaluated_at=alert.last_evaluated_at,
            created_at=alert.created_at,
            deliveries_count=deliv_count
        )

    @staticmethod
    def delete_alert(db: Session, user: User, alert_id: int) -> bool:
        alert = db.query(Alert).filter(Alert.id == alert_id, Alert.user_id == user.id).first()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        db.delete(alert)
        db.commit()
        return True

    @classmethod
    def evaluate_alert_for_new_jobs(cls, db: Session, alert_id: int, user: Optional[User] = None) -> int:
        query = db.query(Alert).filter(
            Alert.id == alert_id,
            Alert.is_active == True
        )
        if user is not None:
            query = query.filter(Alert.user_id == user.id)

        alert = query.first()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found or unauthorized")

        criteria = alert.criteria or {}
        query = db.query(Job).filter(Job.status.in_(["ACTIVE", "POSSIBLY_STALE"]))

        if criteria.get("keywords"):
            kw = f"%{criteria['keywords']}%"
            query = query.filter(or_(Job.title.ilike(kw), Job.description.ilike(kw)))

        if criteria.get("country"):
            query = query.filter(Job.country.ilike(f"%{criteria['country']}%"))

        if criteria.get("city"):
            query = query.filter(Job.city.ilike(f"%{criteria['city']}%"))

        if criteria.get("remote_only"):
            query = query.filter(Job.remote_type == "REMOTE")

        if criteria.get("min_salary"):
            query = query.filter(Job.salary_max >= criteria["min_salary"])

        matching_jobs = query.order_by(desc(Job.created_at)).limit(20).all()

        delivered_count = 0
        for job in matching_jobs:
            dedup_raw = f"{alert.id}:{job.id}:{job.content_fingerprint[:8]}"
            dedup_key = hashlib.sha256(dedup_raw.encode("utf-8")).hexdigest()

            # Check if notification already delivered
            existing_delivery = db.query(AlertDelivery).filter(
                AlertDelivery.deduplication_key == dedup_key
            ).first()

            if not existing_delivery:
                delivery = AlertDelivery(
                    alert_id=alert.id,
                    job_id=job.id,
                    user_id=alert.user_id,
                    deduplication_key=dedup_key,
                    status="SENT",
                    attempts=1,
                    provider_message_id=f"sim-email-{dedup_key[:10]}",
                    sent_at=datetime.datetime.now(datetime.timezone.utc)
                )
                db.add(delivery)
                delivered_count += 1

        alert.last_evaluated_at = datetime.datetime.now(datetime.timezone.utc)
        db.commit()
        return delivered_count
