import time
import httpx
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from app.ingestion.base import SourceAdapter, NormalizedJob
from app.ingestion.normalizer import normalize_location_and_country, clean_html_markup, get_country_code

class BreezyAdapter(SourceAdapter):
    """
    Adapter for Breezy HR public career board JSON feeds:
    https://{company_slug}.breezy.hr/json
    Provides genuine direct-to-employer opportunities with canonical Breezy application URLs.
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
            if len(host_parts) >= 3 and host_parts[1] == "breezy":
                company_slug = host_parts[0]
            else:
                parts = [p for p in parsed.path.rstrip("/").split("/") if p]
                if parts:
                    company_slug = parts[-1]

        if not company_slug:
            raise ValueError("Breezy HR company_slug could not be determined from configuration or URL")

        api_url = f"https://{company_slug}.breezy.hr/json"
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
                        raise Exception(f"Breezy HR board for '{company_slug}' not found (HTTP 404)")
                    if resp.status_code == 429:
                        raise Exception("Rate limit exceeded on Breezy HR API (HTTP 429)")
                    resp.raise_for_status()
                    data = resp.json()
                    break
                except httpx.HTTPStatusError as e:
                    if e.response.status_code in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                        time.sleep(backoff_seconds)
                        backoff_seconds *= 2
                        continue
                    raise

        if not data or not isinstance(data, list):
            return [], {"completed": True}, False

        return data, {"completed": True}, False

    def parse_and_normalize(self, raw_record: Dict[str, Any]) -> Optional[NormalizedJob]:
        ext_id = str(raw_record.get("id") or "").strip()
        title = (raw_record.get("name") or "").strip()
        if not ext_id or not title:
            return None

        desc_raw = raw_record.get("description") or ""
        desc_clean = clean_html_markup(desc_raw) if desc_raw else title

        app_url = raw_record.get("url") or f"https://breezy.hr/p/{ext_id}"

        # Location extraction
        loc_obj = raw_record.get("location") or {}
        raw_location = ""
        is_remote = False
        if isinstance(loc_obj, dict):
            raw_location = loc_obj.get("name") or ""
            is_remote = bool(loc_obj.get("is_remote"))
            if not raw_location:
                city = loc_obj.get("city") or ""
                state = loc_obj.get("state") or ""
                country_dict = loc_obj.get("country") or {}
                cname = country_dict.get("name") if isinstance(country_dict, dict) else str(country_dict or "")
                parts = [p for p in [city, state, cname] if p]
                raw_location = ", ".join(parts)
        elif isinstance(loc_obj, str):
            raw_location = loc_obj

        clean_loc, city, region, country, detected_remote = normalize_location_and_country(raw_location, title)
        if is_remote or "remote" in title.lower():
            detected_remote = "REMOTE"

        # Employment type
        type_obj = raw_record.get("type") or {}
        type_str = (type_obj.get("name") or "") if isinstance(type_obj, dict) else str(type_obj)
        type_lower = type_str.lower()
        if "part" in type_lower:
            emp_type = "PART_TIME"
        elif "contract" in type_lower or "freelance" in type_lower:
            emp_type = "CONTRACT"
        elif "intern" in type_lower:
            emp_type = "INTERNSHIP"
        else:
            emp_type = "FULL_TIME"

        post_dt = None
        pub_str = raw_record.get("published_date")
        if pub_str:
            try:
                post_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
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

        # Experience level
        exp_obj = raw_record.get("experience") or {}
        exp_name = (exp_obj.get("name") or exp_obj.get("id") or "") if isinstance(exp_obj, dict) else str(exp_obj)
        exp_level = None
        exp_name_low = exp_name.lower()
        if "senior" in exp_name_low or "senior" in title.lower():
            exp_level = "SENIOR"
        elif "lead" in exp_name_low or "lead" in title.lower():
            exp_level = "LEAD"
        elif "entry" in exp_name_low or "junior" in exp_name_low:
            exp_level = "ENTRY"
        elif "mid" in exp_name_low:
            exp_level = "MID"

        # Salary
        sal_min = None
        sal_max = None
        sal_curr = "USD"
        sal_obj = raw_record.get("salary")
        if isinstance(sal_obj, dict):
            if sal_obj.get("min"):
                sal_min = float(sal_obj["min"])
            if sal_obj.get("max"):
                sal_max = float(sal_obj["max"])
            sal_curr = sal_obj.get("currency") or "USD"

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
            experience_level=exp_level,
            skills=matched_skills,
            salary_min=sal_min,
            salary_max=sal_max,
            salary_currency=sal_curr,
            posting_date=post_dt,
            application_url=app_url,
            raw_data=raw_record
        )
