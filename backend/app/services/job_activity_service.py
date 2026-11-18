import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from fastapi import HTTPException, status, Request

from app.models import JobActivity, Job, User, Company, VisitedJob, SavedJob
from app.services.url_verifier import UrlVerifierService
from app.services.visited_job_service import VisitedJobService
from app.schemas.job_activity import (
    JobActivityItem,
    JobActivitySummaryResponse,
    JobActivityTimelineResponse,
    JobApplicationResponse,
    JobViewRecordResponse,
)


class JobActivityService:
    """
    Candidate Job Activity & Application Redirection Service.
    Tracks job views and application clicks with strict distinction:
    - VIEW: Candidate viewed job listing details.
    - APPLY_CLICK: Candidate clicked outbound 'Apply Now' to employer career board.
    - Never labels an apply click as a completed employer application.
    Enforces candidate multi-tenant isolation, SSRF prevention, and closed-job honesty.
    """

    @classmethod
    def determine_link_status(cls, job: Job) -> Tuple[str, bool]:
        """
        Determines truthful application link status:
        - CLOSED: Job status is closed, expired, or removed.
        - UNAVAILABLE: Missing or unsafe URL scheme.
        - INACCESSIBLE: Employer source is unavailable or known broken.
        - VERIFIED_ACCESSIBLE: URL is safe and recently verified active.
        - UNVERIFIED: Valid format but not recently checked.
        Returns: (status_string, is_safe)
        """
        if job.status in ("CLOSED", "EXPIRED", "REMOVED_PENDING_REVIEW"):
            return "CLOSED", True

        if not job.application_url or not job.application_url.strip():
            return "UNAVAILABLE", False

        if not UrlVerifierService.is_safe_url(job.application_url):
            return "INACCESSIBLE", False

        if job.status == "SOURCE_UNAVAILABLE":
            return "INACCESSIBLE", False

        # Freshness threshold: 14 days
        now = datetime.datetime.now(datetime.timezone.utc)
        if job.last_verified_at:
            delta = now - job.last_verified_at
            if delta.days <= 14:
                return "VERIFIED_ACCESSIBLE", True

        return "UNVERIFIED", True

    @classmethod
    def record_view(
        cls,
        db: Session,
        job_id: int,
        user: Optional[User] = None,
        request: Optional[Request] = None
    ) -> JobViewRecordResponse:
        job = db.query(Job).options(joinedload(Job.company), joinedload(Job.source)).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job listing not found")

        now = datetime.datetime.now(datetime.timezone.utc)
        user_id = user.id if user else None

        # Debounce: avoid duplicate view events within 2 minutes for the same user
        if user_id:
            two_mins_ago = now - datetime.timedelta(minutes=2)
            recent_view = db.query(JobActivity).filter(
                JobActivity.user_id == user_id,
                JobActivity.job_id == job_id,
                JobActivity.activity_type == "VIEW",
                JobActivity.created_at >= two_mins_ago
            ).first()

            if recent_view:
                return JobViewRecordResponse(
                    job_id=job.id,
                    activity_type="VIEW",
                    recorded_at=recent_view.created_at,
                    message="Job view already recorded within debounce window."
                )

        ip_addr = request.client.host if request and request.client else None
        user_agent = request.headers.get("user-agent")[:490] if request and request.headers.get("user-agent") else None
        company_name = job.company.canonical_name if job.company else "Unknown"

        activity = JobActivity(
            user_id=user_id,
            job_id=job.id,
            activity_type="VIEW",
            company_id=job.company_id,
            company_name=company_name,
            job_title=job.normalized_title or job.title,
            source_platform=job.source.source_name if job.source else "Direct",
            application_url=job.application_url,
            redirect_result="SUCCESS",
            ip_address=ip_addr,
            user_agent=user_agent,
            created_at=now
        )
        db.add(activity)
        db.commit()

        return JobViewRecordResponse(
            job_id=job.id,
            activity_type="VIEW",
            recorded_at=now,
            message="Job view activity recorded successfully."
        )

    @classmethod
    def record_apply_click(
        cls,
        db: Session,
        job_id: int,
        user: Optional[User] = None,
        request: Optional[Request] = None,
        allow_closed: bool = False,
        update_visited_job: bool = True
    ) -> JobApplicationResponse:
        job = db.query(Job).options(joinedload(Job.company), joinedload(Job.source)).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job listing not found")

        now = datetime.datetime.now(datetime.timezone.utc)
        user_id = user.id if user else None
        ip_addr = request.client.host if request and request.client else None
        user_agent = request.headers.get("user-agent")[:490] if request and request.headers.get("user-agent") else None
        company_name = job.company.canonical_name if job.company else "Unknown"
        link_status, is_safe = cls.determine_link_status(job)

        # 1. Validate application URL format and safety (SSRF and disallowed schemes)
        if not job.application_url or not job.application_url.strip():
            db.add(JobActivity(
                user_id=user_id,
                job_id=job.id,
                activity_type="APPLY_CLICK",
                company_id=job.company_id,
                company_name=company_name,
                job_title=job.normalized_title or job.title,
                source_platform=job.source.source_name if job.source else "Direct",
                application_url="",
                redirect_result="INVALID_URL",
                ip_address=ip_addr,
                user_agent=user_agent,
                created_at=now
            ))
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job listing has no application URL configured."
            )

        if not UrlVerifierService.is_safe_url(job.application_url):
            db.add(JobActivity(
                user_id=user_id,
                job_id=job.id,
                activity_type="APPLY_CLICK",
                company_id=job.company_id,
                company_name=company_name,
                job_title=job.normalized_title or job.title,
                source_platform=job.source.source_name if job.source else "Direct",
                application_url=job.application_url,
                redirect_result="INVALID_URL",
                ip_address=ip_addr,
                user_agent=user_agent,
                created_at=now
            ))
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or disallowed application URL destination."
            )

        # 2. Check if job is closed or expired
        if job.status in ("CLOSED", "EXPIRED", "REMOVED_PENDING_REVIEW"):
            db.add(JobActivity(
                user_id=user_id,
                job_id=job.id,
                activity_type="APPLY_CLICK",
                company_id=job.company_id,
                company_name=company_name,
                job_title=job.normalized_title or job.title,
                source_platform=job.source.source_name if job.source else "Direct",
                application_url=job.application_url,
                redirect_result="CLOSED_JOB",
                ip_address=ip_addr,
                user_agent=user_agent,
                created_at=now
            ))
            db.commit()
            if not allow_closed:
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail="This job vacancy is marked as closed by the employer and is no longer accepting applications."
                )

        # 3. Successful apply click
        activity = JobActivity(
            user_id=user_id,
            job_id=job.id,
            activity_type="APPLY_CLICK",
            company_id=job.company_id,
            company_name=company_name,
            job_title=job.normalized_title or job.title,
            source_platform=job.source.source_name if job.source else "Direct",
            application_url=job.application_url,
            redirect_result="SUCCESS",
            ip_address=ip_addr,
            user_agent=user_agent,
            created_at=now
        )
        db.add(activity)

        # Update backward-compatible VisitedJob tracking for authenticated user
        if update_visited_job and user:
            visited = db.query(VisitedJob).filter(
                VisitedJob.user_id == user.id,
                VisitedJob.job_id == job.id
            ).first()
            if visited:
                visited.last_visited_at = now
                visited.visit_count += 1
            else:
                db.add(VisitedJob(
                    user_id=user.id,
                    job_id=job.id,
                    visited_at=now,
                    last_visited_at=now,
                    visit_count=1
                ))

        db.commit()

        return JobApplicationResponse(
            job_id=job.id,
            application_url=job.application_url,
            company_name=company_name,
            job_title=job.normalized_title or job.title,
            status=job.status,
            redirect_result="SUCCESS",
            link_status=link_status,
            is_safe=is_safe
        )

    @classmethod
    def get_user_activity_summary(cls, db: Session, user: User) -> JobActivitySummaryResponse:
        total_views = db.query(func.count(JobActivity.id)).filter(
            JobActivity.user_id == user.id,
            JobActivity.activity_type == "VIEW"
        ).scalar() or 0

        total_clicks = db.query(func.count(JobActivity.id)).filter(
            JobActivity.user_id == user.id,
            JobActivity.activity_type == "APPLY_CLICK"
        ).scalar() or 0

        unique_companies = db.query(func.count(func.distinct(JobActivity.company_id))).filter(
            JobActivity.user_id == user.id,
            JobActivity.company_id.isnot(None)
        ).scalar() or 0

        saved_count = db.query(func.count(SavedJob.id)).filter(
            SavedJob.user_id == user.id
        ).scalar() or 0

        # Recent 5 views
        recent_views_records = db.query(JobActivity).options(
            joinedload(JobActivity.job).joinedload(Job.company)
        ).filter(
            JobActivity.user_id == user.id,
            JobActivity.activity_type == "VIEW"
        ).order_by(JobActivity.created_at.desc()).limit(5).all()

        # Recent 5 apply clicks
        recent_clicks_records = db.query(JobActivity).options(
            joinedload(JobActivity.job).joinedload(Job.company)
        ).filter(
            JobActivity.user_id == user.id,
            JobActivity.activity_type == "APPLY_CLICK"
        ).order_by(JobActivity.created_at.desc()).limit(5).all()

        def _to_item(act: JobActivity) -> JobActivityItem:
            j = act.job
            return JobActivityItem(
                id=act.id,
                activity_type=act.activity_type,
                job_id=act.job_id,
                job_title=act.job_title or (j.title if j else "Job"),
                company_id=act.company_id or (j.company_id if j else None),
                company_name=act.company_name or (j.company.canonical_name if j and j.company else "Unknown"),
                company_logo=j.company.logo_url if j and j.company else None,
                location=j.location if j else None,
                remote_type=j.remote_type if j else None,
                employment_type=j.employment_type if j else None,
                job_status=j.status if j else "CLOSED",
                status=j.status if j else "CLOSED",
                application_url=act.application_url,
                redirect_result=act.redirect_result,
                source_platform=act.source_platform,
                created_at=act.created_at
            )

        return JobActivitySummaryResponse(
            total_views=total_views,
            total_apply_clicks=total_clicks,
            unique_companies_explored=unique_companies,
            saved_jobs_count=saved_count,
            recent_views=[_to_item(a) for a in recent_views_records],
            recent_apply_clicks=[_to_item(a) for a in recent_clicks_records]
        )

    @classmethod
    def get_user_activity_timeline(
        cls,
        db: Session,
        user: User,
        activity_type: Optional[str] = None,
        company: Optional[str] = None,
        job_title: Optional[str] = None,
        start_date: Optional[datetime.datetime] = None,
        end_date: Optional[datetime.datetime] = None,
        limit: int = 20,
        offset: int = 0
    ) -> JobActivityTimelineResponse:
        query = db.query(JobActivity).options(
            joinedload(JobActivity.job).joinedload(Job.company)
        ).filter(JobActivity.user_id == user.id)

        if activity_type and activity_type.upper() in ("VIEW", "APPLY_CLICK"):
            query = query.filter(JobActivity.activity_type == activity_type.upper())

        if company and company.strip():
            query = query.filter(JobActivity.company_name.ilike(f"%{company.strip()}%"))

        if job_title and job_title.strip():
            query = query.filter(JobActivity.job_title.ilike(f"%{job_title.strip()}%"))

        if start_date:
            query = query.filter(JobActivity.created_at >= start_date)

        if end_date:
            query = query.filter(JobActivity.created_at <= end_date)

        total = query.count()
        records = query.order_by(JobActivity.created_at.desc()).offset(offset).limit(limit).all()

        total_views = db.query(func.count(JobActivity.id)).filter(
            JobActivity.user_id == user.id,
            JobActivity.activity_type == "VIEW"
        ).scalar() or 0

        total_clicks = db.query(func.count(JobActivity.id)).filter(
            JobActivity.user_id == user.id,
            JobActivity.activity_type == "APPLY_CLICK"
        ).scalar() or 0

        unique_companies = db.query(func.count(func.distinct(JobActivity.company_id))).filter(
            JobActivity.user_id == user.id,
            JobActivity.company_id.isnot(None)
        ).scalar() or 0

        items = []
        for act in records:
            j = act.job
            items.append(JobActivityItem(
                id=act.id,
                activity_type=act.activity_type,
                job_id=act.job_id,
                job_title=act.job_title or (j.title if j else "Job"),
                company_id=act.company_id or (j.company_id if j else None),
                company_name=act.company_name or (j.company.canonical_name if j and j.company else "Unknown"),
                company_logo=j.company.logo_url if j and j.company else None,
                location=j.location if j else None,
                remote_type=j.remote_type if j else None,
                employment_type=j.employment_type if j else None,
                job_status=j.status if j else "CLOSED",
                status=j.status if j else "CLOSED",
                application_url=act.application_url,
                redirect_result=act.redirect_result,
                source_platform=act.source_platform,
                created_at=act.created_at
            ))

        page = (offset // limit) + 1 if limit > 0 else 1

        return JobActivityTimelineResponse(
            items=items,
            total=total,
            total_count=total,
            page=page,
            page_size=limit,
            total_views=total_views,
            total_apply_clicks=total_clicks,
            unique_companies=unique_companies
        )
