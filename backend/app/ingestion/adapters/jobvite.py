"""
Jobvite Public Career Feed Adapter.

Ingests authentic vacancies from enterprise employers operating Jobvite career portals.
Supported endpoints:
- JSON feeds: https://jobs.jobvite.com/{company}/search?format=json
- XML/RSS feeds: https://jobs.jobvite.com/{company}/jobs.rss
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

class JobviteAdapter(SourceAdapter):
    """Adapter for Jobvite career platform."""

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        company_slug = config.get("company_slug") or config.get("board_id")
        return bool(company_slug)

    def fetch_page(
        self, source_url: str, config: Dict[str, Any], checkpoint: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], bool]:
        company_slug = config.get("company_slug") or config.get("board_id")
        if not company_slug and source_url:
            match = re.search(r"https?://jobs\.jobvite\.com/([a-zA-Z0-9_\-]+)", source_url)
            if match:
                company_slug = match.group(1)

        if not company_slug:
            raise ValueError(f"Jobvite company slug must be configured (url={source_url})")

        checkpoint = checkpoint or {}
        if checkpoint.get("completed"):
            return [], checkpoint, True

        api_url = f"https://jobs.jobvite.com/{company_slug}/search?format=json"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json, text/xml, */*",
        }

        try:
            with httpx.Client(timeout=15.0, follow_redirects=True) as client:
                resp = client.get(api_url, headers=headers)
                if resp.status_code == 404:
                    return [], {"completed": True}, True
                resp.raise_for_status()

                raw_jobs = []
                try:
                    data = resp.json()
                    raw_jobs = data if isinstance(data, list) else data.get("requisitions", data.get("jobs", []))
                except Exception:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(resp.text, "xml")
                    items = soup.find_all("item")
                    for item in items:
                        t = item.find("title")
                        l = item.find("link")
                        d = item.find("description")
                        loc = item.find("location") or item.find("jobLocation")
                        raw_jobs.append({
                            "title": t.get_text(strip=True) if t else "Untitled",
                            "url": l.get_text(strip=True) if l else "",
                            "description": d.get_text(strip=True) if d else "",
                            "location": loc.get_text(strip=True) if loc else "",
                            "id": (l.get_text(strip=True) if l else "").split("/")[-1],
                            "company_name": company_slug.replace("-", " ").title(),
                        })

                return raw_jobs, {"completed": True, "total_found": len(raw_jobs)}, True

        except httpx.HTTPStatusError as e:
            if e.response.status_code in (404, 410):
                return [], {"completed": True}, True
            raise

    def parse_and_normalize(self, raw_record: Dict[str, Any]) -> Optional[NormalizedJob]:
        title = raw_record.get("title") or raw_record.get("job_title") or "Unknown Title"
        title = html.unescape(title).strip()

        ext_id = str(raw_record.get("id") or raw_record.get("eId") or raw_record.get("requisitionId") or "")
        app_url = raw_record.get("url") or raw_record.get("jobUrl") or raw_record.get("detailUrl") or ""
        if not app_url and ext_id:
            app_url = f"https://jobs.jobvite.com/job/{ext_id}"

        raw_loc = raw_record.get("location") or raw_record.get("cityState") or ""
        norm_loc, city, region, country, c_code, remote_type = normalize_location_full(raw_loc)

        desc = raw_record.get("description") or raw_record.get("jobDescription") or f"{title} vacancy."
        desc = clean_html_markup(desc)

        emp_type = raw_record.get("jobType") or raw_record.get("employment_type") or "FULL_TIME"
        if "contract" in str(emp_type).lower():
            emp_type = "CONTRACT"
        elif "part" in str(emp_type).lower():
            emp_type = "PART_TIME"
        elif "intern" in str(emp_type).lower():
            emp_type = "INTERNSHIP"
        else:
            emp_type = "FULL_TIME"

        return NormalizedJob(
            external_job_id=ext_id or f"jobvite-{abs(hash(title + app_url))}",
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
            application_url=app_url,
            posting_date=datetime.now(timezone.utc),
            raw_data=raw_record,
        )

    def normalize(self, raw_job: Dict[str, Any], company_name: str, source_id: int) -> NormalizedJob:
        raw_job["company_name"] = company_name
        return self.parse_and_normalize(raw_job)
