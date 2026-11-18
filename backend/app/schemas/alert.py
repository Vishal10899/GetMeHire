from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from app.schemas.job import JobListResponseItem

class AlertCriteria(BaseModel):
    keywords: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    remote_only: Optional[bool] = False
    skills: List[str] = Field(default_factory=list)
    min_salary: Optional[float] = None
    employment_type: Optional[str] = None

class AlertCreate(BaseModel):
    title: str
    criteria: AlertCriteria
    frequency: str = "DAILY"  # IMMEDIATE, DAILY, WEEKLY

class AlertUpdate(BaseModel):
    title: Optional[str] = None
    criteria: Optional[AlertCriteria] = None
    frequency: Optional[str] = None
    is_active: Optional[bool] = None

class AlertDeliveryItem(BaseModel):
    id: int
    job_id: int
    deduplication_key: str
    status: str
    sent_at: datetime
    job_title: Optional[str] = None
    company_name: Optional[str] = None

class AlertResponse(BaseModel):
    id: int
    user_id: int
    title: str
    criteria: Dict[str, Any]
    frequency: str
    is_active: bool
    last_evaluated_at: Optional[datetime] = None
    created_at: datetime
    deliveries_count: int = 0

    model_config = ConfigDict(from_attributes=True)
