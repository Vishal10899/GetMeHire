from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class SourceCreate(BaseModel):
    company_name: str
    company_website: Optional[str] = None
    source_name: str
    source_type: str  # GREENHOUSE, LEVER, ASHBY, GENERIC_JSON, WEB_SCRAPER
    canonical_source_url: str
    external_board_id: Optional[str] = None
    access_classification: str = "PUBLIC_API"
    sync_schedule_cron: str = "0 */6 * * *"
    rate_limit_rpm: int = 60
    concurrency_limit: int = 1
    configuration: Dict[str, Any] = Field(default_factory=dict)

class SourceUpdate(BaseModel):
    source_name: Optional[str] = None
    is_active: Optional[bool] = None
    sync_schedule_cron: Optional[str] = None
    rate_limit_rpm: Optional[int] = None
    concurrency_limit: Optional[int] = None
    configuration: Optional[Dict[str, Any]] = None

class SourceResponse(BaseModel):
    id: int
    company_id: int
    company_name: str
    source_name: str
    source_type: str
    canonical_source_url: str
    external_board_id: Optional[str] = None
    access_classification: str
    sync_schedule_cron: str
    rate_limit_rpm: int
    concurrency_limit: int
    is_active: bool
    last_attempted_at: Optional[datetime] = None
    last_successful_sync_at: Optional[datetime] = None
    last_complete_sync_at: Optional[datetime] = None
    health_status: str
    total_jobs: int = 0
    active_jobs: int = 0
    created_at: datetime

    # Source-level diagnostics (Requirement 7)
    pagination_status: str = "FULLY_CRAWLED"
    has_continuation_cursor: bool = False
    last_failure_at: Optional[datetime] = None
    last_failure_message: Optional[str] = None
    jobs_discovered: int = 0
    jobs_accepted: int = 0
    jobs_rejected: int = 0

    model_config = ConfigDict(from_attributes=True)

class IngestionRunResponse(BaseModel):
    id: int
    source_id: int
    source_name: Optional[str] = None
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    records_discovered: int
    records_inserted: int
    records_updated: int
    records_unchanged: int
    records_rejected: int
    error_message: Optional[str] = None
    error_category: Optional[str] = None
    anomaly_detected: bool
    anomaly_details: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class HealthCheckResponse(BaseModel):
    status: str
    database_connected: bool
    total_sources: int
    active_sources: int
    healthy_sources: int
    failing_sources: int
    total_jobs: int
    active_jobs: int
    stale_jobs: int
    closed_jobs: int
    timestamp: datetime

class GlobalSearchQualityDashboardResponse(BaseModel):
    global_active_jobs: int
    active_employers: int
    active_job_sources: int
    country_distribution: List[Dict[str, Any]]
    city_distribution: List[Dict[str, Any]]
    industry_distribution: List[Dict[str, Any]]
    profession_distribution: List[Dict[str, Any]]
    employment_type_distribution: List[Dict[str, Any]]
    work_arrangement_distribution: List[Dict[str, Any]]
    remote_eligibility_distribution: List[Dict[str, Any]]
    zero_job_sources: List[Dict[str, Any]]
    failed_sources: List[Dict[str, Any]]
    partially_crawled_sources: List[Dict[str, Any]]
    stale_jobs_count: int
    closed_jobs_count: int
    timestamp: datetime

class BoardProbeRequest(BaseModel):
    query: str

class BoardProbeResponse(BaseModel):
    found: bool
    source_type: Optional[str] = None
    board_id: Optional[str] = None
    canonical_source_url: Optional[str] = None
    sample_jobs_count: int = 0
    details: Optional[str] = None

class BoardDiscoverRequest(BaseModel):
    company_name: str
    query: str
    website: Optional[str] = None
    sync_now: bool = True

class BoardDiscoverResponse(BaseModel):
    source_id: int
    company_name: str
    source_type: str
    canonical_source_url: str
    sample_jobs_count: int = 0
    initial_sync: Optional[Dict[str, Any]] = None

class SchedulerRunResponse(BaseModel):
    sources_evaluated: int
    runs: List[Dict[str, Any]]
    stale_jobs_expired: int
    timestamp: str

class DiscoverySummaryResponse(BaseModel):
    total_companies: int
    domain_verified_companies: int = 0
    career_pages_found: int = 0
    verified_ats_sources: int = 0
    active_job_sources: int = 0
    no_current_vacancies: int = 0
    unsupported_sources: int = 0
    partially_crawled_sources: int = 0
    pending_verification: int = 0
    active_jobs_count: int = 0
    jobs_rejected_count: int = 0
    tiers: Dict[str, int]
    countries: List[Dict[str, Any]]
    regions: List[Dict[str, Any]]
    industries: List[Dict[str, Any]]
    ats_providers: List[Dict[str, Any]]
    active_sources_count: int
    india_diagnostics: Optional[Dict[str, Any]] = None

class CompanyStatusUpdateRequest(BaseModel):
    verification_status: str
    verification_notes: Optional[str] = None

class DiscoveryRunRequest(BaseModel):
    limit_per_source: int = 500
    verify_online: bool = True
    max_to_verify: int = 200
    target_country: Optional[str] = None
    target_industry: Optional[str] = None
