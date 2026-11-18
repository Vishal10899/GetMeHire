from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from app.schemas.job import JobListResponseItem

class JobVisitRecordResponse(BaseModel):
    job_id: int
    redirect_url: str
    visited_at: datetime
    last_visited_at: datetime
    visit_count: int
    disclaimer: str = "Visiting an employer application page does not mean an application was submitted."

class VisitedJobItem(BaseModel):
    id: int
    user_id: int
    job_id: int
    visited_at: datetime
    last_visited_at: datetime
    visit_count: int
    job: JobListResponseItem

class VisitedJobsListResponse(BaseModel):
    items: List[VisitedJobItem]
    total_unique_visited: int
    total_clicks: int
    disclaimer: str = "Visiting an employer application page does not mean an application was submitted."
