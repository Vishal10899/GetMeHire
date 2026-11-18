from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models import User
from app.schemas.saved_job import SavedJobCreate, SavedJobItem, SavedJobsListResponse
from app.schemas.job import JobListResponseItem
from app.services.job_service import JobService

router = APIRouter()

@router.get("", response_model=SavedJobsListResponse)
def get_saved_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    saved_list = JobService.get_saved_jobs(db, current_user)
    items = []
    for s in saved_list:
        job = s.job
        job_item = JobListResponseItem(
            id=job.id,
            title=job.title,
            department=job.department,
            profession=job.profession,
            location=job.location,
            city=job.city,
            region=job.region,
            country=job.country,
            remote_type=job.remote_type,
            employment_type=job.employment_type,
            experience_level=job.experience_level,
            min_experience_years=job.min_experience_years,
            skills=job.skills or [],
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            salary_currency=job.salary_currency,
            salary_period=job.salary_period,
            posting_date=job.posting_date,
            status=job.status,
            application_url=job.application_url,
            company_id=job.company_id,
            company_name=job.company.canonical_name if job.company else "Unknown",
            company_logo=job.company.logo_url if job.company else None,
            source_name=job.source.source_name if job.source else "Direct",
            first_seen_at=job.first_seen_at,
            last_verified_at=job.last_verified_at,
            is_saved=True
        )
        items.append(SavedJobItem(
            id=s.id,
            user_id=s.user_id,
            job_id=s.job_id,
            notes=s.notes,
            created_at=s.created_at,
            job=job_item
        ))
    return SavedJobsListResponse(items=items, total=len(items))

@router.put("/{job_id}", status_code=status.HTTP_200_OK)
def save_job(
    job_id: int,
    body: SavedJobCreate = SavedJobCreate(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    JobService.save_job(db, current_user, job_id, notes=body.notes)
    return {"message": "Job successfully saved", "job_id": job_id}

@router.delete("/{job_id}", status_code=status.HTTP_200_OK)
def unsave_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    JobService.unsave_job(db, current_user, job_id)
    return {"message": "Job removed from saved items", "job_id": job_id}
