import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, or_
from fastapi import HTTPException
from app.models import Source, Company, IngestionRun, Job, AuditLog, User
from app.schemas.admin import (
    SourceCreate, SourceUpdate, SourceResponse, IngestionRunResponse, HealthCheckResponse,
    GlobalSearchQualityDashboardResponse
)
from app.ingestion.runner import IngestionRunner

class AdminService:
    @staticmethod
    def create_source(db: Session, actor: User, source_in: SourceCreate) -> SourceResponse:
        # Find or create company
        company = db.query(Company).filter(Company.canonical_name.ilike(source_in.company_name.strip())).first()
        if not company:
            company = Company(
                canonical_name=source_in.company_name.strip(),
                website=source_in.company_website,
                identity_status="VERIFIED"
            )
            db.add(company)
            db.flush()

        source = Source(
            company_id=company.id,
            source_name=source_in.source_name,
            source_type=source_in.source_type.upper(),
            canonical_source_url=source_in.canonical_source_url,
            external_board_id=source_in.external_board_id,
            access_classification=source_in.access_classification,
            sync_schedule_cron=source_in.sync_schedule_cron,
            rate_limit_rpm=source_in.rate_limit_rpm,
            concurrency_limit=source_in.concurrency_limit,
            configuration=source_in.configuration,
            is_active=True,
            health_status="HEALTHY"
        )
        db.add(source)
        db.flush()

        audit = AuditLog(
            actor_user_id=actor.id,
            action="CREATE_SOURCE",
            target_type="SOURCE",
            target_id=str(source.id),
            details={"source_name": source.source_name, "company": company.canonical_name}
        )
        db.add(audit)
        db.commit()
        db.refresh(source)

        return SourceResponse(
            id=source.id,
            company_id=company.id,
            company_name=company.canonical_name,
            source_name=source.source_name,
            source_type=source.source_type,
            canonical_source_url=source.canonical_source_url,
            external_board_id=source.external_board_id,
            access_classification=source.access_classification,
            sync_schedule_cron=source.sync_schedule_cron,
            rate_limit_rpm=source.rate_limit_rpm,
            concurrency_limit=source.concurrency_limit,
            is_active=source.is_active,
            last_attempted_at=source.last_attempted_at,
            last_successful_sync_at=source.last_successful_sync_at,
            last_complete_sync_at=source.last_complete_sync_at,
            health_status=source.health_status,
            total_jobs=0,
            active_jobs=0,
            created_at=source.created_at,
            pagination_status="FULLY_CRAWLED",
            has_continuation_cursor=False,
            jobs_discovered=0,
            jobs_accepted=0,
            jobs_rejected=0
        )

    @staticmethod
    def get_sources(db: Session) -> List[SourceResponse]:
        sources = db.query(Source).options(joinedload(Source.company)).order_by(Source.id.asc()).all()
        result = []
        for s in sources:
            total_jobs = db.query(Job).filter(Job.source_id == s.id).count()
            active_jobs = db.query(Job).filter(Job.source_id == s.id, Job.status == "ACTIVE").count()

            latest_run = db.query(IngestionRun).filter(IngestionRun.source_id == s.id).order_by(IngestionRun.id.desc()).first()
            latest_failed = db.query(IngestionRun).filter(IngestionRun.source_id == s.id, IngestionRun.status == "FAILED").order_by(IngestionRun.id.desc()).first()

            cfg = s.configuration or {}
            crawl_status = cfg.get("crawl_status") or ("PARTIALLY_CRAWLED" if latest_run and latest_run.status == "PARTIAL" else "FULLY_CRAWLED")
            has_cursor = bool(cfg.get("continuation_cursor"))

            last_fail_at = None
            last_fail_msg = None
            if latest_failed:
                last_fail_at = latest_failed.end_time or latest_failed.start_time
                last_fail_msg = latest_failed.error_message
            elif s.error_history and len(s.error_history) > 0:
                last_err = s.error_history[-1]
                last_fail_msg = last_err.get("error")

            discovered = latest_run.records_discovered if latest_run else 0
            accepted = (latest_run.records_inserted + latest_run.records_updated + latest_run.records_unchanged) if latest_run else 0
            rejected = latest_run.records_rejected if latest_run else 0

            res = SourceResponse(
                id=s.id,
                company_id=s.company_id,
                company_name=s.company.canonical_name if s.company else "Unknown",
                source_name=s.source_name,
                source_type=s.source_type,
                canonical_source_url=s.canonical_source_url,
                external_board_id=s.external_board_id,
                access_classification=s.access_classification,
                sync_schedule_cron=s.sync_schedule_cron,
                rate_limit_rpm=s.rate_limit_rpm,
                concurrency_limit=s.concurrency_limit,
                is_active=s.is_active,
                last_attempted_at=s.last_attempted_at,
                last_successful_sync_at=s.last_successful_sync_at,
                last_complete_sync_at=s.last_complete_sync_at,
                health_status=s.health_status,
                total_jobs=total_jobs,
                active_jobs=active_jobs,
                created_at=s.created_at,
                pagination_status=crawl_status,
                has_continuation_cursor=has_cursor,
                last_failure_at=last_fail_at,
                last_failure_message=last_fail_msg,
                jobs_discovered=discovered,
                jobs_accepted=accepted,
                jobs_rejected=rejected
            )
            result.append(res)
        return result

    @staticmethod
    def update_source(db: Session, actor: User, source_id: int, source_in: SourceUpdate) -> SourceResponse:
        source = db.query(Source).options(joinedload(Source.company)).filter(Source.id == source_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        if source_in.source_name is not None:
            source.source_name = source_in.source_name
        if source_in.is_active is not None:
            source.is_active = source_in.is_active
        if source_in.sync_schedule_cron is not None:
            source.sync_schedule_cron = source_in.sync_schedule_cron
        if source_in.rate_limit_rpm is not None:
            source.rate_limit_rpm = source_in.rate_limit_rpm
        if source_in.concurrency_limit is not None:
            source.concurrency_limit = source_in.concurrency_limit
        if source_in.configuration is not None:
            source.configuration = source_in.configuration

        source.updated_at = datetime.datetime.now(datetime.timezone.utc)
        source.config_version += 1

        audit = AuditLog(
            actor_user_id=actor.id,
            action="UPDATE_SOURCE",
            target_type="SOURCE",
            target_id=str(source.id),
            details={"changes": source_in.model_dump(exclude_unset=True)}
        )
        db.add(audit)
        db.commit()
        db.refresh(source)

        total_jobs = db.query(Job).filter(Job.source_id == source.id).count()
        active_jobs = db.query(Job).filter(Job.source_id == source.id, Job.status == "ACTIVE").count()

        return SourceResponse(
            id=source.id,
            company_id=source.company_id,
            company_name=source.company.canonical_name if source.company else "Unknown",
            source_name=source.source_name,
            source_type=source.source_type,
            canonical_source_url=source.canonical_source_url,
            external_board_id=source.external_board_id,
            access_classification=source.access_classification,
            sync_schedule_cron=source.sync_schedule_cron,
            rate_limit_rpm=source.rate_limit_rpm,
            concurrency_limit=source.concurrency_limit,
            is_active=source.is_active,
            last_attempted_at=source.last_attempted_at,
            last_successful_sync_at=source.last_successful_sync_at,
            last_complete_sync_at=source.last_complete_sync_at,
            health_status=source.health_status,
            total_jobs=total_jobs,
            active_jobs=active_jobs,
            created_at=source.created_at,
            pagination_status=(source.configuration or {}).get("crawl_status", "FULLY_CRAWLED"),
            has_continuation_cursor=bool((source.configuration or {}).get("continuation_cursor")),
            jobs_discovered=0,
            jobs_accepted=0,
            jobs_rejected=0
        )

    @staticmethod
    def trigger_source_sync(db: Session, actor: User, source_id: int) -> IngestionRunResponse:
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        run = IngestionRunner.execute_sync(db, source_id)
        
        audit = AuditLog(
            actor_user_id=actor.id,
            action="TRIGGER_SYNC",
            target_type="SOURCE",
            target_id=str(source_id),
            details={"run_id": run.id, "status": run.status}
        )
        db.add(audit)
        db.commit()

        return IngestionRunResponse(
            id=run.id,
            source_id=run.source_id,
            source_name=source.source_name,
            status=run.status,
            start_time=run.start_time,
            end_time=run.end_time,
            duration_seconds=run.duration_seconds,
            records_discovered=run.records_discovered,
            records_inserted=run.records_inserted,
            records_updated=run.records_updated,
            records_unchanged=run.records_unchanged,
            records_rejected=run.records_rejected,
            error_message=run.error_message,
            error_category=run.error_category,
            anomaly_detected=run.anomaly_detected,
            anomaly_details=run.anomaly_details,
            created_at=run.created_at
        )

    @staticmethod
    def get_ingestion_runs(db: Session, limit: int = 50) -> List[IngestionRunResponse]:
        runs = db.query(IngestionRun).options(joinedload(IngestionRun.source)).order_by(desc(IngestionRun.id)).limit(limit).all()
        return [
            IngestionRunResponse(
                id=r.id,
                source_id=r.source_id,
                source_name=r.source.source_name if r.source else "Unknown",
                status=r.status,
                start_time=r.start_time,
                end_time=r.end_time,
                duration_seconds=r.duration_seconds,
                records_discovered=r.records_discovered,
                records_inserted=r.records_inserted,
                records_updated=r.records_updated,
                records_unchanged=r.records_unchanged,
                records_rejected=r.records_rejected,
                error_message=r.error_message,
                error_category=r.error_category,
                anomaly_detected=r.anomaly_detected,
                anomaly_details=r.anomaly_details,
                created_at=r.created_at
            )
            for r in runs
        ]

    @staticmethod
    def get_system_health(db: Session) -> HealthCheckResponse:
        total_sources = db.query(Source).count()
        active_sources = db.query(Source).filter(Source.is_active == True).count()
        healthy_sources = db.query(Source).filter(Source.health_status == "HEALTHY").count()
        failing_sources = db.query(Source).filter(Source.health_status.in_(["FAILING", "QUARANTINED"])).count()

        total_jobs = db.query(Job).count()
        active_jobs = db.query(Job).filter(Job.status == "ACTIVE").count()
        stale_jobs = db.query(Job).filter(Job.status == "POSSIBLY_STALE").count()
        closed_jobs = db.query(Job).filter(Job.status == "CLOSED").count()

        return HealthCheckResponse(
            status="HEALTHY" if failing_sources == 0 else "DEGRADED",
            database_connected=True,
            total_sources=total_sources,
            active_sources=active_sources,
            healthy_sources=healthy_sources,
            failing_sources=failing_sources,
            total_jobs=total_jobs,
            active_jobs=active_jobs,
            stale_jobs=stale_jobs,
            closed_jobs=closed_jobs,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

    @staticmethod
    def get_quality_dashboard(db: Session) -> GlobalSearchQualityDashboardResponse:
        now = datetime.datetime.now(datetime.timezone.utc)

        # 1. Global active jobs
        active_jobs = db.query(Job).filter(Job.status == "ACTIVE").count()
        stale_jobs = db.query(Job).filter(Job.status == "POSSIBLY_STALE").count()
        closed_jobs = db.query(Job).filter(Job.status == "CLOSED").count()

        # 2. Active employers (companies with active jobs)
        active_employers = (
            db.query(Company.id)
            .join(Job, Job.company_id == Company.id)
            .filter(Job.status == "ACTIVE")
            .distinct()
            .count()
        )

        # 3. Active job sources
        active_sources = db.query(Source).filter(Source.is_active == True, Source.health_status == "HEALTHY").count()

        # 4. Country-wise vacancy counts
        country_rows = (
            db.query(Job.country, func.count(Job.id).label("count"))
            .filter(Job.status == "ACTIVE", Job.country.isnot(None))
            .group_by(Job.country)
            .order_by(desc("count"))
            .all()
        )
        country_distribution = [{"country": r[0], "count": r[1]} for r in country_rows]

        # 5. City-wise vacancy counts (top 50)
        city_rows = (
            db.query(Job.city, Job.country, func.count(Job.id).label("count"))
            .filter(Job.status == "ACTIVE", Job.city.isnot(None))
            .group_by(Job.city, Job.country)
            .order_by(desc("count"))
            .limit(50)
            .all()
        )
        city_distribution = [{"city": r[0], "country": r[1], "count": r[2]} for r in city_rows]

        # 6. Industry-wise vacancy counts
        industry_rows = (
            db.query(Company.industry, func.count(Job.id).label("count"))
            .join(Job, Job.company_id == Company.id)
            .filter(Job.status == "ACTIVE", Company.industry.isnot(None))
            .group_by(Company.industry)
            .order_by(desc("count"))
            .all()
        )
        industry_distribution = [{"industry": r[0], "count": r[1]} for r in industry_rows]

        # 7. Profession-wise vacancy counts
        prof_rows = (
            db.query(Job.profession, func.count(Job.id).label("count"))
            .filter(Job.status == "ACTIVE")
            .group_by(Job.profession)
            .order_by(desc("count"))
            .all()
        )
        profession_distribution = [{"profession": r[0], "count": r[1]} for r in prof_rows]

        # 8. Employment-type distribution
        emp_rows = (
            db.query(Job.employment_type, func.count(Job.id).label("count"))
            .filter(Job.status == "ACTIVE")
            .group_by(Job.employment_type)
            .order_by(desc("count"))
            .all()
        )
        employment_type_distribution = [{"employment_type": r[0], "count": r[1]} for r in emp_rows]

        # 9. Work-arrangement distribution
        arr_rows = (
            db.query(func.coalesce(Job.work_arrangement, Job.remote_type).label("arr"), func.count(Job.id).label("count"))
            .filter(Job.status == "ACTIVE")
            .group_by("arr")
            .order_by(desc("count"))
            .all()
        )
        work_arrangement_distribution = [{"work_arrangement": r[0], "count": r[1]} for r in arr_rows]

        # 10. Remote eligibility distribution
        rel_rows = (
            db.query(Job.remote_eligibility, func.count(Job.id).label("count"))
            .filter(Job.status == "ACTIVE", Job.remote_eligibility.isnot(None))
            .group_by(Job.remote_eligibility)
            .order_by(desc("count"))
            .all()
        )
        remote_eligibility_distribution = [{"remote_eligibility": r[0], "count": r[1]} for r in rel_rows]

        # 11. Sources showing zero indexed jobs despite available website listings
        all_sources = db.query(Source).options(joinedload(Source.company)).all()
        zero_job_sources = []
        for s in all_sources:
            job_cnt = db.query(Job.id).filter(Job.source_id == s.id).limit(1).count()
            if job_cnt == 0:
                zero_job_sources.append({
                    "source_id": s.id,
                    "source_name": s.source_name,
                    "company_name": s.company.canonical_name if s.company else "Unknown",
                    "career_url": s.canonical_source_url,
                    "health_status": s.health_status,
                    "last_attempted_at": s.last_attempted_at.isoformat() if s.last_attempted_at else None
                })

        # 12. Failed and partially crawled sources
        failed_sources_q = (
            db.query(Source)
            .options(joinedload(Source.company))
            .filter(or_(Source.health_status.in_(["FAILING", "QUARANTINED", "DEGRADED"]), Source.is_active == False))
            .all()
        )
        failed_sources = [
            {
                "source_id": s.id,
                "source_name": s.source_name,
                "company_name": s.company.canonical_name if s.company else "Unknown",
                "health_status": s.health_status,
                "error": s.error_history[-1].get("error") if s.error_history else None,
                "canonical_url": s.canonical_source_url
            }
            for s in failed_sources_q
        ]

        partially_crawled_sources = []
        for s in db.query(Source).options(joinedload(Source.company)).all():
            cfg = s.configuration or {}
            if cfg.get("crawl_status") == "PARTIALLY_CRAWLED" or cfg.get("continuation_cursor"):
                partially_crawled_sources.append({
                    "source_id": s.id,
                    "source_name": s.source_name,
                    "company_name": s.company.canonical_name if s.company else "Unknown",
                    "has_cursor": bool(cfg.get("continuation_cursor"))
                })

        return GlobalSearchQualityDashboardResponse(
            global_active_jobs=active_jobs,
            active_employers=active_employers,
            active_job_sources=active_sources,
            country_distribution=country_distribution,
            city_distribution=city_distribution,
            industry_distribution=industry_distribution,
            profession_distribution=profession_distribution,
            employment_type_distribution=employment_type_distribution,
            work_arrangement_distribution=work_arrangement_distribution,
            remote_eligibility_distribution=remote_eligibility_distribution,
            zero_job_sources=zero_job_sources,
            failed_sources=failed_sources,
            partially_crawled_sources=partially_crawled_sources,
            stale_jobs_count=stale_jobs,
            closed_jobs_count=closed_jobs,
            timestamp=now
        )
