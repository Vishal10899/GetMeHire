import time
import httpx
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from app.ingestion.base import SourceAdapter, NormalizedJob
from app.ingestion.normalizer import normalize_location_and_country, clean_html_markup, get_country_code

class BambooHRAdapter(SourceAdapter):
    """
    Adapter for BambooHR public careers list API:
    https://{company_slug}.bamboohr.com/careers/list
    Provides authentic job vacancy listings with official BambooHR application links.
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
            if len(host_parts) >= 3 and host_parts[1] == "bamboohr":
                company_slug = host_parts[0]
            else:
                parts = [p for p in parsed.path.rstrip("/").split("/") if p]
                if parts:
                    company_slug = parts[-1]

        if not company_slug:
            raise ValueError("BambooHR company_slug could not be determined from configuration or URL")

        api_url = f"https://{company_slug}.bamboohr.com/careers/list"
        headers = {
            "User-Agent": "GetMeHirePlatform/2.0 (+https://getmehire.com/bot; permitted indexer)",
            "Accept": "application/json",
        }

        max_retries = 3
        backoff_seconds = 1.0
        data = None

        with httpx.Client(timeout=25.0, follow_redirects=True) as client:
            for attempt in range(max_retries):
                try:
                    resp = client.get(api_url, headers=headers)
                    if resp.status_code == 404:
                        raise Exception(f"BambooHR board for '{company_slug}' not found (HTTP 404)")
                    if str(resp.url).rstrip("/") in ["https://www.bamboohr.com", "http://www.bamboohr.com"]:
                        return [], {"completed": True}, False
                    if resp.status_code == 429:
                        raise Exception("Rate limit exceeded on BambooHR API (HTTP 429)")
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

        records = data.get("result", [])
        # Attach company_slug for URL derivation in parse_and_normalize
        for r in records:
            r["_company_slug"] = company_slug

        return records, {"completed": True}, False

    def parse_and_normalize(self, raw_record: Dict[str, Any]) -> Optional[NormalizedJob]:
        ext_id = str(raw_record.get("id") or "").strip()
        title = (raw_record.get("jobOpeningName") or raw_record.get("title") or "").strip()
        if not ext_id or not title:
            return None

        company_slug = raw_record.get("_company_slug") or "careers"
        app_url = f"https://{company_slug}.bamboohr.com/careers/{ext_id}"

        # Location extraction
        loc_obj = raw_record.get("location") or {}
        raw_location = ""
        if isinstance(loc_obj, dict):
            parts = [
                str(loc_obj.get("city") or "").strip(),
                str(loc_obj.get("state") or "").strip(),
                str(loc_obj.get("country") or "").strip()
            ]
            raw_location = ", ".join([p for p in parts if p])
        elif isinstance(loc_obj, str):
            raw_location = loc_obj

        clean_loc, city, region, country, detected_remote = normalize_location_and_country(raw_location, title)

        loc_type = str(raw_record.get("locationType") or "").lower()
        if "remote" in loc_type or "remote" in title.lower():
            detected_remote = "REMOTE"
        elif "hybrid" in loc_type:
            detected_remote = "HYBRID"

        emp_type_str = str(raw_record.get("employmentType") or "").lower()
        if "part" in emp_type_str:
            emp_type = "PART_TIME"
        elif "contract" in emp_type_str or "temporary" in emp_type_str:
            emp_type = "CONTRACT"
        elif "intern" in emp_type_str:
            emp_type = "INTERNSHIP"
        else:
            emp_type = "FULL_TIME"

        desc = raw_record.get("jobDescription") or raw_record.get("description") or f"{title} position at {company_slug}."

        import re
        desc_clean = clean_html_markup(desc)
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

        # Parse compensation
        sal_min = None
        sal_max = None
        sal_curr = "USD"
        comp_str = str(raw_record.get("compensation") or "")
        if comp_str:
            if "cad" in comp_str.lower():
                sal_curr = "CAD"
            elif "eur" in comp_str.lower() or "€" in comp_str:
                sal_curr = "EUR"
            elif "gbp" in comp_str.lower() or "£" in comp_str:
                sal_curr = "GBP"
            matches = re.findall(r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)", comp_str)
            clean_nums = []
            for m in matches:
                try:
                    num = float(m.replace(",", ""))
                    if num > 100:
                        clean_nums.append(num)
                except ValueError:
                    pass
            if clean_nums:
                sal_min = clean_nums[0]
                if len(clean_nums) > 1:
                    sal_max = clean_nums[1]

        return NormalizedJob(
            external_job_id=ext_id,
            title=title,
            description=desc_clean,
            department=raw_record.get("departmentLabel") or raw_record.get("department"),
            location=clean_loc or "Unspecified",
            city=city,
            region=region,
            country=country,
            country_code=get_country_code(country),
            remote_type=detected_remote,
            employment_type=emp_type,
            skills=matched_skills,
            salary_min=sal_min,
            salary_max=sal_max,
            salary_currency=sal_curr,
            posting_date=None,
            application_url=app_url,
            raw_data=raw_record
        )
