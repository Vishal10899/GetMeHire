import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Float, Numeric, Text, ForeignKey,
    UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="USER", nullable=False)  # USER, ADMIN
    account_status = Column(String(50), default="ACTIVE", nullable=False)  # ACTIVE, SUSPENDED, DELETED
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(255), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    saved_jobs = relationship("SavedJob", back_populates="user", cascade="all, delete-orphan")
    visited_jobs = relationship("VisitedJob", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")
    resume_versions = relationship("ResumeVersion", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    entitlements = relationship("Entitlement", back_populates="user", cascade="all, delete-orphan")
    job_activities = relationship("JobActivity", back_populates="user", cascade="all, delete-orphan")

    @property
    def full_name(self) -> Optional[str]:
        return self.profile.full_name if self.profile else None



class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    headline = Column(String(255), nullable=True)
    phone_number = Column(String(50), nullable=True)
    current_location = Column(String(255), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    portfolio_url = Column(String(500), nullable=True)
    profession = Column(String(100), nullable=True)  # ENGINEERING, DATA_AI, PRODUCT_DESIGN, SALES_BIZDEV, MARKETING_GROWTH, FINANCE_LEGAL, OPERATIONS_PEOPLE
    skills = Column(JSONB, default=list, nullable=False)  # list of strings: ["Python", "FastAPI", "React"]
    preferred_roles = Column(JSONB, default=list, nullable=False)  # list of strings: ["Software Engineer", "Backend Developer"]
    career_interests = Column(JSONB, default=list, nullable=False)  # list of dicts: [{"profession": "...", "preferred_roles": [...], "skills": [...], "experience_years": 3.0}]
    recent_searches = Column(JSONB, default=list, nullable=False)  # list of strings: ["python", "customer support remote"]
    total_experience_years = Column(Float, nullable=True)
    relevant_experience_years = Column(Float, nullable=True)
    preferred_countries = Column(JSONB, default=list, nullable=False)
    preferred_locations = Column(JSONB, default=list, nullable=False)
    work_arrangements = Column(JSONB, default=list, nullable=False)  # ["REMOTE", "HYBRID", "ONSITE"]
    employment_types = Column(JSONB, default=list, nullable=False)  # ["FULL_TIME", "CONTRACT"]
    salary_expectation_min = Column(Numeric(12, 2), nullable=True)
    salary_expectation_max = Column(Numeric(12, 2), nullable=True)
    salary_currency = Column(String(10), default="USD", nullable=True)
    salary_period = Column(String(20), default="YEAR", nullable=True)  # YEAR, MONTH, HOUR
    resume_filename = Column(String(255), nullable=True)
    resume_storage_path = Column(String(500), nullable=True)
    resume_uploaded_at = Column(DateTime(timezone=True), nullable=True)
    work_experience = Column(JSONB, default=list, nullable=True)
    education = Column(JSONB, default=list, nullable=True)
    projects = Column(JSONB, default=list, nullable=True)
    certifications = Column(JSONB, default=list, nullable=True)
    extracted_resume_data = Column(JSONB, default=dict, nullable=True)
    profile_completion_pct = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="profile")

    @property
    def visited_jobs_count(self) -> int:
        return len(self.user.visited_jobs) if self.user and self.user.visited_jobs else 0


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    canonical_name = Column(String(255), unique=True, index=True, nullable=False)
    website = Column(String(500), nullable=True)
    domain = Column(String(255), index=True, nullable=True)
    career_page_url = Column(String(500), nullable=True)
    identity_status = Column(String(50), default="VERIFIED", nullable=False)  # VERIFIED, UNVERIFIED
    verification_status = Column(String(50), default="DISCOVERED", index=True, nullable=False)  # DISCOVERED, DOMAIN_VERIFIED, CAREER_PAGE_FOUND, SOURCE_VERIFIED, ACTIVE_JOB_SOURCE, NO_CURRENT_VACANCIES, UNSUPPORTED
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_notes = Column(Text, nullable=True)
    aliases = Column(JSONB, default=list, nullable=True)
    logo_url = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    industry = Column(String(100), index=True, nullable=True)
    country = Column(String(100), index=True, nullable=True)
    operating_region = Column(String(100), nullable=True)
    ats_provider = Column(String(50), index=True, nullable=True)
    ats_board_id = Column(String(255), nullable=True)
    discovery_source = Column(String(255), nullable=True)
    company_metadata = Column(JSONB, default=dict, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    sources = relationship("Source", back_populates="company", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="company", cascade="all, delete-orphan")
    job_activities = relationship("JobActivity", back_populates="company")

    @property
    def last_successful_crawl(self) -> Optional[datetime.datetime]:
        if not self.sources:
            return None
        syncs = [s.last_successful_sync_at for s in self.sources if s.last_successful_sync_at]
        return max(syncs) if syncs else None

    @property
    def source_health(self) -> str:
        if not self.sources:
            return "UNCONFIGURED"
        statuses = [s.health_status for s in self.sources]
        if "HEALTHY" in statuses:
            return "HEALTHY"
        if "DEGRADED" in statuses:
            return "DEGRADED"
        if "QUARANTINED" in statuses:
            return "QUARANTINED"
        return statuses[0] if statuses else "UNKNOWN"


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    source_name = Column(String(255), nullable=False)
    source_type = Column(String(50), nullable=False)  # GREENHOUSE, LEVER, ASHBY, GENERIC_JSON, WEB_SCRAPER
    canonical_source_url = Column(String(500), nullable=False)
    external_board_id = Column(String(255), nullable=True)
    access_classification = Column(String(50), default="PUBLIC_API", nullable=False)  # PUBLIC_API, PERMITTED_SCRAPE, PARTNER_FEED
    sync_schedule_cron = Column(String(50), default="0 */6 * * *", nullable=False)
    rate_limit_rpm = Column(Integer, default=60, nullable=False)
    concurrency_limit = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_attempted_at = Column(DateTime(timezone=True), nullable=True)
    last_successful_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_complete_sync_at = Column(DateTime(timezone=True), nullable=True)
    health_status = Column(String(50), default="HEALTHY", nullable=False)  # HEALTHY, DEGRADED, FAILING, QUARANTINED
    error_history = Column(JSONB, default=list, nullable=False)
    configuration = Column(JSONB, default=dict, nullable=False)
    config_version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    company = relationship("Company", back_populates="sources")
    jobs = relationship("Job", back_populates="source", cascade="all, delete-orphan")
    ingestion_runs = relationship("IngestionRun", back_populates="source", cascade="all, delete-orphan")


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), default="RUNNING", nullable=False)  # RUNNING, SUCCESS, PARTIAL, FAILED, ANOMALY_QUARANTINE
    start_time = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    records_discovered = Column(Integer, default=0, nullable=False)
    records_inserted = Column(Integer, default=0, nullable=False)
    records_updated = Column(Integer, default=0, nullable=False)
    records_unchanged = Column(Integer, default=0, nullable=False)
    records_rejected = Column(Integer, default=0, nullable=False)
    pagination_checkpoint = Column(JSONB, default=dict, nullable=False)
    error_message = Column(Text, nullable=True)
    error_category = Column(String(50), nullable=True)  # TRANSIENT, PERMANENT, RATE_LIMIT, AUTHENTICATION, PARSE
    anomaly_detected = Column(Boolean, default=False, nullable=False)
    anomaly_details = Column(JSONB, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False)

    source = relationship("Source", back_populates="ingestion_runs")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)
    external_job_id = Column(String(255), nullable=False)
    title = Column(String(255), index=True, nullable=False)
    normalized_title = Column(String(255), index=True, nullable=True)
    description = Column(Text, nullable=False)
    system_summary = Column(Text, nullable=True)
    department = Column(String(255), nullable=True)
    profession = Column(String(100), index=True, nullable=True)  # Canonical profession key or legacy alias
    classification_confidence = Column(Float, default=1.0, nullable=True)
    location = Column(String(255), index=True, nullable=True)
    city = Column(String(100), index=True, nullable=True)
    region = Column(String(100), nullable=True)
    country = Column(String(100), index=True, nullable=True)
    country_code = Column(String(10), index=True, nullable=True)
    remote_type = Column(String(50), default="ONSITE", index=True, nullable=False)  # REMOTE, HYBRID, ONSITE
    work_arrangement = Column(String(50), default="ONSITE", index=True, nullable=True)  # ONSITE, REMOTE, HYBRID, FIELD_BASED, FLEXIBLE, NOT_SPECIFIED
    remote_eligibility = Column(String(50), default="UNSPECIFIED", index=True, nullable=True)  # WORLDWIDE, REGION_RESTRICTED, COUNTRY_RESTRICTED, TIMEZONE_RESTRICTED, EMPLOYER_DEFINED, NOT_REMOTE, UNSPECIFIED
    employment_type = Column(String(50), default="FULL_TIME", index=True, nullable=False)  # FULL_TIME, PART_TIME, CONTRACT, FREELANCE, INTERNSHIP, APPRENTICESHIP, TEMPORARY, PERMANENT, SEASONAL, CASUAL, COMMISSION, PERFORMANCE_BASED, FIXED_TERM, SHIFT_BASED, OTHER
    experience_level = Column(String(50), index=True, nullable=True)  # ENTRY, MID, SENIOR, LEAD, EXECUTIVE
    min_experience_years = Column(Float, nullable=True)
    early_career_category = Column(String(50), index=True, nullable=True)  # TRUE_FRESHER, GRADUATE, ENTRY_LEVEL, EARLY_CAREER, JUNIOR, TRAINEE, INTERNSHIP, APPRENTICESHIP, EXPERIENCE_FLEXIBLE, MISLABELLED_ENTRY_LEVEL, EXPERIENCED, UNCERTAIN
    early_career_metadata = Column(JSONB, default=dict, nullable=True)
    skills = Column(JSONB, default=list, nullable=False)
    salary_min = Column(Numeric(12, 2), nullable=True)
    salary_max = Column(Numeric(12, 2), nullable=True)
    salary_currency = Column(String(10), default="USD", nullable=True)
    salary_period = Column(String(20), default="YEAR", nullable=True)  # YEAR, MONTH, HOUR
    posting_date = Column(DateTime(timezone=True), nullable=True)
    first_seen_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False)
    last_seen_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False)
    last_verified_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False)
    status = Column(String(50), default="ACTIVE", index=True, nullable=False)  # ACTIVE, POSSIBLY_STALE, CLOSED, EXPIRED, SOURCE_UNAVAILABLE, REMOVED_PENDING_REVIEW
    application_url = Column(String(1000), nullable=False)
    content_fingerprint = Column(String(64), index=True, nullable=False)
    raw_source_data = Column(JSONB, default=dict, nullable=False)
    search_vector = Column(TSVECTOR, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    company = relationship("Company", back_populates="jobs")
    source = relationship("Source", back_populates="jobs")
    saved_by = relationship("SavedJob", back_populates="job", cascade="all, delete-orphan")
    visited_by = relationship("VisitedJob", back_populates="job", cascade="all, delete-orphan")
    activities = relationship("JobActivity", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("source_id", "external_job_id", name="uq_source_external_job_id"),
        Index("ix_jobs_search_vector", "search_vector", postgresql_using="gin"),
        Index("ix_jobs_status_posting", "status", "posting_date"),
    )


class SavedJob(Base):
    __tablename__ = "saved_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="saved_jobs")
    job = relationship("Job", back_populates="saved_by")

    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_user_job_saved"),
    )


