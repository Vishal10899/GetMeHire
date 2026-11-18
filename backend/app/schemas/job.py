from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from decimal import Decimal

class CompanySummary(BaseModel):
    id: int
    canonical_name: str
    website: Optional[str] = None
    logo_url: Optional[str] = None
    identity_status: str

    model_config = ConfigDict(from_attributes=True)

class JobBase(BaseModel):
    title: str
    normalized_title: Optional[str] = None
    department: Optional[str] = None
    profession: Optional[str] = None  # Canonical profession key or legacy alias
    classification_confidence: Optional[float] = 1.0
    system_summary: Optional[str] = None
    location: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    remote_type: str = "ONSITE"  # REMOTE, HYBRID, ONSITE
    work_arrangement: Optional[str] = "ONSITE"  # ONSITE, REMOTE, HYBRID, FIELD_BASED, FLEXIBLE, NOT_SPECIFIED
    remote_eligibility: Optional[str] = "UNSPECIFIED"  # WORLDWIDE, REGION_RESTRICTED, COUNTRY_RESTRICTED, TIMEZONE_RESTRICTED, EMPLOYER_DEFINED, NOT_REMOTE, UNSPECIFIED
    employment_type: str = "FULL_TIME"  # FULL_TIME, PART_TIME, CONTRACT, FREELANCE, INTERNSHIP, APPRENTICESHIP, TEMPORARY, PERMANENT, SEASONAL, CASUAL, COMMISSION, PERFORMANCE_BASED, FIXED_TERM, SHIFT_BASED, OTHER
    experience_level: Optional[str] = None  # ENTRY, MID, SENIOR, LEAD, EXECUTIVE
    min_experience_years: Optional[float] = None
    early_career_category: Optional[str] = None  # TRUE_FRESHER, GRADUATE, ENTRY_LEVEL, EARLY_CAREER, JUNIOR, TRAINEE, INTERNSHIP, APPRENTICESHIP, etc.
    early_career_metadata: Optional[Dict[str, Any]] = None
    skills: List[str] = Field(default_factory=list)
    salary_min: Optional[Decimal] = None
    salary_max: Optional[Decimal] = None
    salary_currency: Optional[str] = "USD"
    salary_period: Optional[str] = "YEAR"
    posting_date: Optional[datetime] = None
    status: str = "ACTIVE"
    application_url: str
    is_demo: bool = False

class JobDetailResponse(JobBase):
    id: int
    company_id: int
    source_id: int
    external_job_id: str
    description: str
    source_name: Optional[str] = None
    first_seen_at: datetime
    last_seen_at: datetime
    last_verified_at: datetime
    company: CompanySummary
    is_saved: bool = False
    application_link_status: str = "VERIFIED_ACCESSIBLE"  # VERIFIED_ACCESSIBLE, UNVERIFIED, CLOSED, UNAVAILABLE, INACCESSIBLE
    is_application_link_safe: bool = True

    model_config = ConfigDict(from_attributes=True)

class JobListResponseItem(JobBase):
    id: int
    company_id: int
    company_name: str
    company_logo: Optional[str] = None
    source_name: str
    first_seen_at: datetime
    last_verified_at: datetime
    is_saved: bool = False
    match_score: Optional[float] = None
    match_reasons: Optional[List[str]] = None
    match_breakdown: Optional[Dict[str, Any]] = None
    profession_score: Optional[float] = None
    early_career_score: Optional[float] = None
    recommendation_reasons: Optional[List[str]] = None

    model_config = ConfigDict(from_attributes=True)

class JobSearchResponse(BaseModel):
    items: List[JobListResponseItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
    did_you_mean: Optional[str] = None
    is_corrected: bool = False
    suggested_roles: List[str] = Field(default_factory=list)
    detected_profession: Optional[str] = None
    query_latency_ms: Optional[float] = None

class SimilarJobResponse(BaseModel):
    jobs: List[JobListResponseItem]

class ProfessionItem(BaseModel):
    key: str
    label: str
    category: Optional[str] = None
    count: int
    description: str
    icon: Optional[str] = None
    canonical_roles: List[str] = Field(default_factory=list)
    core_skills: List[str] = Field(default_factory=list)

class ProfessionListResponse(BaseModel):
    professions: List[ProfessionItem]
    total_jobs: int

class CompanyItem(BaseModel):
    id: int
    canonical_name: str
    website: Optional[str] = None
    career_page_url: Optional[str] = None
    logo_url: Optional[str] = None
    identity_status: str = "VERIFIED"
    verification_status: str = "DISCOVERED"
    domain: Optional[str] = None
    last_verified_at: Optional[datetime] = None
    verification_notes: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)
    industry: Optional[str] = None
    country: Optional[str] = None
    operating_region: Optional[str] = None
    ats_provider: Optional[str] = None
    ats_board_id: Optional[str] = None
    discovery_source: Optional[str] = None
    active_jobs_count: int = 0
    sources_count: int = 0
    last_successful_crawl: Optional[datetime] = None
    source_health: Optional[str] = "HEALTHY"

    model_config = ConfigDict(from_attributes=True)

class CompanyListResponse(BaseModel):
    items: List[CompanyItem]
    total: int
    page: int = 1
    page_size: int = 50

