import time
import httpx
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from bs4 import BeautifulSoup
from app.ingestion.base import SourceAdapter, NormalizedJob
from app.ingestion.normalizer import normalize_location_and_country

class WorkableAdapter(SourceAdapter):
    """
    Adapter for Workable public job board feeds.
    Fetches job listings from Workable's public widget API:
    https://apply.workable.com/api/v1/widget/accounts/{company_slug}
    and enriches with full job details from:
    https://apply.workable.com/api/v2/accounts/{company_slug}/jobs/{shortcode}
    """

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        return bool(config.get("company_slug") or config.get("account_slug") or config.get("board_url"))

    def fetch_page(
        self, source_url: str, config: Dict[str, Any], checkpoint: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], bool]:
        company_slug = config.get("company_slug") or config.get("account_slug")
        if not company_slug and source_url:
            # e.g., https://apply.workable.com/arondite/ -> arondite
            parts = [p for p in source_url.rstrip("/").split("/") if p]
            if parts:
                company_slug = parts[-1]

        if not company_slug:
            raise ValueError("Workable company_slug could not be determined from configuration or URL")

        api_url = f"https://apply.workable.com/api/v1/widget/accounts/{company_slug}"
        headers = {
            "User-Agent": "GetMeHirePlatform/2.0 (+https://getmehire.com/bot; permitted indexer)",
            "Accept": "application/json",
        }
        client_timeout = httpx.Timeout(30.0, connect=10.0)

        # Execute with retry and exponential backoff
        max_retries = 3
        backoff_seconds = 1.0
        data = None

        with httpx.Client(timeout=client_timeout) as client:
            for attempt in range(max_retries):
                try:
                    resp = client.get(api_url, headers=headers)
                    if resp.status_code == 404:
                        raise Exception(f"Workable account '{company_slug}' not found (HTTP 404)")
                    if resp.status_code == 429:
                        raise Exception("Rate limit exceeded on Workable API (HTTP 429)")
                    resp.raise_for_status()
                    data = resp.json()
                    break
                except httpx.HTTPStatusError as e:
                    if e.response.status_code in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                        time.sleep(backoff_seconds)
                        backoff_seconds *= 2
                        continue
                    raise

            if not data or not isinstance(data, dict):
                return [], {"completed": True}, False

            raw_jobs = data.get("jobs", [])
            enriched_jobs = []

            # Enrich jobs with details if needed
            fetch_details = config.get("fetch_details", True)
            max_details = int(config.get("max_details", 250))
            for idx, job_item in enumerate(raw_jobs):
                shortcode = job_item.get("shortcode")
                if fetch_details and shortcode and idx < max_details:
                    detail_url = f"https://apply.workable.com/api/v2/accounts/{company_slug}/jobs/{shortcode}"
                    try:
                        time.sleep(0.04)  # Polite throttle
                        d_resp = client.get(detail_url, headers=headers)
                        if d_resp.status_code == 200:
                            detail_data = d_resp.json()
                            job_item["detail"] = detail_data
                    except Exception:
                        pass  # Fail gracefully to base item
                enriched_jobs.append(job_item)

        return enriched_jobs, {"completed": True}, False

    def parse_and_normalize(self, raw_record: Dict[str, Any]) -> Optional[NormalizedJob]:
        try:
            external_id = str(raw_record.get("shortcode") or raw_record.get("id") or "").strip()
            title = (raw_record.get("title") or "").strip()
            if not external_id or not title:
                return None

            detail = raw_record.get("detail", {})

            # Construct clean description from detail or fallback
            desc_html_parts = []
            if detail:
                if detail.get("description"):
                    desc_html_parts.append(detail["description"])
                if detail.get("requirements"):
                    desc_html_parts.append(f"<h3>Requirements</h3>{detail['requirements']}")
                if detail.get("benefits"):
                    desc_html_parts.append(f"<h3>Benefits</h3>{detail['benefits']}")
            elif raw_record.get("description"):
                desc_html_parts.append(raw_record["description"])

            combined_html = "\n".join(desc_html_parts)
            if combined_html:
                soup = BeautifulSoup(combined_html, "html.parser")
                clean_desc = soup.get_text(separator="\n").strip()
            else:
                clean_desc = f"Open position for {title}."

            # Department
            dept = raw_record.get("department")
            if isinstance(dept, list) and dept:
                dept_name = str(dept[0])
            elif isinstance(dept, str):
                dept_name = dept
            else:
                dept_name = detail.get("department")
                if isinstance(dept_name, list) and dept_name:
                    dept_name = str(dept_name[0])

            # Location and country resolution
            loc_data = detail.get("location") or {}
            city = loc_data.get("city") or raw_record.get("city")
            region = loc_data.get("region") or raw_record.get("state")
            country_val = loc_data.get("country") or raw_record.get("country")

            loc_str_candidates = [c for c in [city, region, country_val] if c]
            location_str = ", ".join(loc_str_candidates) if loc_str_candidates else "Worldwide"

            norm_loc, norm_city, norm_region, norm_country, detected_remote = normalize_location_and_country(
                location_str, title
            )

            # Remote / Workplace determination
            workplace = (detail.get("workplace") or raw_record.get("workplace") or "").lower()
            telecommuting = raw_record.get("telecommuting") or detail.get("remote")

            remote_type = detected_remote
            if "remote" in workplace or telecommuting is True:
                remote_type = "REMOTE"
            elif "hybrid" in workplace and remote_type != "REMOTE":
                remote_type = "HYBRID"

            # Employment type
            raw_emp = (raw_record.get("employment_type") or detail.get("employment_type") or "FULL_TIME").upper()
            emp_type = "FULL_TIME"
            if "PART" in raw_emp:
                emp_type = "PART_TIME"
            elif "CONTRACT" in raw_emp or "FREELANCE" in raw_emp:
                emp_type = "CONTRACT"
            elif "INTERN" in raw_emp:
                emp_type = "INTERNSHIP"

            # Application URL preservation
            app_url = (
                raw_record.get("application_url")
                or raw_record.get("url")
                or f"https://apply.workable.com/j/{external_id}/apply"
            )

            # Posting date
            date_str = raw_record.get("published_on") or raw_record.get("created_at") or detail.get("published")
            posting_dt = datetime.utcnow()
            if date_str:
                try:
                    posting_dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                except Exception:
                    posting_dt = datetime.utcnow()

            # Taxonomy skills extraction
            tech_skills = [
                "python", "react", "fastapi", "django", "node", "typescript", "javascript",
                "aws", "docker", "kubernetes", "sql", "postgres", "golang", "java", "ruby",
                "ai", "machine learning", "product", "sales", "marketing", "devops"
            ]
            matched_skills = [s.capitalize() for s in tech_skills if s in clean_desc.lower() or s in title.lower()]

            return NormalizedJob(
                external_job_id=external_id,
                title=title,
                description=clean_desc,
                department=dept_name,
                location=norm_loc,
                city=norm_city or city,
                region=norm_region or region,
                country=norm_country or country_val,
                remote_type=remote_type,
                employment_type=emp_type,
                experience_level="SENIOR" if "senior" in title.lower() else "MID",
                skills=matched_skills,
                posting_date=posting_dt,
                application_url=app_url,
                raw_data=raw_record,
            )
        except Exception:
            return None