class VisitedJob(Base):
    __tablename__ = "visited_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    visited_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False)
    last_visited_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)
    visit_count = Column(Integer, default=1, nullable=False)

    user = relationship("User", back_populates="visited_jobs")
    job = relationship("Job", back_populates="visited_by")

    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_user_job_visited"),
        Index("ix_visited_jobs_user_visited", "user_id", "last_visited_at"),
    )


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    criteria = Column(JSONB, default=dict, nullable=False)  # {"keywords": "python", "remote_only": true, "skills": ["FastAPI"]}
    frequency = Column(String(50), default="DAILY", nullable=False)  # IMMEDIATE, DAILY, WEEKLY
    is_active = Column(Boolean, default=True, nullable=False)
    last_evaluated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="alerts")
    deliveries = relationship("AlertDelivery", back_populates="alert", cascade="all, delete-orphan")


class AlertDelivery(Base):
    __tablename__ = "alert_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    deduplication_key = Column(String(255), unique=True, index=True, nullable=False)
    status = Column(String(50), default="SENT", nullable=False)  # PENDING, SENT, FAILED
    attempts = Column(Integer, default=1, nullable=False)
    provider_message_id = Column(String(255), nullable=True)
    failure_reason = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False)

    alert = relationship("Alert", back_populates="deliveries")
    job = relationship("Job")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)
    target_type = Column(String(100), nullable=False)
    target_id = Column(String(100), nullable=True)
    details = Column(JSONB, default=dict, nullable=False)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False)


