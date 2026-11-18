from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models import User
from app.schemas.alert import AlertCreate, AlertUpdate, AlertResponse
from app.services.alert_service import AlertService

router = APIRouter()

@router.get("", response_model=List[AlertResponse])
def get_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return AlertService.get_user_alerts(db, current_user)

@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
def create_alert(
    alert_in: AlertCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    alert = AlertService.create_alert(db, current_user, alert_in)
    return AlertResponse(
        id=alert.id,
        user_id=alert.user_id,
        title=alert.title,
        criteria=alert.criteria,
        frequency=alert.frequency,
        is_active=alert.is_active,
        last_evaluated_at=alert.last_evaluated_at,
        created_at=alert.created_at,
        deliveries_count=0
    )

@router.patch("/{alert_id}", response_model=AlertResponse)
def update_alert(
    alert_id: int,
    alert_in: AlertUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return AlertService.update_alert(db, current_user, alert_id, alert_in)

@router.delete("/{alert_id}", status_code=status.HTTP_200_OK)
def delete_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    AlertService.delete_alert(db, current_user, alert_id)
    return {"message": "Alert deleted"}

@router.post("/{alert_id}/evaluate")
def evaluate_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    count = AlertService.evaluate_alert_for_new_jobs(db, alert_id=alert_id, user=current_user)
    return {"message": f"Alert evaluated against newly ingested jobs. {count} new matches delivered.", "delivered": count}
