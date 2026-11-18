import os
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models import User
from app.schemas.profile import ProfileUpdate, ProfileResponse, ResumeUploadResponse
from app.schemas.resume import ProfileReviewApprovalRequest
from app.schemas.visited_job import VisitedJobsListResponse
from app.schemas.job_activity import JobActivitySummaryResponse, JobActivityTimelineResponse
from app.services.profile_service import ProfileService
from app.services.resume_storage import ResumeStorageService
from app.services.visited_job_service import VisitedJobService
from app.services.job_activity_service import JobActivityService

router = APIRouter()

@router.get("", response_model=ProfileResponse)
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = ProfileService.get_or_create_profile(db, current_user)
    return profile

@router.patch("", response_model=ProfileResponse)
def update_profile(
    profile_in: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ProfileService.update_profile(db, current_user, profile_in)

@router.post("/resume", response_model=ResumeUploadResponse)
def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile, download_url, extracted_data, existing_data, conflicts, raw_preview = ProfileService.upload_resume(db, current_user, file)
    return ResumeUploadResponse(
        message="Resume successfully uploaded and parsed",
        filename=profile.resume_filename or file.filename or "resume",
        profile_completion_pct=profile.profile_completion_pct,
        download_url=download_url,
        raw_text_preview=raw_preview,
        extracted_data=extracted_data,
        existing_data=existing_data,
        conflicts=conflicts
    )

@router.post("/resume/apply", response_model=ProfileResponse)
@router.post("/review-approve", response_model=ProfileResponse)
def apply_resume_extraction(
    approval_request: ProfileReviewApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Applies candidate-approved structured fields extracted from their resume into their profile.
    Prevents silent overwrites by allowing candidate review and confirmation.
    """
    return ProfileService.approve_extracted_profile(db, current_user, approval_request)

@router.delete("/resume", response_model=ProfileResponse)
def delete_resume(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ProfileService.delete_resume(db, current_user)

@router.get("/resume/download")
def download_resume(
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    user_id, filename = ResumeStorageService.verify_download_token(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.profile or not user.profile.resume_storage_path:
        raise HTTPException(status_code=404, detail="Resume file not found")

    path = user.profile.resume_storage_path
    return ResumeStorageService.get_download_response(path, filename)

@router.get("/visited-jobs", response_model=VisitedJobsListResponse)
def get_user_visited_jobs(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns the authenticated user's tracked visited jobs with deduplicated counts
    and application status disclaimers.
    """
    return VisitedJobService.get_user_visited_jobs(db, current_user, limit=limit, offset=offset)

@router.get("/activity/summary", response_model=JobActivitySummaryResponse)
def get_user_activity_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns candidate's aggregated job activity metrics:
    total jobs viewed, total apply now clicks, unique companies explored, saved jobs,
    and recent activity items.
    """
    return JobActivityService.get_user_activity_summary(db, current_user)

@router.get("/activity", response_model=JobActivityTimelineResponse)
def get_user_activity_timeline(
    activity_type: Optional[str] = Query(None, description="Filter by VIEW or APPLY_CLICK"),
    company: Optional[str] = Query(None, description="Filter by company name"),
    job_title: Optional[str] = Query(None, description="Filter by job title"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns candidate's chronologically ordered activity timeline with multi-faceted filters
    for date ranges, company, job title, and activity types.
    """
    return JobActivityService.get_user_activity_timeline(
        db=db,
        user=current_user,
        activity_type=activity_type,
        company=company,
        job_title=job_title,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )
