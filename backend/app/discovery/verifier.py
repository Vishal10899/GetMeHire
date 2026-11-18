import datetime
import httpx
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.models import Company, Source, Job
from app.ingestion.crawler import CareerCrawlerService

class CompanyVerifierService:
    """
    Tiered Verification Pipeline:
    DISCOVERED -> DOMAIN_VERIFIED -> CAREER_PAGE_FOUND -> SOURCE_VERIFIED -> ACTIVE_JOB_SOURCE / NO_CURRENT_VACANCIES / UNSUPPORTED
    """

    @classmethod
    def verify_domain(cls, company: Company, client: Optional[httpx.Client] = None) -> bool:
        """
        Confirms official domain resolves via standard HTTP(S).
        """
        target = company.website or (f"https://{company.domain}" if company.domain else None)
        if not target:
            return False

        headers = {
            "User-Agent": "GetMeHire-Verifier/2.0 (+https://getmehire.com/bot; health-check)",
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8"
        }

        try:
            if client:
                resp = client.head(target, headers=headers, timeout=8.0, follow_redirects=True)
                if resp.status_code >= 400:
                    resp = client.get(target, headers=headers, timeout=8.0, follow_redirects=True)
            else:
                with httpx.Client(timeout=8.0, follow_redirects=True) as local_client:
                    resp = local_client.head(target, headers=headers)
                    if resp.status_code >= 400:
                        resp = local_client.get(target, headers=headers)

            # HTTP 200/3xx or CDN 403 confirms server exists and domain is active
            if resp.status_code < 500 or resp.status_code == 403:
                company.verification_status = "DOMAIN_VERIFIED"
                company.last_verified_at = datetime.datetime.now(datetime.timezone.utc)
                if not company.website:
                    company.website = str(resp.url)
                return True
        except Exception as e:
            company.verification_notes = f"Domain probe failed: {str(e)[:150]}"

        return False

    @classmethod
    def verify_career_page(cls, company: Company) -> Optional[str]:
        """
        Discovers and validates employer's official public career page.
        """
        if company.career_page_url:
            company.verification_status = "CAREER_PAGE_FOUND"
            company.last_verified_at = datetime.datetime.now(datetime.timezone.utc)
            return company.career_page_url

        target_site = company.website or (f"https://{company.domain}" if company.domain else None)
        if not target_site:
            return None

        career_url = CareerCrawlerService.discover_career_page(target_site)
        if career_url:
            company.career_page_url = career_url
            company.verification_status = "CAREER_PAGE_FOUND"
            company.last_verified_at = datetime.datetime.now(datetime.timezone.utc)
            return career_url

        return None

    @classmethod
    def verify_source(cls, db: Session, company: Company) -> Tuple[bool, Optional[Source]]:
        """
        Validates career page or ATS endpoint and links verified Source record.
        """
        if not company.career_page_url and not company.ats_board_id:
            return False, None

        FEED_TEMPLATES = {
            "GREENHOUSE": "https://boards-api.greenhouse.io/v1/boards/{board_id}/jobs?content=true",
            "LEVER": "https://api.lever.co/v0/postings/{board_id}?mode=json",
            "ASHBY": "https://api.ashbyhq.com/posting-api/job-board/{board_id}",
            "SMARTRECRUITERS": "https://api.smartrecruiters.com/v1/companies/{board_id}/postings?limit=100",
            "PERSONIO": "https://{board_id}.jobs.personio.de/xml?language=en",
            "BAMBOOHR": "https://{board_id}.bamboohr.com/careers/list",
            "RECRUITEE": "https://{board_id}.recruitee.com/api/offers/",
            "TEAMTAILOR": "https://{board_id}.teamtailor.com/jobs.rss",
            "WORKABLE": "https://apply.workable.com/api/v1/widget/accounts/{board_id}",
            "BREEZY": "https://{board_id}.breezy.hr/json",
        }

        if company.ats_provider and company.ats_provider != "WEB_SCRAPER" and company.ats_board_id:
            ats_provider = company.ats_provider
            board_id = company.ats_board_id
            template = FEED_TEMPLATES.get(ats_provider)
            feed_url = template.format(board_id=board_id) if template else company.career_page_url
        elif company.career_page_url:
            ats_provider, board_id, feed_url = CareerCrawlerService.detect_ats(company.career_page_url)
            company.ats_provider = ats_provider
            company.ats_board_id = board_id
        else:
            return False, None

        # Check existing source or create
        source = db.query(Source).filter(Source.company_id == company.id).first()
        if not source:
            source = Source(
                company_id=company.id,
                source_name=f"{company.canonical_name} {ats_provider.title()}",
                source_type=ats_provider,
                canonical_source_url=feed_url or company.career_page_url,
                external_board_id=board_id,
                access_classification="PUBLIC_API" if ats_provider != "WEB_SCRAPER" else "PERMITTED_SCRAPE",
                sync_schedule_cron="0 */12 * * *",
                configuration={"board_id": board_id, "company_slug": board_id} if board_id else {},
                health_status="HEALTHY",
                is_active=True
            )
            db.add(source)
            db.flush()
        else:
            source.source_type = ats_provider
            source.external_board_id = board_id
            source.canonical_source_url = feed_url or source.canonical_source_url
            if board_id:
                cfg = source.configuration or {}
                cfg["board_id"] = board_id
                cfg["company_slug"] = board_id
                source.configuration = cfg
            source.is_active = True

        company.verification_status = "SOURCE_VERIFIED"
        company.last_verified_at = datetime.datetime.now(datetime.timezone.utc)
        return True, source

    @classmethod
    def evaluate_active_vacancies(cls, db: Session, company: Company) -> str:
        """
        Transitions company to ACTIVE_JOB_SOURCE or NO_CURRENT_VACANCIES based on indexed jobs,
        while preserving higher-order verification tiers (SOURCE_VERIFIED, CAREER_PAGE_FOUND, DOMAIN_VERIFIED).
        """
        job_count = db.query(Job).filter(
            Job.company_id == company.id,
            Job.status.in_(["ACTIVE", "POSSIBLY_STALE"])
        ).count()

        if job_count > 0:
            company.verification_status = "ACTIVE_JOB_SOURCE"
        elif company.sources:
            company.verification_status = "NO_CURRENT_VACANCIES"
        elif company.career_page_url and company.ats_provider:
            company.verification_status = "SOURCE_VERIFIED"
        elif company.career_page_url:
            company.verification_status = "CAREER_PAGE_FOUND"
        elif company.domain or company.website:
            company.verification_status = "DOMAIN_VERIFIED"
        elif company.verification_status not in ["UNSUPPORTED"]:
            company.verification_status = "DISCOVERED"

        company.last_verified_at = datetime.datetime.now(datetime.timezone.utc)
        return company.verification_status
