import time
import httpx
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from bs4 import BeautifulSoup
from app.ingestion.base import SourceAdapter, NormalizedJob
from app.ingestion.normalizer import normalize_location_and_country, clean_html_markup, get_country_code

class RecruiteeAdapter(SourceAdapter):
    """
    Adapter for Recruitee public careers API:
    https://{company_slug}.recruitee.com/api/offers/
    Provides structured vacancy listings with authentic employer application URLs.
    """

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        return bool(config.get("company_slug") or config.get("board_url"))

    def fetch_page(
        self, source_url: str, config: Dict[str, Any], checkpoint: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], bool]:
        company_slug = config.get("company_slug")
        if not company_slug and source_url:
            import urllib.parse
            parsed = urllib.parse.urlparse(source_url)
            host_parts = parsed.netloc.split(".")
            if len(host_parts) >= 3 and host_parts[1] == "recruitee":
                company_slug = host_parts[0]
            else:
                parts = [p for p in parsed.path.rstrip("/").split("/") if p]
                if parts:
                    company_slug = parts[-1]

        if not company_slug:
            raise ValueError("Recruitee company_slug could not be determined from configuration or URL")

        api_url = f"https://{company_slug}.recruitee.com/api/offers/"
        headers = {
            "User-Agent": "GetMeHirePlatform/2.0 (+https://getmehire.com/bot; permitted indexer)",
            "Accept": "application/json",
        }

        max_retries = 3
        backoff_seconds = 1.0
        data = None

        with httpx.Client(timeout=25.0) as client:
            for attempt in range(max_retries):
                try:
                    resp = client.get(api_url, headers=headers)
                    if resp.status_code == 404:
                        raise Exception(f"Recruitee board for '{company_slug}' not found (HTTP 404)")
                    if resp.status_code == 429:
                        raise Exception("Rate limit exceeded on Recruitee API (HTTP 429)")
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

        offers = data.get("offers", [])
        return offers, {"completed": True}, False

    def parse_and_normalize(self, raw_record: Dict[str, Any]) -> Optional[NormalizedJob]:
        ext_id = str(raw_record.get("id") or "").strip()
        title = (raw_record.get("title") or "").strip()
        if not ext_id or not title:
            return None

        desc_raw = raw_record.get("description") or raw_record.get("requirements") or ""
        desc_clean = clean_html_markup(desc_raw) if desc_raw else title

        # Application URL: prefer careers_url or fallback to standard public offer URL
        app_url = raw_record.get("careers_url")
        if not app_url:
            slug = raw_record.get("slug") or ext_id
            app_url = f"https://careers.recruitee.com/o/{slug}"

        loc_parts = []
        if raw_record.get("city"):
            loc_parts.append(str(raw_record.get("city")).strip())
        if raw_record.get("state"):
            loc_parts.append(str(raw_record.get("state")).strip())
        if raw_record.get("country"):
            loc_parts.append(str(raw_record.get("country")).strip())
        
        raw_location = ", ".join(loc_parts) if loc_parts else raw_record.get("location")
        clean_loc, city, region, country, detected_remote = normalize_location_and_country(raw_location, title)

        if raw_record.get("remote") is True or "remote" in title.lower():
            detected_remote = "REMOTE"

        # Employment type mapping
        emp_code = str(raw_record.get("employment_type_code") or "").lower()
        if "full" in emp_code:
            emp_type = "FULL_TIME"
        elif "part" in emp_code:
            emp_type = "PART_TIME"
        elif "contract" in emp_code or "freelance" in emp_code:
            emp_type = "CONTRACT"
        elif "intern" in emp_code:
            emp_type = "INTERNSHIP"
        else:
            emp_type = "FULL_TIME"

        post_dt = None
        created_str = raw_record.get("created_at")
        if created_str:
            try:
                post_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            except Exception:
                pass

        import re
        desc_lower = (desc_clean or "").lower()
        title_lower = title.lower()
        keywords_to_check = ["python", "react", "fastapi", "django", "node", "typescript", "aws", "docker", "kubernetes", "sql", "postgresql", "postgres", "go", "golang", "java", "c++", "rust", "linux", "terraform"]
        matched_skills = []
        for k in keywords_to_check:
            if k == "go":
                if re.search(r"\bgo\b", desc_lower) or re.search(r"\bgo\b", title_lower):
                    matched_skills.append("Go")
            elif k in ("postgresql", "postgres"):
                if "postgres" in desc_lower or "postgres" in title_lower:
                    if "Postgresql" not in matched_skills:
                        matched_skills.append("Postgresql")
            elif k in desc_lower or k in title_lower:
                cap = k.capitalize()
                if cap not in matched_skills:
                    matched_skills.append(cap)

        return NormalizedJob(
            external_job_id=ext_id,
            title=title,
            description=desc_clean,
            department=raw_record.get("department"),
            location=clean_loc or "Unspecified",
            city=city,
            region=region,
            country=country,
            country_code=get_country_code(country),
            remote_type=detected_remote,
            employment_type=emp_type,
            skills=matched_skills,
            posting_date=post_dt,
            application_url=app_url,
            raw_data=raw_record
        )
