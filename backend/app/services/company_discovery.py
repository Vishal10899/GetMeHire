import httpx
from typing import Optional, Dict, Any
from urllib.parse import urlparse
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models import Company, Source, User, AuditLog
from app.ingestion.runner import IngestionRunner

class CompanyDiscoveryService:
    """
    Automated ATS Board Discovery and Onboarding Engine (PRD §5.2).
    Probes public endpoints for Greenhouse, Lever, and Ashby to verify existence,
    extract sample job counts, and register verified company sources.
    """

    @staticmethod
    def _is_safe_url(url: str) -> bool:
        """
        Validates URL against SSRF attacks:
        - Blocks loopback, link-local, AWS metadata (169.254.169.254), private ranges.
        - Enforces http/https schemes only.
        """
        if not url:
            return False
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return False
            hostname = parsed.hostname or ""
            if not hostname:
                return False
            hostname_lower = hostname.lower()
            if hostname_lower in ("localhost", "127.0.0.1", "0.0.0.0", "::1", "169.254.169.254"):
                return False
            import ipaddress
            try:
                ip = ipaddress.ip_address(hostname)
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                    return False
            except ValueError:
                # Hostname is a domain name, not an IP literal
                pass
            return True
        except Exception:
            return False

    @staticmethod
    def extract_token_from_input(query_or_url: str) -> str:
        clean = query_or_url.strip()
        if "://" in clean:
            parsed = urlparse(clean)
            parts = [p for p in parsed.path.split("/") if p]
            if parts:
                clean = parts[0] if parts[0] not in ["jobs", "v1", "posting-api"] else parts[-1]
        token = clean.strip("/").split("/")[-1]
        import re
        return re.sub(r"[^a-zA-Z0-9_\-]", "", token)

    @classmethod
    def probe_ats_board(cls, query_or_url: str) -> Dict[str, Any]:
        token = cls.extract_token_from_input(query_or_url)
        headers = {"User-Agent": "JobDiscoveryPlatform/2.0 (+https://example.com/bot)"}
        lower_input = query_or_url.lower()

        candidates = []

        with httpx.Client(timeout=8.0) as client:
            # 1. Probe Greenhouse
            if "ashby" not in lower_input and "lever" not in lower_input:
                try:
                    gh_url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
                    gh_res = client.get(gh_url, headers=headers)
                    if gh_res.status_code == 200:
                        data = gh_res.json()
                        jobs = data.get("jobs", [])
                        candidates.append({
                            "found": True,
                            "source_type": "GREENHOUSE",
                            "board_id": token,
                            "canonical_source_url": f"https://boards.greenhouse.io/{token}",
                            "sample_jobs_count": len(jobs),
                            "details": f"Verified Greenhouse board for '{token}' with {len(jobs)} active listings."
                        })
                except Exception:
                    pass

            # 2. Probe Ashby
            if "greenhouse" not in lower_input and "lever" not in lower_input:
                try:
                    ash_url = f"https://api.ashbyhq.com/posting-api/job-board/{token}"
                    ash_res = client.get(ash_url, headers=headers)
                    if ash_res.status_code == 200:
                        data = ash_res.json()
                        jobs = data.get("jobs", [])
                        candidates.append({
                            "found": True,
                            "source_type": "ASHBY",
                            "board_id": token,
                            "canonical_source_url": f"https://jobs.ashbyhq.com/{token}",
                            "sample_jobs_count": len(jobs),
                            "details": f"Verified Ashby board for '{token}' with {len(jobs)} active listings."
                        })
                except Exception:
                    pass

            # 3. Probe Lever (US)
            if "greenhouse" not in lower_input and "ashby" not in lower_input:
                try:
                    lv_url = f"https://api.lever.co/v0/postings/{token}?mode=json"
                    lv_res = client.get(lv_url, headers=headers)
                    if lv_res.status_code == 200:
                        jobs = lv_res.json()
                        if isinstance(jobs, list):
                            candidates.append({
                                "found": True,
                                "source_type": "LEVER",
                                "board_id": token,
                                "canonical_source_url": f"https://jobs.lever.co/{token}",
                                "sample_jobs_count": len(jobs),
                                "details": f"Verified Lever board for '{token}' with {len(jobs)} active listings."
                            })
                except Exception:
                    pass

                # 4. Probe Lever (EU)
                try:
                    eu_lv_url = f"https://api.eu.lever.co/v0/postings/{token}?mode=json"
                    eu_lv_res = client.get(eu_lv_url, headers=headers)
                    if eu_lv_res.status_code == 200:
                        jobs = eu_lv_res.json()
                        if isinstance(jobs, list):
                            candidates.append({
                                "found": True,
                                "source_type": "LEVER",
                                "board_id": token,
                                "canonical_source_url": f"https://jobs.eu.lever.co/{token}",
                                "sample_jobs_count": len(jobs),
                                "details": f"Verified Lever EU board for '{token}' with {len(jobs)} active listings."
                            })
                except Exception:
                    pass

            # 5. Probe Workable
            try:
                w_url = f"https://apply.workable.com/api/v1/widget/accounts/{token}"
                w_res = client.get(w_url, headers=headers)
                if w_res.status_code == 200:
                    w_data = w_res.json()
                    w_jobs = w_data.get("jobs", []) if isinstance(w_data, dict) else []
                    candidates.append({
                        "found": True,
                        "source_type": "WORKABLE",
                        "board_id": token,
                        "canonical_source_url": f"https://apply.workable.com/{token}",
                        "sample_jobs_count": len(w_jobs),
                        "details": f"Verified Workable board for '{token}' with {len(w_jobs)} active listings."
                    })
            except Exception:
                pass

            # 6. Probe SmartRecruiters
            try:
                sr_url = f"https://api.smartrecruiters.com/v1/companies/{token}/postings?limit=10"
                sr_res = client.get(sr_url, headers=headers)
                if sr_res.status_code == 200:
                    sr_data = sr_res.json()
                    total = sr_data.get("totalFound", 0) if isinstance(sr_data, dict) else len(sr_data.get("content", []))
                    candidates.append({
                        "found": True,
                        "source_type": "SMARTRECRUITERS",
                        "board_id": token,
                        "canonical_source_url": f"https://api.smartrecruiters.com/v1/companies/{token}/postings",
                        "sample_jobs_count": total,
                        "details": f"Verified SmartRecruiters board for '{token}' with {total} active listings."
                    })
            except Exception:
                pass

            # 7. Probe Recruitee
            try:
                rec_url = f"https://{token}.recruitee.com/api/offers/"
                rec_res = client.get(rec_url, headers=headers)
                if rec_res.status_code == 200:
                    rec_data = rec_res.json()
                    rec_jobs = rec_data.get("offers", []) if isinstance(rec_data, dict) else []
                    candidates.append({
                        "found": True,
                        "source_type": "RECRUITEE",
                        "board_id": token,
                        "canonical_source_url": f"https://{token}.recruitee.com",
                        "sample_jobs_count": len(rec_jobs),
                        "details": f"Verified Recruitee board for '{token}' with {len(rec_jobs)} active listings."
                    })
            except Exception:
                pass

            # 8. Probe Breezy HR
            try:
                br_url = f"https://{token}.breezy.hr/json"
                br_res = client.get(br_url, headers=headers)
                if br_res.status_code == 200:
                    br_jobs = br_res.json()
                    if isinstance(br_jobs, list):
                        candidates.append({
                            "found": True,
                            "source_type": "BREEZY",
                            "board_id": token,
                            "canonical_source_url": f"https://{token}.breezy.hr",
                            "sample_jobs_count": len(br_jobs),
                            "details": f"Verified Breezy HR board for '{token}' with {len(br_jobs)} active listings."
                        })
            except Exception:
                pass

            # 9. Probe BambooHR
            try:
                bam_url = f"https://{token}.bamboohr.com/careers/list"
                bam_res = client.get(bam_url, headers=headers)
                if bam_res.status_code == 200:
                    bam_data = bam_res.json()
                    bam_jobs = bam_data.get("result", []) if isinstance(bam_data, dict) else []
                    candidates.append({
                        "found": True,
                        "source_type": "BAMBOOHR",
                        "board_id": token,
                        "canonical_source_url": f"https://{token}.bamboohr.com/careers/list",
                        "sample_jobs_count": len(bam_jobs),
                        "details": f"Verified BambooHR board for '{token}' with {len(bam_jobs)} active listings."
                    })
            except Exception:
                pass

            # 10. Probe Personio
            for p_domain in ["de", "com"]:
                try:
                    per_url = f"https://{token}.jobs.personio.{p_domain}/xml?language=en"
                    per_res = client.get(per_url, headers=headers)
                    if per_res.status_code == 200 and "<workpositions" in per_res.text:
                        candidates.append({
                            "found": True,
                            "source_type": "PERSONIO",
                            "board_id": token,
                            "canonical_source_url": per_url,
                            "sample_jobs_count": per_res.text.count("<job>"),
                            "details": f"Verified Personio feed for '{token}'."
                        })
                        break
                except Exception:
                    pass

            # 11. Probe Jobvite
            try:
                jv_url = f"https://jobs.jobvite.com/{token}/search?format=json"
                jv_res = client.get(jv_url, headers=headers)
                if jv_res.status_code == 200:
                    jv_data = jv_res.json()
                    jv_jobs = jv_data if isinstance(jv_data, list) else jv_data.get("requisitions", jv_data.get("jobs", []))
                    if jv_jobs:
                        candidates.append({
                            "found": True,
                            "source_type": "JOBVITE",
                            "board_id": token,
                            "canonical_source_url": f"https://jobs.jobvite.com/{token}",
                            "sample_jobs_count": len(jv_jobs),
                            "details": f"Verified Jobvite feed for '{token}' with {len(jv_jobs)} active listings."
                        })
            except Exception:
                pass

            # 12. Probe iCIMS
            try:
                icims_url = f"https://{token}.icims.com/jobs/search?pr=0&schema=1&in_iframe=1"
                icims_res = client.get(icims_url, headers=headers)
                if icims_res.status_code == 200 and ("iCIMS" in icims_res.text or "job" in icims_res.text.lower()):
                    candidates.append({
                        "found": True,
                        "source_type": "ICIMS",
                        "board_id": token,
                        "canonical_source_url": f"https://{token}.icims.com",
                        "sample_jobs_count": icims_res.text.count("iCIMS_JobHeader") or 1,
                        "details": f"Verified iCIMS career portal for '{token}'."
                    })
            except Exception:
                pass

        if candidates:
            # Pick candidate with highest verified active job count
            candidates.sort(key=lambda c: c["sample_jobs_count"], reverse=True)
            return candidates[0]

        return {
            "found": False,
            "source_type": None,
            "board_id": token,
            "canonical_source_url": None,
            "sample_jobs_count": 0,
            "details": f"No supported public ATS board discovered for query '{query_or_url}'."
        }

    @classmethod
    def discover_and_register_source(
        cls,
        db: Session,
        actor: User,
        company_name: str,
        query_or_url: str,
        website: Optional[str] = None,
        sync_now: bool = True
    ) -> Dict[str, Any]:
        probe_result = cls.probe_ats_board(query_or_url)
        if not probe_result["found"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=probe_result["details"]
            )

        # 1. Find or create company
        company = db.query(Company).filter(Company.canonical_name.ilike(company_name.strip())).first()
        if not company:
            company = Company(
                canonical_name=company_name.strip(),
                website=website or f"https://{probe_result['board_id']}.com",
                identity_status="VERIFIED"
            )
            db.add(company)
            db.flush()

        # 2. Check if source already exists (by company & type, or by external board ID)
        source = db.query(Source).filter(
            or_(
                Source.company_id == company.id,
                Source.external_board_id == probe_result["board_id"]
            ),
            Source.source_type == probe_result["source_type"]
        ).first()

        if not source:
            source = Source(
                company_id=company.id,
                source_name=f"{company.canonical_name} {probe_result['source_type'].capitalize()} Feed",
                source_type=probe_result["source_type"],
                canonical_source_url=probe_result["canonical_source_url"],
                external_board_id=probe_result["board_id"],
                access_classification="PUBLIC_API",
                sync_schedule_cron="0 */4 * * *",
                rate_limit_rpm=60,
                concurrency_limit=1,
                configuration={"board_name": probe_result["board_id"], "board_token": probe_result["board_id"], "company_slug": probe_result["board_id"]},
                is_active=True,
                health_status="HEALTHY"
            )
            db.add(source)
            db.flush()

        audit = AuditLog(
            actor_user_id=actor.id,
            action="DISCOVER_AND_REGISTER_SOURCE",
            target_type="SOURCE",
            target_id=str(source.id),
            details={
                "company": company.canonical_name,
                "source_type": source.source_type,
                "board_id": probe_result["board_id"]
            }
        )
        db.add(audit)
        db.commit()
        db.refresh(source)

        run_summary = None
        if sync_now:
            run = IngestionRunner.execute_sync(db, source.id)
            run_summary = {
                "run_id": run.id,
                "status": run.status,
                "records_discovered": run.records_discovered,
                "records_inserted": run.records_inserted,
                "records_updated": run.records_updated
            }

        return {
            "source_id": source.id,
            "company_name": company.canonical_name,
            "source_type": source.source_type,
            "canonical_source_url": source.canonical_source_url,
            "sample_jobs_count": probe_result["sample_jobs_count"],
            "initial_sync": run_summary
        }
