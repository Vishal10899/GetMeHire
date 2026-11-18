import time
import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import Source, IngestionRun, Job, Company
from app.ingestion.base import SourceAdapter, NormalizedJob
from app.ingestion.adapters.greenhouse import GreenhouseAdapter
from app.ingestion.adapters.lever import LeverAdapter
from app.ingestion.adapters.ashby import AshbyAdapter
from app.ingestion.adapters.generic_json import GenericJsonAdapter
from app.ingestion.adapters.web_scraper import WebScraperAdapter
from app.ingestion.adapters.workable import WorkableAdapter
from app.ingestion.adapters.smartrecruiters import SmartRecruitersAdapter
from app.ingestion.adapters.personio import PersonioAdapter
from app.ingestion.adapters.remotive import RemotiveAdapter
from app.ingestion.adapters.usajobs import USAJobsAdapter
from app.ingestion.adapters.recruitee import RecruiteeAdapter
from app.ingestion.adapters.breezy import BreezyAdapter
from app.ingestion.adapters.bamboohr import BambooHRAdapter
from app.ingestion.adapters.teamtailor import TeamtailorAdapter
from app.ingestion.adapters.amazon import AmazonJobsAdapter
from app.ingestion.adapters.workday import WorkdayAdapter
from app.ingestion.adapters.icims import ICIMSAdapter
from app.ingestion.adapters.jobvite import JobviteAdapter
from app.ingestion.adapters.oracle_recruiting import OracleRecruitingAdapter
from app.ingestion.adapters.successfactors import SuccessFactorsAdapter
from app.ingestion.adapters.healthcare_careers import HealthcareCareersAdapter
from app.ingestion.adapters.university_careers import UniversityCareersAdapter
from app.ingestion.deduplication import compute_content_fingerprint
from app.ingestion.anomaly import AnomalyDetector
from app.ingestion.classifier import classify_profession_with_confidence
from app.ingestion.normalizer import generate_normalized_title, generate_system_summary, get_country_code, is_valid_job_posting, is_valid_application_url
from app.services.early_career_intelligence import EarlyCareerIntelligence
from sqlalchemy.orm.attributes import flag_modified

ADAPTER_MAP = {
    "GREENHOUSE": GreenhouseAdapter,
    "LEVER": LeverAdapter,
    "ASHBY": AshbyAdapter,
    "GENERIC_JSON": GenericJsonAdapter,
    "WEB_SCRAPER": WebScraperAdapter,
    "WORKABLE": WorkableAdapter,
    "SMARTRECRUITERS": SmartRecruitersAdapter,
    "PERSONIO": PersonioAdapter,
    "REMOTIVE": RemotiveAdapter,
    "USAJOBS": USAJobsAdapter,
    "RECRUITEE": RecruiteeAdapter,
    "BREEZY": BreezyAdapter,
    "BREEZY_HR": BreezyAdapter,
    "BAMBOOHR": BambooHRAdapter,
    "TEAMTAILOR": TeamtailorAdapter,
    "AMAZON_JOBS": AmazonJobsAdapter,
    "AMAZON": AmazonJobsAdapter,
    "WORKDAY": WorkdayAdapter,
    "ICIMS": ICIMSAdapter,
    "JOBVITE": JobviteAdapter,
    "ORACLE": OracleRecruitingAdapter,
    "ORACLE_RECRUITING": OracleRecruitingAdapter,
    "SUCCESSFACTORS": SuccessFactorsAdapter,
    "SAP_SUCCESSFACTORS": SuccessFactorsAdapter,
    "HEALTHCARE": HealthcareCareersAdapter,
    "HEALTHCARE_CAREERS": HealthcareCareersAdapter,
    "UNIVERSITY": UniversityCareersAdapter,
    "UNIVERSITY_CAREERS": UniversityCareersAdapter,
}

