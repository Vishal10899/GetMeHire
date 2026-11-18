"""
iCIMS Public Career Portal & Candidate Experience Adapter.

Ingests authentic vacancies from enterprise employers operating public iCIMS career sites.
Supported endpoints:
- JSON search feeds: https://{company}.icims.com/jobs/search?pr=0&schema=1&in_iframe=1
- Public Job Search RSS / XML / JSON API endpoints
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

class ICIMSAdapter(SourceAdapter):
    """Adapter for iCIMS enterprise applicant tracking system."""

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        company_slug = config.get("company_slug") or config.get("board_id")
        return bool(company_slug)

    def fetch_page(
        self, source_url: str, config: Dict[str, Any], checkpoint: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], bool]:
        company_slug = config.get("company_slug") or config.get("board_id")
        if not company_slug and source_url:
            match = re.search(r"https?://([a-zA-Z0-9_\-]+)\.icims\.com", source_url)
            if match:
                company_slug = match.group(1)

        if not company_slug:
            raise ValueError(f"iCIMS company slug must be configured (url={source_url})")

        checkpoint = checkpoint or {}
        page = int(checkpoint.get("page", 0))
        page_size = min(int(config.get("page_size", 50)), 100)

        api_url = f"https://{company_slug}.icims.com/jobs/search?pr={page}&schema=1&in_iframe=1"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json, text/html, */*",
        }

        try:
            with httpx.Client(timeout=15.0, follow_redirects=True) as client:
                resp = client.get(api_url, headers=headers)
                if resp.status_code == 404:
                    return [], {"page": page, "completed": True}, True
                resp.raise_for_status()

                raw_jobs = []
                content_type = resp.headers.get("content-type", "")
                if "application/json" in content_type:
                    data = resp.json()
                    raw_jobs = data if isinstance(data, list) else data.get("jobs", data.get("searchResults", []))
                else:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(resp.text, "html.parser")
                    job_elements = soup.select(".iCIMS_JobsTable .row, .job-listing, .iCIMS_JobListing")
                    for el in job_elements:
                        title_el = el.select_one(".title a, .iCIMS_JobHeader a, a.iCIMS_Anchor")
                        if not title_el:
                            continue
                        job_title = title_el.get_text(strip=True)
                        job_href = title_el.get("href", "")
                        loc_el = el.select_one(".location, .iCIMS_JobHeader .headerLocation, .iCIMS_JobData")
                        job_loc = loc_el.get_text(strip=True) if loc_el else ""
                        req_el = el.select_one(".req-id, .iCIMS_JobHeader .headerReqId")
                        req_id = req_el.get_text(strip=True) if req_el else ""

                        raw_jobs.append({
                            "title": job_title,
                            "url": job_href,
                            "location": job_loc,
                            "id": req_id or job_href,
                            "company_name": company_slug.replace("-", " ").title(),
                        })

                has_more = len(raw_jobs) >= page_size
                new_checkpoint = {
                    "page": page + 1,
                    "completed": not has_more,
                    "total_found": len(raw_jobs),
                }
                return raw_jobs, new_checkpoint, not has_more

        except httpx.HTTPStatusError as e:
            if e.response.status_code in (404, 410):
                return [], {"page": page, "completed": True}, True
            raise

    def parse_and_normalize(self, raw_record: Dict[str, Any]) -> Optional[NormalizedJob]:
        title = raw_record.get("title") or raw_record.get("job_title") or "Unknown Title"
        title = html.unescape(title).strip()

        ext_id = str(raw_record.get("id") or raw_record.get("job_id") or raw_record.get("req_id") or "")
        app_url = raw_record.get("url") or raw_record.get("application_url") or raw_record.get("job_url") or ""

        raw_loc = raw_record.get("location") or raw_record.get("job_location") or ""
        norm_loc, city, region, country, c_code, remote_type = normalize_location_full(raw_loc)

        desc = raw_record.get("description") or raw_record.get("summary") or f"{title} opportunity at {raw_record.get('company_name', 'Hiring Employer')}."
        desc = clean_html_markup(desc)

        emp_type = raw_record.get("employment_type", "FULL_TIME")

        return NormalizedJob(
            external_job_id=ext_id or f"icims-{abs(hash(title + app_url))}",
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
            employment_type=emp_type,
            application_url=app_url or f"https://careers.icims.com/jobs/{ext_id}",
            posting_date=datetime.now(timezone.utc),
            raw_data=raw_record,
        )

    def normalize(self, raw_job: Dict[str, Any], company_name: str, source_id: int) -> NormalizedJob:
        raw_job["company_name"] = company_name
        return self.parse_and_normalize(raw_job)
