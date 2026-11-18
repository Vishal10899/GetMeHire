from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from app.schemas.job import JobListResponseItem

class SavedJobCreate(BaseModel):
    notes: Optional[str] = None

class SavedJobItem(BaseModel):
    id: int
    user_id: int
    job_id: int
    notes: Optional[str] = None
    created_at: datetime
    job: JobListResponseItem

    model_config = ConfigDict(from_attributes=True)

class SavedJobsListResponse(BaseModel):
    items: list[SavedJobItem]
    total: int
