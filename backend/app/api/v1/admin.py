import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_admin_user
from app.models import User, Company
from app.schemas.admin import (
    SourceCreate, SourceUpdate, SourceResponse,
    IngestionRunResponse, HealthCheckResponse,
    GlobalSearchQualityDashboardResponse,
    BoardProbeRequest, BoardProbeResponse,
    BoardDiscoverRequest, BoardDiscoverResponse,
    SchedulerRunResponse, DiscoverySummaryResponse,
    CompanyStatusUpdateRequest, DiscoveryRunRequest
)
from app.schemas.job import CompanyItem, CompanyListResponse
from app.services.admin_service import AdminService
from app.services.company_discovery import CompanyDiscoveryService
from app.services.job_service import JobService
from app.discovery.worker import CompanyDiscoveryService as GlobalDiscoveryService
from app.ingestion.scheduler import IngestionScheduler
from app.ingestion.runner import IngestionRunner

router = APIRouter()

@router.get("/sources", response_model=List[SourceResponse])
def list_sources(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    return AdminService.get_sources(db)

@router.post("/sources", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
def create_source(
    source_in: SourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    return AdminService.create_source(db, current_user, source_in)

@router.post("/sources/probe", response_model=BoardProbeResponse)
def probe_ats_board(
    probe_in: BoardProbeRequest,
    current_user: User = Depends(get_current_admin_user)
):
    return CompanyDiscoveryService.probe_ats_board(probe_in.query)

@router.post("/sources/discover", response_model=BoardDiscoverResponse, status_code=status.HTTP_201_CREATED)
def discover_and_register_source(
    discover_in: BoardDiscoverRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    return CompanyDiscoveryService.discover_and_register_source(
        db=db,
        actor=current_user,
        company_name=discover_in.company_name,
        query_or_url=discover_in.query,
        website=discover_in.website,
        sync_now=discover_in.sync_now
    )

@router.post("/scheduler/run", response_model=SchedulerRunResponse)
def run_due_sources(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    return IngestionScheduler.run_due_sources(db, max_sources=limit)

@router.post("/jobs/expire-stale")
def expire_stale_jobs(
    grace_days: int = Query(14, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    expired = IngestionRunner.expire_stale_jobs(db, grace_days=grace_days)
    return {"message": f"Successfully transitioned {expired} stale listings to CLOSED status.", "expired_count": expired}

@router.patch("/sources/{source_id}", response_model=SourceResponse)
def update_source(
    source_id: int,
    source_in: SourceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    return AdminService.update_source(db, current_user, source_id, source_in)

@router.post("/sources/{source_id}/sync", response_model=IngestionRunResponse)
def trigger_sync(
    source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    return AdminService.trigger_source_sync(db, current_user, source_id)

@router.get("/ingestion-runs", response_model=List[IngestionRunResponse])
def list_ingestion_runs(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    return AdminService.get_ingestion_runs(db, limit)

@router.get("/health", response_model=HealthCheckResponse)
def get_system_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    return AdminService.get_system_health(db)

@router.get("/quality-dashboard", response_model=GlobalSearchQualityDashboardResponse)
def get_quality_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Returns authoritative product-level search quality metrics (Master Specification §10):
    Global active jobs, employers, active sources, distributions across countries, cities,
    industries, professions, employment types, work arrangements, remote eligibilities,
    as well as zero-indexed sources, failing sources, and stale/closed counts.
    """
    return AdminService.get_quality_dashboard(db)

@router.get("/discovery/summary", response_model=DiscoverySummaryResponse)
def get_discovery_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Returns telemetry across all 7 verification tiers, country & industry distributions.
    """
    return GlobalDiscoveryService.get_discovery_telemetry(db)

@router.get("/discovery/companies", response_model=CompanyListResponse)
def list_discovery_companies(
    query: Optional[str] = Query(None, description="Search company name or domain"),
    tier: Optional[str] = Query(None, description="Filter by verification tier"),
    country: Optional[str] = Query(None, description="Filter by country"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Paginated company discovery management list for admin audit.
    """
    return JobService.get_companies_summary(
        db=db,
        query=query,
        industry=industry,
        country=country,
        verification_status=tier,
        page=page,
        page_size=page_size
    )

@router.post("/discovery/run")
def run_discovery_pipeline(
    req: DiscoveryRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Triggers automated discovery batch across public connectors.
    """
    result = GlobalDiscoveryService.run_discovery_pipeline(
        db=db,
        limit_per_source=req.limit_per_source,
        verify_online=req.verify_online,
        max_to_verify=req.max_to_verify,
        target_country=req.target_country,
        target_industry=req.target_industry
    )
    return {"message": "Discovery pipeline execution completed.", "result": result}

@router.patch("/discovery/companies/{company_id}/status", response_model=CompanyItem)
def update_company_verification_status(
    company_id: int,
    status_update: CompanyStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Admin action to inspect, approve, adjust tier, or reject questionable company records.
    """
    valid_tiers = [
        "DISCOVERED", "DOMAIN_VERIFIED", "CAREER_PAGE_FOUND",
        "SOURCE_VERIFIED", "ACTIVE_JOB_SOURCE", "NO_CURRENT_VACANCIES", "UNSUPPORTED"
    ]
    tier_upper = status_update.verification_status.strip().upper()
    if tier_upper not in valid_tiers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid verification tier '{status_update.verification_status}'. Must be one of {valid_tiers}"
        )

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    company.verification_status = tier_upper
    company.last_verified_at = datetime.datetime.now(datetime.timezone.utc)
    if status_update.verification_notes:
        company.verification_notes = status_update.verification_notes

    db.commit()
    db.refresh(company)

    return JobService.get_companies_summary(db=db, query=company.canonical_name, page=1, page_size=1).items[0]

@router.get("/early-career-metrics")
def get_early_career_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Returns comprehensive metrics on Early Career & Fresher job classification,
    breakdowns by canonical category, and counts of fresher-friendly vs mislabelled postings.
    """
    from app.models import Job
    from sqlalchemy import func

    total_active_jobs = db.query(Job).filter(Job.status.in_(["ACTIVE", "POSSIBLY_STALE"])).count()
    
    category_counts = dict(
        db.query(Job.early_career_category, func.count(Job.id))
        .filter(Job.status.in_(["ACTIVE", "POSSIBLY_STALE"]))
        .group_by(Job.early_career_category)
        .all()
    )

    fresher_friendly_categories = [
        "TRUE_FRESHER", "GRADUATE", "ENTRY_LEVEL", "EARLY_CAREER",
        "JUNIOR", "TRAINEE", "INTERNSHIP", "APPRENTICESHIP", "EXPERIENCE_FLEXIBLE"
    ]
    fresher_friendly_total = sum(category_counts.get(c, 0) for c in fresher_friendly_categories)
    mislabelled_total = category_counts.get("MISLABELLED_ENTRY_LEVEL", 0)

    return {
        "total_active_jobs": total_active_jobs,
        "fresher_friendly_total": fresher_friendly_total,
        "fresher_friendly_percentage": round((fresher_friendly_total / max(total_active_jobs, 1)) * 100, 2),
        "mislabelled_entry_level_total": mislabelled_total,
        "categories_breakdown": category_counts
    }

