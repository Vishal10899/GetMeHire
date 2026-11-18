from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


class JobActivityItem(BaseModel):
    id: int
    activity_type: str  # VIEW, APPLY_CLICK
    job_id: int
    job_title: Optional[str] = None
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    company_logo: Optional[str] = None
    location: Optional[str] = None
    remote_type: Optional[str] = None
    employment_type: Optional[str] = None
    job_status: str = "ACTIVE"
    status: Optional[str] = "ACTIVE"
    application_url: Optional[str] = None
    redirect_result: Optional[str] = None  # SUCCESS, CLOSED_JOB, INVALID_URL, INACCESSIBLE
    source_platform: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobActivitySummaryResponse(BaseModel):
    total_views: int
    total_apply_clicks: int
    unique_companies_explored: int
    saved_jobs_count: int
    recent_views: List[JobActivityItem] = Field(default_factory=list)
    recent_apply_clicks: List[JobActivityItem] = Field(default_factory=list)
    disclaimer: str = (
        "Visiting an employer application page or viewing a job listing does not confirm an application "
        "was submitted. GetMeHire tracks candidate navigation for telemetry and personal job hunting history."
    )


class JobActivityTimelineResponse(BaseModel):
    items: List[JobActivityItem] = Field(default_factory=list)
    total: int
    total_count: Optional[int] = None
    page: int
    page_size: int
    total_views: int
    total_apply_clicks: int
    unique_companies: int
    disclaimer: str = (
        "Visiting an employer application page does not confirm that an application was submitted to the employer."
    )


class JobApplicationResponse(BaseModel):
    job_id: int
    application_url: str
    company_name: str
    job_title: str
    status: str
    redirect_result: str  # SUCCESS, CLOSED_JOB, INVALID_URL, INACCESSIBLE
    link_status: str  # VERIFIED_ACCESSIBLE, UNVERIFIED, CLOSED, UNAVAILABLE
    is_safe: bool = True
    disclaimer: str = (
        "Directing to the official employer career portal. GetMeHire maintains provenance and never submits "
        "applications on your behalf."
    )


class JobViewRecordResponse(BaseModel):
    job_id: int
    activity_type: str = "VIEW"
    recorded_at: datetime
    message: str = "Job view activity recorded successfully."
