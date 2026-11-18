"""
University, Academic & Higher Education Career Adapter.

Ingests authentic vacancies from universities, academic institutions, and public research centers.
Normalizes academic professorships, research grants, postdocs, and university staff roles.
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

class UniversityCareersAdapter(SourceAdapter):
    """Adapter for universities, colleges, and research institutions."""

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        return bool(config.get("feed_url") or config.get("university_slug") or config.get("api_endpoint"))

    def fetch_page(
        self, source_url: str, config: Dict[str, Any], checkpoint: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], bool]:
        feed_url = config.get("feed_url") or config.get("api_endpoint") or source_url
        if not feed_url:
            raise ValueError("University Careers feed URL must be provided")

        checkpoint = checkpoint or {}
        if checkpoint.get("completed"):
            return [], checkpoint, True

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json, application/xml, text/html, */*",
        }

        try:
            with httpx.Client(timeout=20.0, follow_redirects=True) as client:
                resp = client.get(feed_url, headers=headers)
                if resp.status_code == 404:
                    return [], {"completed": True}, True
                resp.raise_for_status()

                raw_jobs = []
                content_type = resp.headers.get("content-type", "")
                if "application/json" in content_type:
                    data = resp.json()
                    raw_jobs = data if isinstance(data, list) else data.get("jobs", data.get("positions", []))
                else:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(resp.text, "html.parser")
                    items = soup.select(".job-row, .academic-job, .position-item, tr.job-item, .career-listing")
                    for el in items:
                        title_el = el.select_one("a.job-title, a.title, .jobTitle a, h3 a, h2 a")
                        if not title_el:
                            continue
                        j_title = title_el.get_text(strip=True)
                        j_url = title_el.get("href", "")
                        loc_el = el.select_one(".location, .campus, .facility")
                        j_loc = loc_el.get_text(strip=True) if loc_el else ""
                        dept_el = el.select_one(".department, .faculty, .school")
                        j_dept = dept_el.get_text(strip=True) if dept_el else "Higher Education"

                        raw_jobs.append({
                            "title": j_title,
                            "url": j_url,
                            "location": j_loc,
                            "department": j_dept,
                            "id": j_url.split("/")[-1] or str(abs(hash(j_title))),
                        })

                return raw_jobs, {"completed": True, "total_found": len(raw_jobs)}, True

        except httpx.HTTPStatusError as e:
            if e.response.status_code in (404, 410):
                return [], {"completed": True}, True
            raise

    def parse_and_normalize(self, raw_record: Dict[str, Any]) -> Optional[NormalizedJob]:
        title = raw_record.get("title") or "Academic Researcher"
        title = html.unescape(title).strip()

        ext_id = str(raw_record.get("id") or "")
        app_url = raw_record.get("url") or ""

        raw_loc = raw_record.get("location") or raw_record.get("campus") or ""
        norm_loc, city, region, country, c_code, remote_type = normalize_location_full(raw_loc)

        desc = raw_record.get("description") or f"{title} faculty/research opportunity at {raw_record.get('company_name', 'University')}."
        desc = clean_html_markup(desc)

        emp_type = "FULL_TIME"
        if "postdoc" in title.lower() or "fellow" in title.lower():
            emp_type = "FIXED_TERM"
        elif "adjunct" in title.lower() or "part" in str(raw_record.get("employment_type", "")).lower():
            emp_type = "PART_TIME"

        return NormalizedJob(
            external_job_id=ext_id or f"acad-{abs(hash(title + app_url))}",
            title=title,
            description=desc,
            company_name=raw_record.get("company_name"),
            location=norm_loc,
            city=city,
            region=region,
            country=country,
            country_code=c_code,
            remote_type=remote_type,
            work_arrangement="ONSITE" if remote_type == "ONSITE" else remote_type,
            remote_eligibility="NOT_REMOTE" if remote_type == "ONSITE" else "EMPLOYER_DEFINED",
            employment_type=emp_type,
            application_url=app_url or f"https://academicjobs.org/position/{ext_id}",
            posting_date=datetime.now(timezone.utc),
            raw_data=raw_record,
        )

    def normalize(self, raw_job: Dict[str, Any], company_name: str, source_id: int) -> NormalizedJob:
        raw_job["company_name"] = company_name
        return self.parse_and_normalize(raw_job)
