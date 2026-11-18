import time
import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.models import Company, Source, Job, IngestionRun
from app.discovery.connectors.base import DiscoveredCompanyCandidate
from app.discovery.connectors.sec_edgar import SecEdgarConnector
from app.discovery.connectors.open_directory import OpenDirectoryConnector
from app.discovery.connectors.ats_directory import PublicAtsDirectoryConnector
from app.discovery.connectors.global_enterprise import GlobalEnterpriseConnector
from app.discovery.connectors.public_registries import PublicRegistriesConnector
from app.discovery.normalizer import clean_company_name, extract_canonical_domain, is_duplicate_company
from app.discovery.verifier import CompanyVerifierService

class CompanyDiscoveryService:
    """
    Scalable Discovery & Verification Service:
    - Ingests candidates from open public registries.
    - Runs deduplication and name/domain normalization.
    - Drives tiered status transitions.
    """

    CONNECTORS = [
        PublicAtsDirectoryConnector(),
        OpenDirectoryConnector(),
        GlobalEnterpriseConnector(),
        PublicRegistriesConnector(),
        SecEdgarConnector(),
    ]

    @classmethod
    def run_discovery_pipeline(
        cls,
        db: Session,
        limit_per_source: int = 500,
        verify_online: bool = True,
        max_to_verify: int = 200,
        target_country: Optional[str] = None,
        target_industry: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes discovery pass across all registered public connectors with deduplication.
        """
        discovered_count = 0
        duplicates_skipped = 0
        verified_count = 0

        for connector in cls.CONNECTORS:
            try:
                candidates = connector.discover(limit=limit_per_source)
                for cand in candidates:
                    # Filter by target country / industry if requested
                    if target_country and cand.country and target_country.lower() not in cand.country.lower():
                        continue
                    if target_industry and cand.industry and target_industry.lower() not in cand.industry.lower():
                        continue

                    # Deduplication check
                    existing = is_duplicate_company(
                        db=db,
                        name=cand.name,
                        domain=cand.domain,
                        aliases=cand.aliases
                    )
                    if existing:
                        duplicates_skipped += 1
                        # Enrich existing metadata if missing
                        if not existing.domain and cand.domain:
                            existing.domain = cand.domain
                        if not existing.career_page_url and cand.career_page_url:
                            existing.career_page_url = cand.career_page_url
                        if cand.ats_provider and (not existing.ats_provider or existing.ats_provider == "WEB_SCRAPER"):
                            existing.ats_provider = cand.ats_provider
                            existing.ats_board_id = cand.ats_board_id
                            CompanyVerifierService.verify_source(db, existing)
                        if not existing.industry and cand.industry:
                            existing.industry = cand.industry
                        if not existing.country and cand.country:
                            existing.country = cand.country
                        if not existing.operating_region and cand.operating_region:
                            existing.operating_region = cand.operating_region
                        continue

                    # Insert new company
                    initial_status = "DISCOVERED"
                    if cand.career_page_url and cand.ats_provider:
                        initial_status = "SOURCE_VERIFIED"
                    elif cand.career_page_url:
                        initial_status = "CAREER_PAGE_FOUND"
                    elif cand.domain:
                        initial_status = "DOMAIN_VERIFIED"

                    comp = Company(
                        canonical_name=cand.name,
                        domain=cand.domain,
                        website=cand.website or (f"https://{cand.domain}" if cand.domain else None),
                        career_page_url=cand.career_page_url,
                        country=cand.country,
                        operating_region=cand.operating_region,
                        industry=cand.industry,
                        ats_provider=cand.ats_provider,
                        ats_board_id=cand.ats_board_id,
                        discovery_source=cand.discovery_source,
                        verification_status=initial_status,
                        last_verified_at=datetime.datetime.now(datetime.timezone.utc),
                        aliases=cand.aliases,
                        company_metadata=cand.metadata,
                        identity_status="VERIFIED"
                    )
                    db.add(comp)
                    db.flush()
                    discovered_count += 1

                    # If candidate has ATS provider, link Source
                    if cand.ats_provider and cand.career_page_url:
                        CompanyVerifierService.verify_source(db, comp)

                db.commit()
            except Exception as e:
                db.rollback()

        # Optional online verification pass for unverified domains
        if verify_online and max_to_verify > 0:
            import httpx
            import socket
            unverified = db.query(Company).filter(
                Company.verification_status == "DISCOVERED"
            ).limit(max_to_verify).all()

            headers = {
                "User-Agent": "GetMeHire-Verifier/2.0 (+https://getmehire.com/bot; domain-check)",
                "Accept": "text/html,application/xhtml+xml,*/*;q=0.8"
            }

            with httpx.Client(timeout=2.5, follow_redirects=True) as client:
                for comp in unverified:
                    # If domain is missing, probe standard corporate domains
                    if not comp.domain and not comp.website:
                        simple_name = clean_company_name(comp.canonical_name).lower().replace(" ", "").replace("-", "").replace(",", "")
                        candidate_domains = [f"{simple_name}.com", f"{simple_name}.co", f"{simple_name}.io"]
                        for d in candidate_domains:
                            try:
                                socket.gethostbyname(d)
                            except Exception:
                                continue
                            try:
                                resp = client.head(f"https://{d}", headers=headers)
                                if resp.status_code < 500:
                                    comp.domain = d
                                    comp.website = f"https://{d}"
                                    comp.verification_status = "DOMAIN_VERIFIED"
                                    comp.last_verified_at = datetime.datetime.now(datetime.timezone.utc)
                                    verified_count += 1
                                    break
                            except Exception:
                                continue
                    elif comp.domain or comp.website:
                        if CompanyVerifierService.verify_domain(comp, client=client):
                            verified_count += 1

                    if verified_count % 20 == 0:
                        db.commit()

            db.commit()

        # Evaluate vacancy statuses
        all_comps = db.query(Company).all()
        for comp in all_comps:
            CompanyVerifierService.evaluate_active_vacancies(db, comp)
        db.commit()

        return {
            "discovered_new": discovered_count,
            "duplicates_skipped": duplicates_skipped,
            "online_verified": verified_count,
            "total_companies": db.query(Company).count()
        }

    @classmethod
    def get_discovery_telemetry(cls, db: Session) -> Dict[str, Any]:
        """
        Calculates complete telemetry across the 7 tiered verification states,
        country distributions, industry distributions, and crawl activity.
        """
        total = db.query(Company).count()

        # Tier breakdown
        tiers = {
            "DISCOVERED": db.query(Company).filter(Company.verification_status == "DISCOVERED").count(),
            "DOMAIN_VERIFIED": db.query(Company).filter(Company.verification_status == "DOMAIN_VERIFIED").count(),
            "CAREER_PAGE_FOUND": db.query(Company).filter(Company.verification_status == "CAREER_PAGE_FOUND").count(),
            "SOURCE_VERIFIED": db.query(Company).filter(Company.verification_status == "SOURCE_VERIFIED").count(),
            "ACTIVE_JOB_SOURCE": db.query(Company).filter(Company.verification_status == "ACTIVE_JOB_SOURCE").count(),
            "NO_CURRENT_VACANCIES": db.query(Company).filter(Company.verification_status == "NO_CURRENT_VACANCIES").count(),
            "UNSUPPORTED": db.query(Company).filter(Company.verification_status == "UNSUPPORTED").count(),
        }

        # Country distribution
        countries = [
            {"country": row[0] or "Unspecified", "count": row[1]}
            for row in db.query(Company.country, func.count(Company.id)).group_by(Company.country).order_by(func.count(Company.id).desc()).limit(15).all()
        ]

        # Region distribution
        regions = [
            {"region": row[0] or "Global", "count": row[1]}
            for row in db.query(Company.operating_region, func.count(Company.id)).group_by(Company.operating_region).order_by(func.count(Company.id).desc()).all()
        ]

        # Industry distribution
        industries = [
            {"industry": row[0] or "Unclassified", "count": row[1]}
            for row in db.query(Company.industry, func.count(Company.id)).group_by(Company.industry).order_by(func.count(Company.id).desc()).limit(20).all()
        ]

        # ATS provider distribution
        ats_providers = [
            {"provider": row[0] or "DIRECT_CAREER_PAGE", "count": row[1]}
            for row in db.query(Company.ats_provider, func.count(Company.id)).group_by(Company.ats_provider).order_by(func.count(Company.id).desc()).all()
        ]

        # Active sources and jobs
        active_sources_count = db.query(Source).filter(Source.is_active == True).count()
        active_jobs_count = db.query(Job).filter(Job.status == "ACTIVE").count()

        # Specific metric calculations for Section 7 dashboard
        domain_verified_total = db.query(Company).filter(
            or_(
                Company.domain.isnot(None),
                Company.verification_status.in_(["DOMAIN_VERIFIED", "CAREER_PAGE_FOUND", "SOURCE_VERIFIED", "ACTIVE_JOB_SOURCE", "NO_CURRENT_VACANCIES"])
            )
        ).count()

        career_pages_total = db.query(Company).filter(
            or_(
                Company.career_page_url.isnot(None),
                Company.verification_status.in_(["CAREER_PAGE_FOUND", "SOURCE_VERIFIED", "ACTIVE_JOB_SOURCE", "NO_CURRENT_VACANCIES"])
            )
        ).count()

        verified_ats_sources = db.query(Source).filter(
            Source.is_active == True,
            Source.source_type.in_(["GREENHOUSE", "LEVER", "ASHBY", "SMARTRECRUITERS", "PERSONIO", "WORKABLE", "BAMBOOHR", "TEAMTAILOR", "RECRUITEE", "BREEZY", "BREEZY_HR"])
        ).count()

        all_sources = db.query(Source).all()
        partially_crawled_count = sum(
            1 for s in all_sources
            if (s.configuration or {}).get("crawl_status") == "PARTIALLY_CRAWLED"
            or (s.configuration or {}).get("continuation_cursor") is not None
        )

        total_rejected_jobs = db.query(func.coalesce(func.sum(IngestionRun.records_rejected), 0)).scalar() or 0

        # India Coverage Diagnostics (Section 6)
        in_comps = db.query(Company).filter(or_(Company.country == "India", Company.operating_region == "South Asia")).count()
        ver_in_comps = db.query(Company).filter(
            or_(Company.country == "India", Company.operating_region == "South Asia"),
            Company.verification_status.in_(["DOMAIN_VERIFIED", "CAREER_PAGE_FOUND", "SOURCE_VERIFIED", "ACTIVE_JOB_SOURCE", "NO_CURRENT_VACANCIES"])
        ).count()
        cp_in_comps = db.query(Company).filter(
            or_(Company.country == "India", Company.operating_region == "South Asia"),
            or_(Company.career_page_url.isnot(None), Company.verification_status.in_(["CAREER_PAGE_FOUND", "SOURCE_VERIFIED", "ACTIVE_JOB_SOURCE", "NO_CURRENT_VACANCIES"]))
        ).count()
        act_in_sources = db.query(Company).filter(
            or_(Company.country == "India", Company.operating_region == "South Asia"),
            Company.verification_status == "ACTIVE_JOB_SOURCE"
        ).count()
        act_in_jobs = db.query(Job).filter(or_(Job.country == "India", Job.country_code == "IN"), Job.status == "ACTIVE").count()

        city_dist = [
            {"city": row[0] or "Unspecified", "count": row[1]}
            for row in db.query(Job.city, func.count(Job.id)).filter(
                or_(Job.country == "India", Job.country_code == "IN"),
                Job.status == "ACTIVE",
                Job.city.isnot(None)
            ).group_by(Job.city).order_by(func.count(Job.id).desc()).limit(15).all()
        ]

        employer_dist = [
            {"company": row[0] or "Unknown", "count": row[1]}
            for row in db.query(Company.canonical_name, func.count(Job.id)).join(
                Job, Job.company_id == Company.id
            ).filter(
                or_(Job.country == "India", Job.country_code == "IN"),
                Job.status == "ACTIVE"
            ).group_by(Company.canonical_name).order_by(func.count(Job.id).desc()).limit(15).all()
        ]

        zero_or_failed_sources = [
            {
                "source_id": s.id,
                "source_name": s.source_name,
                "company_name": s.company.canonical_name if s.company else "Unknown",
                "source_type": s.source_type,
                "health_status": s.health_status,
                "last_failure": (s.error_history[-1].get("message") if s.error_history else None),
                "last_crawled_at": (
                    s.last_successful_sync_at.isoformat()
                    if s.last_successful_sync_at
                    else (s.last_attempted_at.isoformat() if s.last_attempted_at else None)
                ),
            }
            for s in db.query(Source).join(Company, Company.id == Source.company_id).filter(
                or_(Company.country == "India", Company.operating_region == "South Asia"),
                Source.health_status.in_(["FAILING", "DEGRADED", "QUARANTINED"])
            ).limit(10).all()
        ]

        india_diagnostics = {
            "registered_employers": in_comps,
            "verified_employers": ver_in_comps,
            "employers_with_career_pages": cp_in_comps,
            "active_job_sources": act_in_sources,
            "active_vacancies": act_in_jobs,
            "city_distribution": city_dist,
            "employer_distribution": employer_dist,
            "zero_or_failed_sources": zero_or_failed_sources,
        }

        return {
            "total_companies": total,
            "domain_verified_companies": domain_verified_total,
            "career_pages_found": career_pages_total,
            "verified_ats_sources": verified_ats_sources,
            "active_job_sources": tiers["ACTIVE_JOB_SOURCE"],
            "no_current_vacancies": tiers["NO_CURRENT_VACANCIES"],
            "unsupported_sources": tiers["UNSUPPORTED"],
            "partially_crawled_sources": partially_crawled_count,
            "pending_verification": tiers["DISCOVERED"],
            "active_jobs_count": active_jobs_count,
            "jobs_rejected_count": int(total_rejected_jobs),
            "tiers": tiers,
            "countries": countries,
            "regions": regions,
            "industries": industries,
            "ats_providers": ats_providers,
            "active_sources_count": active_sources_count,
            "india_diagnostics": india_diagnostics,
        }
