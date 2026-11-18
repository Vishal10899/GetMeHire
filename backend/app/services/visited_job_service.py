import datetime
from typing import Tuple, List, Optional
from urllib.parse import urlparse
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.models import VisitedJob, Job, User, SavedJob
from app.schemas.job import JobListResponseItem
from app.schemas.visited_job import JobVisitRecordResponse, VisitedJobItem, VisitedJobsListResponse

class VisitedJobService:
    """
    Candidate Visited-Job Tracking Service (PRD §4.4 & §4.5).
    Safely records clicks to official employer application links with deduplication,
    validates outbound URLs against open redirect vulnerabilities, and provides audit history.
    """

    @staticmethod
    def validate_redirect_url(url: str) -> str:
        if not url:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job has no application URL configured")
        clean_url = url.strip()
        parsed = urlparse(clean_url)
        if parsed.scheme not in ["http", "https"] or not parsed.netloc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid application URL destination")
        
        # SSRF & Localhost loopback mitigation
        hostname = (parsed.hostname or "").lower()
        disallowed_hosts = {"localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254", "::1"}
        if hostname in disallowed_hosts or hostname.startswith("10.") or hostname.startswith("192.168.") or (hostname.startswith("172.") and any(hostname.startswith(f"172.{i}.") for i in range(16, 32))):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Disallowed target destination")
        
        return clean_url

    @classmethod
    def record_job_visit(cls, db: Session, user: User, job_id: int) -> JobVisitRecordResponse:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job listing not found")

        # Validate application URL against open redirect vulnerability
        valid_redirect_url = cls.validate_redirect_url(job.application_url)

        now = datetime.datetime.now(datetime.timezone.utc)
        visited = db.query(VisitedJob).filter(
            VisitedJob.user_id == user.id,
            VisitedJob.job_id == job.id
        ).first()

        if visited:
            visited.last_visited_at = now
            visited.visit_count += 1
        else:
            visited = VisitedJob(
                user_id=user.id,
                job_id=job.id,
                visited_at=now,
                last_visited_at=now,
                visit_count=1
            )
            db.add(visited)

        db.commit()
        db.refresh(visited)

        return JobVisitRecordResponse(
            job_id=job.id,
            redirect_url=valid_redirect_url,
            visited_at=visited.visited_at,
            last_visited_at=visited.last_visited_at,
            visit_count=visited.visit_count,
            disclaimer="Visiting an employer application page does not mean an application was submitted."
        )

    @classmethod
    def get_user_visited_jobs(
        cls,
        db: Session,
        user: User,
        limit: int = 50,
        offset: int = 0
    ) -> VisitedJobsListResponse:
        total_unique = db.query(func.count(VisitedJob.id)).filter(VisitedJob.user_id == user.id).scalar() or 0
        total_clicks = db.query(func.coalesce(func.sum(VisitedJob.visit_count), 0)).filter(VisitedJob.user_id == user.id).scalar() or 0

        visited_records = db.query(VisitedJob).options(
            joinedload(VisitedJob.job).joinedload(Job.company),
            joinedload(VisitedJob.job).joinedload(Job.source)
        ).filter(
            VisitedJob.user_id == user.id
        ).order_by(
            VisitedJob.last_visited_at.desc()
        ).offset(offset).limit(limit).all()

        # User's saved job IDs for badge
        user_saved = db.query(SavedJob.job_id).filter(SavedJob.user_id == user.id).all()
        saved_job_ids = {s[0] for s in user_saved}

        items = []
        for v in visited_records:
            j = v.job
            if not j:
                continue
            is_demo = bool((j.raw_source_data and j.raw_source_data.get("seed") is True) or j.id <= 7)
            job_item = JobListResponseItem(
                id=j.id,
                title=j.title,
                department=j.department,
                location=j.location,
                city=j.city,
                region=j.region,
                country=j.country,
                remote_type=j.remote_type,
                employment_type=j.employment_type,
                experience_level=j.experience_level,
                min_experience_years=j.min_experience_years,
                skills=j.skills or [],
                salary_min=j.salary_min,
                salary_max=j.salary_max,
                salary_currency=j.salary_currency,
                salary_period=j.salary_period,
                posting_date=j.posting_date,
                status=j.status,
                application_url=j.application_url,
                company_id=j.company_id,
                company_name=j.company.canonical_name if j.company else "Unknown",
                company_logo=j.company.logo_url if j.company else None,
                source_name=j.source.source_name if j.source else "Direct",
                first_seen_at=j.first_seen_at,
                last_verified_at=j.last_verified_at,
                is_saved=(j.id in saved_job_ids),
                is_demo=is_demo
            )
            items.append(VisitedJobItem(
                id=v.id,
                user_id=v.user_id,
                job_id=v.job_id,
                visited_at=v.visited_at,
                last_visited_at=v.last_visited_at,
                visit_count=v.visit_count,
                job=job_item
            ))

        return VisitedJobsListResponse(
            items=items,
            total_unique_visited=total_unique,
            total_clicks=total_clicks,
            disclaimer="Visiting an employer application page does not mean an application was submitted."
        )