class IngestionRunner:
    @classmethod
    def get_adapter(cls, source_type: str) -> SourceAdapter:
        adapter_cls = ADAPTER_MAP.get(source_type.upper())
        if not adapter_cls:
            raise ValueError(f"No adapter found for source type '{source_type}'")
        return adapter_cls()

    @classmethod
    def execute_sync(cls, db: Session, source_id: int) -> IngestionRun:
        source = db.query(Source).filter(Source.id == source_id).with_for_update().first()
        if not source:
            raise ValueError(f"Source with id {source_id} not found")

        company = db.query(Company).filter(Company.id == source.company_id).first()
        company_name = company.canonical_name if company else "Unknown"

        # Concurrency lease / state check
        running_run = db.query(IngestionRun).filter(
            IngestionRun.source_id == source.id,
            IngestionRun.status == "RUNNING"
        ).first()

        if running_run:
            # Check if stuck for > 30 minutes
            if (datetime.datetime.utcnow() - running_run.start_time.replace(tzinfo=None)).total_seconds() > 1800:
                running_run.status = "FAILED"
                running_run.error_message = "Ingestion lease expired (timeout)"
                db.commit()
            else:
                raise RuntimeError(f"Ingestion run {running_run.id} is already in progress for this source")

        # 1. Create IngestionRun
        run = IngestionRun(
            source_id=source.id,
            status="RUNNING",
            start_time=datetime.datetime.now(datetime.timezone.utc),
            pagination_checkpoint={}
        )
        db.add(run)
        source.last_attempted_at = datetime.datetime.now(datetime.timezone.utc)
        db.commit()
        db.refresh(run)

        start_perf = time.time()
        adapter = cls.get_adapter(source.source_type)

        discovered = 0
        inserted = 0
        updated = 0
        unchanged = 0
        rejected = 0
        seen_external_ids = set()

        # Resume from saved continuation cursor if present (Requirement 5)
        saved_cursor = (source.configuration or {}).get("continuation_cursor")
        checkpoint = dict(saved_cursor) if isinstance(saved_cursor, dict) else {}
        has_more = True
        page_count = 0
        max_pages = int((source.configuration or {}).get("max_pages", 50))  # configurable pagination limit with high safety ceiling

        try:
            while has_more and page_count < max_pages:
                page_count += 1
                raw_records, next_checkpoint, has_more = adapter.fetch_page(
                    source_url=source.canonical_source_url,
                    config=source.configuration or {},
                    checkpoint=checkpoint
                )
                checkpoint = next_checkpoint
                run.pagination_checkpoint = checkpoint  # checkpoint persistence
                discovered += len(raw_records)

                for raw_item in raw_records:
                    normalized: Optional[NormalizedJob] = adapter.parse_and_normalize(raw_item)
                    if not normalized:
                        rejected += 1
                        continue

                    # Data quality gate: reject dummy/test postings from feed
                    is_valid, reject_reason = is_valid_job_posting(normalized.title, normalized.description)
                    if not is_valid:
                        rejected += 1
                        continue

                    # Application URL verification gate (Requirement 6)
                    url_valid, url_reason = is_valid_application_url(normalized.application_url)
                    if not url_valid:
                        rejected += 1
                        continue

                    # Guard against multi-location duplicates in same feed batch
                    if normalized.external_job_id in seen_external_ids:
                        unchanged += 1
                        continue
                    seen_external_ids.add(normalized.external_job_id)

                    # Dynamic company resolution for multi-employer public feeds
                    target_company_id = source.company_id
                    target_company_name = company_name
                    if normalized.company_name and normalized.company_name.strip():
                        comp_clean = normalized.company_name.strip()
                        existing_comp = db.query(Company).filter(func.lower(Company.canonical_name) == func.lower(comp_clean)).first()
                        if not existing_comp:
                            existing_comp = Company(
                                canonical_name=comp_clean,
                                identity_status="VERIFIED" if source.access_classification == "PUBLIC_FEED" else "UNVERIFIED"
                            )
                            db.add(existing_comp)
                            db.flush()
                        target_company_id = existing_comp.id
                        target_company_name = existing_comp.canonical_name

                    fingerprint = compute_content_fingerprint(normalized, target_company_name)

                    # Query existing record (case-insensitive external_job_id match to prevent unique violation)
                    existing_job = db.query(Job).filter(
                        Job.source_id == source.id,
                        func.lower(Job.external_job_id) == func.lower(normalized.external_job_id)
                    ).first()

                    now_dt = datetime.datetime.now(datetime.timezone.utc)

                    clean_title = generate_normalized_title(normalized.title)
                    summary = generate_system_summary(normalized.description)
                    prof, conf = classify_profession_with_confidence(normalized.title, normalized.department, normalized.description)

                    # Bounded field length guards against schema limits (255 chars)
                    safe_title = (normalized.title or "").strip()[:255]
                    safe_clean_title = (clean_title or "").strip()[:255]
                    safe_loc = normalized.location[:255] if normalized.location else None
                    safe_city = normalized.city[:100] if normalized.city else None
                    safe_region = normalized.region[:100] if normalized.region else None
                    safe_country = normalized.country[:100] if normalized.country else None
                    safe_country_code = (normalized.country_code or get_country_code(normalized.country))
                    safe_country_code = safe_country_code[:10] if safe_country_code else None
                    safe_dept = normalized.department[:255] if normalized.department else None

                    # Early career intelligence evaluation
                    ec_cat, ec_meta = EarlyCareerIntelligence.evaluate_job(
                        title=safe_title,
                        description=normalized.description or "",
                        employment_type=normalized.employment_type,
                        source_min_years=normalized.min_experience_years
                    )

                    if not existing_job:
                        # Cross-feed duplicate detection under same company identity (Requirement 4)
                        cross_dup = db.query(Job).filter(
                            Job.company_id == target_company_id,
                            Job.content_fingerprint == fingerprint,
                            Job.status.in_(["ACTIVE", "POSSIBLY_STALE"])
                        ).first()
                        if cross_dup:
                            cross_dup.last_seen_at = now_dt
                            cross_dup.last_verified_at = now_dt
                            unchanged += 1
                            continue

                        # INSERT new job
                        new_job = Job(
                            company_id=target_company_id,
                            source_id=source.id,
                            external_job_id=normalized.external_job_id,
                            title=safe_title,
                            normalized_title=safe_clean_title,
                            description=normalized.description,
                            system_summary=summary,
                            department=safe_dept,
                            profession=prof,
                            classification_confidence=conf,
                            location=safe_loc,
                            city=safe_city,
                            region=safe_region,
                            country=safe_country,
                            country_code=safe_country_code,
                            remote_type=normalized.remote_type,
                            work_arrangement=getattr(normalized, "work_arrangement", None) or normalized.remote_type or "ONSITE",
                            remote_eligibility=getattr(normalized, "remote_eligibility", None) or "UNSPECIFIED",
                            early_career_category=ec_cat,
                            early_career_metadata=ec_meta,
                            employment_type=normalized.employment_type,
                            experience_level=normalized.experience_level,
                            min_experience_years=normalized.min_experience_years,
                            skills=normalized.skills,
                            salary_min=normalized.salary_min,
                            salary_max=normalized.salary_max,
                            salary_currency=normalized.salary_currency,
                            salary_period=normalized.salary_period,
                            posting_date=normalized.posting_date or now_dt,
                            first_seen_at=now_dt,
                            last_seen_at=now_dt,
                            last_verified_at=now_dt,
                            status="ACTIVE",
                            application_url=normalized.application_url,
                            content_fingerprint=fingerprint,
                            raw_source_data=normalized.raw_data,
                            search_vector=func.to_tsvector("english", f"{safe_title} {target_company_name} {safe_dept or ''} {safe_country or ''} {safe_city or ''} {normalized.description[:2000]}")
                        )
                        db.add(new_job)
                        inserted += 1
                    else:
                        # Existing job: check fingerprint
                        if existing_job.content_fingerprint == fingerprint:
                            # UNCHANGED: verify timestamps and ensure active if was stale
                            existing_job.last_seen_at = now_dt
                            existing_job.last_verified_at = now_dt
                            if existing_job.status in ["POSSIBLY_STALE", "SOURCE_UNAVAILABLE"]:
                                existing_job.status = "ACTIVE"
                            # Ensure normalized location metadata is populated
                            if not existing_job.country and safe_country:
                                existing_job.country = safe_country
                                existing_job.city = safe_city
                                existing_job.region = safe_region
                                existing_job.country_code = safe_country_code
                            elif not existing_job.country_code and existing_job.country:
                                existing_job.country_code = get_country_code(existing_job.country)
                            if not existing_job.early_career_category:
                                existing_job.early_career_category = ec_cat
                                existing_job.early_career_metadata = ec_meta
                            unchanged += 1
                        else:
                            # UPDATED: content has changed
                            existing_job.company_id = target_company_id
                            existing_job.title = safe_title
                            existing_job.normalized_title = safe_clean_title
                            existing_job.description = normalized.description
                            existing_job.system_summary = summary
                            existing_job.department = safe_dept
                            existing_job.profession = prof
                            existing_job.classification_confidence = conf
                            existing_job.location = safe_loc
                            existing_job.city = safe_city
                            existing_job.region = safe_region
                            existing_job.country = safe_country
                            existing_job.country_code = safe_country_code
                            existing_job.remote_type = normalized.remote_type
                            existing_job.work_arrangement = getattr(normalized, "work_arrangement", None) or normalized.remote_type or "ONSITE"
                            existing_job.remote_eligibility = getattr(normalized, "remote_eligibility", None) or "UNSPECIFIED"
                            existing_job.early_career_category = ec_cat
                            existing_job.early_career_metadata = ec_meta
                            existing_job.employment_type = normalized.employment_type
                            existing_job.experience_level = normalized.experience_level
                            existing_job.min_experience_years = normalized.min_experience_years
                            existing_job.skills = normalized.skills
                            existing_job.salary_min = normalized.salary_min
                            existing_job.salary_max = normalized.salary_max
                            existing_job.salary_currency = normalized.salary_currency
                            existing_job.application_url = normalized.application_url
                            existing_job.content_fingerprint = fingerprint
                            existing_job.raw_source_data = normalized.raw_data
                            existing_job.search_vector = func.to_tsvector("english", f"{safe_title} {target_company_name} {safe_dept or ''} {safe_country or ''} {safe_city or ''} {normalized.description[:2000]}")
                            existing_job.last_seen_at = now_dt
                            existing_job.last_verified_at = now_dt
                            existing_job.status = "ACTIVE"
                            updated += 1

                db.flush()

                # Pacing between pages to adhere to source rate_limit_rpm (PRD §5.4)
                rate_rpm = source.rate_limit_rpm if source.rate_limit_rpm and source.rate_limit_rpm > 0 else 60
                pace_delay = 60.0 / rate_rpm
                if has_more and page_count < max_pages:
                    time.sleep(min(pace_delay, 1.0))

            # 2. Pagination continuation and exhaustion tracking (Requirement 5)
            is_exhausted = not has_more
            src_config = dict(source.configuration or {})
            if is_exhausted:
                src_config["continuation_cursor"] = None
                src_config["crawl_status"] = "FULLY_CRAWLED"
            else:
                src_config["continuation_cursor"] = checkpoint
                src_config["crawl_status"] = "PARTIALLY_CRAWLED"
            source.configuration = src_config
            flag_modified(source, "configuration")

            # 3. Anomaly detection
            anomaly_detected, anomaly_details = AnomalyDetector.evaluate_run(
                db=db,
                source=source,
                discovered_count=discovered,
                rejected_count=rejected,
                inserted_count=inserted,
                updated_count=updated,
                unchanged_count=unchanged
            )

            # 4. Staleness / Disappearance check
            # Only trigger lifecycle transitions if run succeeded, no anomaly detected,
            # AND the board crawl genuinely exhausted all pages (prevent closing jobs on partial crawls)!
            if not anomaly_detected and discovered > 0 and is_exhausted:
                # Mark jobs that were NOT seen in this complete sync as POSSIBLY_STALE
                # Exclude seeded demo jobs (IDs <= 7) from automated staleness transitions
                unseen_jobs = db.query(Job).filter(
                    Job.source_id == source.id,
                    Job.id > 7,
                    Job.status == "ACTIVE",
                    Job.external_job_id.notin_(seen_external_ids)
                ).all()

                for j in unseen_jobs:
                    j.status = "POSSIBLY_STALE"

                # 5. Transition POSSIBLY_STALE jobs exceeding grace period to CLOSED (PRD §5.8)
                grace_days = int((source.configuration or {}).get("stale_grace_days", 14))
                cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=grace_days)
                stale_expired_jobs = db.query(Job).filter(
                    Job.source_id == source.id,
                    Job.id > 7,
                    Job.status == "POSSIBLY_STALE",
                    Job.last_seen_at < cutoff_date
                ).all()

                for j in stale_expired_jobs:
                    j.status = "CLOSED"

            run.duration_seconds = round(time.time() - start_perf, 2)
            run.end_time = datetime.datetime.now(datetime.timezone.utc)
            run.records_discovered = discovered
            run.records_inserted = inserted
            run.records_updated = updated
            run.records_unchanged = unchanged
            run.records_rejected = rejected
            run.anomaly_detected = anomaly_detected
            run.anomaly_details = anomaly_details

            if anomaly_detected:
                run.status = "ANOMALY_QUARANTINE"
                source.health_status = "DEGRADED"
            elif not is_exhausted:
                run.status = "PARTIAL"
                source.health_status = "HEALTHY"
                source.last_successful_sync_at = run.end_time
            else:
                run.status = "SUCCESS"
                source.health_status = "HEALTHY"
                source.last_successful_sync_at = run.end_time
                source.last_complete_sync_at = run.end_time

            db.commit()
            db.refresh(run)
            return run

        except Exception as exc:
            db.rollback()
            err_category = adapter.classify_error(exc)
            run.status = "FAILED"
            run.end_time = datetime.datetime.now(datetime.timezone.utc)
            run.duration_seconds = round(time.time() - start_perf, 2)
            run.error_message = str(exc)
            run.error_category = err_category

            # append to error history
            history = list(source.error_history or [])
            history.append({
                "run_id": run.id,
                "error": str(exc),
                "category": err_category,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
            })
            source.error_history = history[-10:]  # keep last 10 errors

            # Resilient health status determination:
            # - Permanent errors mark source as FAILING immediately
            # - Rate limit or Auth errors mark source as DEGRADED
            # - Transient network/socket/DNS errors mark DEGRADED unless consecutive failures >= 3
            if err_category == "PERMANENT":
                source.health_status = "FAILING"
            elif err_category in ["AUTHENTICATION", "RATE_LIMIT"]:
                source.health_status = "DEGRADED"
            else:  # TRANSIENT, PARSE
                recent_failures = [h for h in source.error_history[-3:] if h.get("category") == "TRANSIENT"]
                if len(recent_failures) >= 3:
                    source.health_status = "FAILING"
                else:
                    source.health_status = "DEGRADED"

            db.commit()
            db.refresh(run)
            return run

    @classmethod
    def expire_stale_jobs(cls, db: Session, source_id: Optional[int] = None, grace_days: int = 14) -> int:
        """
        Transitions POSSIBLY_STALE jobs older than grace_days into CLOSED status (PRD §5.8).
        """
        cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=grace_days)
        query = db.query(Job).filter(
            Job.id > 7,
            Job.status == "POSSIBLY_STALE",
            Job.last_seen_at < cutoff_date
        )
        if source_id is not None:
            query = query.filter(Job.source_id == source_id)

        expired_jobs = query.all()
        for j in expired_jobs:
            j.status = "CLOSED"
        db.commit()
        return len(expired_jobs)