class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_job_id = Column(Integer, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    version_title = Column(String(255), nullable=False, default="Tailored Resume")
    version_number = Column(Integer, default=1, nullable=False)
    template_id = Column(String(50), default="classic_single", nullable=False)  # classic_single, modern_professional, compact_technical, data_analytics, executive_leadership
    content = Column(JSONB, nullable=False, default=dict)
    analysis = Column(JSONB, nullable=True, default=dict)
    is_master = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="resume_versions")
    target_job = relationship("Job")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_job_id = Column(Integer, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    resume_version_id = Column(Integer, ForeignKey("resume_versions.id", ondelete="SET NULL"), nullable=True, index=True)
    amount = Column(Numeric(10, 2), default=9.99, nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    status = Column(String(50), default="PENDING", nullable=False, index=True)  # PENDING, COMPLETED, FAILED, REFUNDED
    provider = Column(String(50), default="TEST_GATEWAY", nullable=False)  # TEST_GATEWAY, STRIPE, RAZORPAY
    transaction_id = Column(String(255), unique=True, index=True, nullable=True)
    idempotency_key = Column(String(255), index=True, nullable=True)
    payment_metadata = Column(JSONB, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="orders")
    target_job = relationship("Job")
    resume_version = relationship("ResumeVersion")
    entitlement = relationship("Entitlement", back_populates="order", uselist=False)


class Entitlement(Base):
    __tablename__ = "entitlements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True)
    target_job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=True, index=True)
    resume_version_id = Column(Integer, ForeignKey("resume_versions.id", ondelete="SET NULL"), nullable=True, index=True)
    entitlement_type = Column(String(50), default="JOB_SPECIFIC_RESUME", nullable=False)  # JOB_SPECIFIC_RESUME
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    granted_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="entitlements")
    order = relationship("Order", back_populates="entitlement")
    target_job = relationship("Job")
    resume_version = relationship("ResumeVersion")

    __table_args__ = (
        UniqueConstraint("user_id", "target_job_id", name="uq_user_job_entitlement"),
    )


class JobActivity(Base):
    __tablename__ = "job_activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    activity_type = Column(String(50), nullable=False, index=True)  # VIEW, APPLY_CLICK
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    company_name = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=True)
    source_platform = Column(String(100), nullable=True)
    application_url = Column(String(1000), nullable=True)
    redirect_result = Column(String(50), nullable=True)  # SUCCESS, CLOSED_JOB, INVALID_URL, INACCESSIBLE
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False, index=True)

    user = relationship("User", back_populates="job_activities")
    job = relationship("Job", back_populates="activities")
    company = relationship("Company", back_populates="job_activities")

    __table_args__ = (
        Index("ix_job_activities_user_type_created", "user_id", "activity_type", "created_at"),
        Index("ix_job_activities_job_type", "job_id", "activity_type"),
    )



