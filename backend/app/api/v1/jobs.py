from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user, get_optional_current_user
from app.models import User
from app.schemas.job import (
    JobSearchResponse,
    JobDetailResponse,
    SimilarJobResponse,
    ProfessionListResponse,
    CompanyListResponse,
)
from app.schemas.visited_job import JobVisitRecordResponse
from app.schemas.job_activity import JobApplicationResponse, JobViewRecordResponse
from app.services.job_service import JobService
from app.services.visited_job_service import VisitedJobService
from app.services.job_activity_service import JobActivityService

router = APIRouter()

@router.get("", response_model=JobSearchResponse)
def search_jobs(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
    keyword: Optional[str] = Query(None, description="Search keyword in title, description or company"),
    company: Optional[str] = Query(None, description="Filter by company name"),
    company_id: Optional[int] = Query(None, description="Filter by company ID"),
    profession: Optional[str] = Query(None, description="Filter by profession (e.g. ENGINEERING, SALES_BIZDEV, PRODUCT_DESIGN, DATA_AI, MARKETING_GROWTH, FINANCE_LEGAL, OPERATIONS_PEOPLE)"),
    category: Optional[str] = Query(None, description="Filter by job category or industry family"),
    location: Optional[str] = Query(None, description="Filter by location string"),
    country: Optional[str] = Query(None, description="Filter by country"),
    country_code: Optional[str] = Query(None, description="Filter by 2-letter ISO country code (e.g. US, IN, GB)"),
    city: Optional[str] = Query(None, description="Filter by city"),
    remote_type: Optional[str] = Query(None, description="REMOTE, HYBRID, or ONSITE"),
    work_arrangement: Optional[str] = Query(None, description="ONSITE, REMOTE, HYBRID, FIELD_BASED, FLEXIBLE, NOT_SPECIFIED"),
    remote_eligibility: Optional[str] = Query(None, description="WORLDWIDE, REGION_RESTRICTED, COUNTRY_RESTRICTED, TIMEZONE_RESTRICTED, EMPLOYER_DEFINED, NOT_REMOTE, UNSPECIFIED"),
    employment_type: Optional[str] = Query(None, description="FULL_TIME, PART_TIME, CONTRACT, INTERNSHIP, FREELANCE, etc."),
    experience_level: Optional[str] = Query(None, description="ENTRY, MID, SENIOR, LEAD, EXECUTIVE"),
    experience_range: Optional[str] = Query(None, description="internship, entry, 0-1, 1-3, 3-5, 5-8, 8+, unspecified"),
    early_career_category: Optional[str] = Query(None, description="TRUE_FRESHER, GRADUATE, ENTRY_LEVEL, EARLY_CAREER, JUNIOR, TRAINEE, INTERNSHIP, APPRENTICESHIP, etc."),
    is_fresher_friendly: Optional[bool] = Query(None, description="Filter for jobs verified suitable for freshers / zero experience"),
    max_experience_years: Optional[float] = Query(None, description="Maximum mandatory experience required in years"),
    graduation_year: Optional[int] = Query(None, description="Eligible graduation year / batch (e.g. 2024, 2025, 2026)"),
    skills: Optional[List[str]] = Query(None, description="Skills to match"),
    min_salary: Optional[float] = Query(None, description="Minimum salary"),
    max_salary: Optional[float] = Query(None, description="Maximum salary"),
    currency: Optional[str] = Query(None, description="Salary currency e.g. USD"),
    date_posted: Optional[str] = Query(None, description="Filter jobs posted within range (24h, 3d, 7d, 30d)"),
    status: Optional[str] = Query("ACTIVE", description="ACTIVE or other listing status"),
    sort_by: str = Query("newest", description="newest, relevant, oldest, company, salary_high"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    include_demo: bool = Query(False, description="Include demo/seed listings")
):
    return JobService.search_jobs(
        db=db,
        current_user=current_user,
        keyword=keyword,
        company=company,
        company_id=company_id,
        profession=profession,
        category=category,
        location=location,
        country=country,
        country_code=country_code,
        city=city,
        remote_type=remote_type,
        work_arrangement=work_arrangement,
        remote_eligibility=remote_eligibility,
        employment_type=employment_type,
        experience_level=experience_level,
        experience_range=experience_range,
        early_career_category=early_career_category,
        is_fresher_friendly=is_fresher_friendly,
        max_experience_years=max_experience_years,
        graduation_year=graduation_year,
        skills=skills,
        min_salary=min_salary,
        max_salary=max_salary,
        currency=currency,
        date_posted=date_posted,
        status_filter=status,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
        include_demo=include_demo
    )

@router.get("/companies", response_model=CompanyListResponse)
def get_companies(
    query: Optional[str] = Query(None, description="Filter company by canonical name"),
    industry: Optional[str] = Query(None, description="Filter company by industry"),
    country: Optional[str] = Query(None, description="Filter company by country/region"),
    ats_provider: Optional[str] = Query(None, description="Filter company by ATS provider"),
    verification_status: Optional[str] = Query(None, description="Filter company by verification status tier"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Returns verified company identities with active job counts, career page links,
    and associated sources without suppressing individual vacancy discovery.
    """
    return JobService.get_companies_summary(
        db=db,
        query=query,
        industry=industry,
        country=country,
        ats_provider=ats_provider,
        verification_status=verification_status,
        page=page,
        page_size=page_size
    )

@router.get("/professions", response_model=ProfessionListResponse)
def get_job_professions(
    db: Session = Depends(get_db)
):
    """
    Returns aggregated job counts and metadata across all multi-profession taxonomy tracks.
    """
    return JobService.get_profession_counts(db)

@router.get("/categories")
def get_job_categories(
    db: Session = Depends(get_db)
):
    """
    Returns aggregated job counts and metadata across industry categories.
    """
    return JobService.get_categories_summary(db)

@router.get("/{job_id}", response_model=JobDetailResponse)
def get_job_detail(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    detail = JobService.get_job_by_id(db, job_id, current_user)
    try:
        JobActivityService.record_view(db, job_id, current_user, request)
    except Exception:
        pass
    return detail

@router.get("/{job_id}/similar", response_model=SimilarJobResponse)
def get_similar_jobs(
    job_id: int,
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db)
):
    return JobService.get_similar_jobs(db, job_id, limit)

@router.post("/{job_id}/view", response_model=JobViewRecordResponse)
def record_job_view(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Explicitly records a job viewing activity event.
    """
    return JobActivityService.record_view(db, job_id, current_user, request)

@router.post("/{job_id}/apply", response_model=JobApplicationResponse)
def apply_to_job(
    job_id: int,
    request: Request,
    allow_closed: bool = Query(False, description="Whether to allow redirecting to a closed job posting"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Validates genuine stored employer application link, checks closed-job status,
    records an APPLY_CLICK telemetry event, and returns safe redirect destination.
    """
    return JobActivityService.record_apply_click(
        db=db,
        job_id=job_id,
        user=current_user,
        request=request,
        allow_closed=allow_closed
    )

@router.post("/{job_id}/visit", response_model=JobVisitRecordResponse)
def track_job_visit(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Records an authenticated visit to an official employer application page.
    Enforces deduplication, increments visit count, validates redirect destination,
    and returns verified redirect URL with disclaimer.
    """
    JobActivityService.record_apply_click(db, job_id, current_user, request, update_visited_job=False)
    return VisitedJobService.record_job_visit(db, current_user, job_id)

@router.get("/{job_id}/apply-redirect")
def apply_redirect(
    job_id: int,
    request: Request,
    allow_closed: bool = Query(False, description="Whether to allow redirecting to a closed job posting"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Direct application redirection endpoint.
    Records tracking event, validates against open redirects and closed jobs,
    and issues an HTTP 307 redirect to the official employer application page.
    """
    app_resp = JobActivityService.record_apply_click(
        db=db,
        job_id=job_id,
        user=current_user,
        request=request,
        allow_closed=allow_closed
    )
    return RedirectResponse(url=app_resp.application_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
