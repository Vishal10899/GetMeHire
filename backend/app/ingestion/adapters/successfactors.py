"""
SAP SuccessFactors (SF) Career Site Builder Adapter.

Ingests authentic vacancies from enterprise employers operating SAP SuccessFactors recruiting portals.
Supported endpoints:
- CSB Job Search RSS feeds: https://career{instance}.successfactors.com/career?company={company}&rcm_site_locale=en_US
- CSB search JSON endpoints
"""
import re
import html
import httpx
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from app.ingestion.base import SourceAdapter, NormalizedJob
from app.ingestion.normalizer import (
    clean_html_markup,
    normalize_location_full,
    is_valid_application_url,
    get_country_code,
)

class SuccessFactorsAdapter(SourceAdapter):
    """Adapter for SAP SuccessFactors career portals."""

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        company = config.get("company") or config.get("board_id")
        return bool(company)

    def fetch_page(
        self, source_url: str, config: Dict[str, Any], checkpoint: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], bool]:
        company = config.get("company") or config.get("board_id")
        instance = config.get("instance", "4")

        if not company and source_url:
            match = re.search(r"career(\d*)\.successfactors\.com.*?company=([a-zA-Z0-9_\-]+)", source_url)
            if match:
                instance = match.group(1) or "4"
                company = match.group(2)

        if not company:
            raise ValueError(f"SuccessFactors company identifier must be configured (url={source_url})")

        checkpoint = checkpoint or {}
        if checkpoint.get("completed"):
            return [], checkpoint, True

        feed_url = f"https://career{instance}.successfactors.com/career?company={company}&rcm_site_locale=en_US&career_job_req_id="
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html, application/xml, */*",
        }

        try:
            with httpx.Client(timeout=20.0, follow_redirects=True) as client:
                resp = client.get(feed_url, headers=headers)
                if resp.status_code == 404:
                    return [], {"completed": True}, True
                resp.raise_for_status()

                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, "html.parser")
                rows = soup.select("table.jobResultsTable tr, .jobResultItem, tr.jobResult")
                raw_jobs = []

                for r in rows:
                    link_el = r.select_one("a.jobTitle, a[href*='career_job_req_id']")
                    if not link_el:
                        continue
                    j_title = link_el.get_text(strip=True)
                    j_url = link_el.get("href", "")
                    if j_url and not j_url.startswith("http"):
                        j_url = f"https://career{instance}.successfactors.com{j_url}"

                    loc_el = r.select_one(".jobLocation, td.colLocation")
                    j_loc = loc_el.get_text(strip=True) if loc_el else ""

                    req_match = re.search(r"career_job_req_id=(\d+)", j_url)
                    req_id = req_match.group(1) if req_match else j_url

                    raw_jobs.append({
                        "title": j_title,
                        "url": j_url,
                        "location": j_loc,
                        "id": req_id,
                        "company_name": company.replace("-", " ").title(),
                    })

                return raw_jobs, {"completed": True, "total_found": len(raw_jobs)}, True

        except httpx.HTTPStatusError as e:
            if e.response.status_code in (404, 410):
                return [], {"completed": True}, True
            raise

    def parse_and_normalize(self, raw_record: Dict[str, Any]) -> Optional[NormalizedJob]:
        title = raw_record.get("title") or "Unknown Title"
        title = html.unescape(title).strip()

        ext_id = str(raw_record.get("id") or "")
        app_url = raw_record.get("url") or ""

        raw_loc = raw_record.get("location") or ""
        norm_loc, city, region, country, c_code, remote_type = normalize_location_full(raw_loc)

        desc = raw_record.get("description") or f"{title} position at {raw_record.get('company_name', 'Hiring Employer')}."
        desc = clean_html_markup(desc)

        return NormalizedJob(
            external_job_id=ext_id or f"sf-{abs(hash(title + app_url))}",
            title=title,
            description=desc,
            company_name=raw_record.get("company_name"),
            location=norm_loc,
            city=city,
            region=region,
            country=country,
            country_code=c_code,
            remote_type=remote_type,
            work_arrangement=remote_type,
            remote_eligibility="NOT_REMOTE" if remote_type == "ONSITE" else "EMPLOYER_DEFINED",
            employment_type="FULL_TIME",
            application_url=app_url or f"https://successfactors.com/jobs/{ext_id}",
            posting_date=datetime.now(timezone.utc),
            raw_data=raw_record,
        )

    def normalize(self, raw_job: Dict[str, Any], company_name: str, source_id: int) -> NormalizedJob:
        raw_job["company_name"] = company_name
        return self.parse_and_normalize(raw_job)
