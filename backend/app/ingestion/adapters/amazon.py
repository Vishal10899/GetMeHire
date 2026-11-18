"""
Amazon Jobs Public Search API Adapter.

Ingests authentic vacancies from Amazon's official public jobs search API:
https://www.amazon.jobs/en/search.json

Extracts:
- Canonical job title & description
- Standardized city, state, and country (e.g. Bengaluru, Hyderabad, Chennai, India)
- Direct application URL to Amazon Jobs portal
- Requisition ID and posted date
"""
import re
import html
import time
import httpx
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from app.ingestion.base import SourceAdapter, NormalizedJob
from app.ingestion.normalizer import (
    clean_html_markup,
    normalize_location_full,
    is_valid_application_url,
)

class AmazonJobsAdapter(SourceAdapter):
    """Adapter for Amazon's public careers search API."""

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        # Configuration is optional; defaults to India (country=IND)
        return True

    def fetch_page(
        self, source_url: str, config: Dict[str, Any], checkpoint: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], bool]:
        checkpoint = checkpoint or {}
        offset = int(checkpoint.get("offset", 0))
        limit = int(config.get("result_limit", 25))
        country = config.get("country", "IND")
        city = config.get("city")
        search_query = config.get("search_query")

        base_url = "https://www.amazon.jobs/en/search.json"
        params: Dict[str, Any] = {
            "country": country,
            "result_limit": limit,
            "offset": offset,
            "sort": "recent",
        }
        if city:
            params["city"] = city
        if search_query:
            params["base_query"] = search_query

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
        }

        client_timeout = httpx.Timeout(25.0, connect=10.0)
        data = None

        with httpx.Client(timeout=client_timeout) as client:
            for attempt in range(3):
                try:
                    resp = client.get(base_url, params=params, headers=headers)
                    if resp.status_code == 429:
                        time.sleep(2.0 * (attempt + 1))
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    break
                except httpx.HTTPStatusError as e:
                    if e.response.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                        time.sleep(2.0 * (attempt + 1))
                        continue
                    raise

        if not data:
            return [], checkpoint, False

        jobs = data.get("jobs", [])
        total_hits = data.get("hits", 0)
        next_offset = offset + len(jobs)
        has_more = next_offset < total_hits and len(jobs) > 0

        next_checkpoint = {
            "offset": next_offset,
            "total_hits": total_hits,
            "last_crawled_at": datetime.now(timezone.utc).isoformat(),
        }

        return jobs, next_checkpoint, has_more

    def parse_and_normalize(self, raw_record: Dict[str, Any]) -> Optional[NormalizedJob]:
        try:
            external_id = str(raw_record.get("id_icims") or raw_record.get("id") or "")
            if not external_id:
                return None

            title = (raw_record.get("title") or "").strip()
            if not title:
                return None

            job_path = raw_record.get("job_path") or f"/en/jobs/{external_id}"
            app_url = f"https://www.amazon.jobs{job_path}"
            is_valid, _ = is_valid_application_url(app_url)
            if not is_valid:
                return None

            raw_desc = raw_record.get("description") or raw_record.get("basic_qualifications") or "Amazon genuine vacancy."
            clean_desc = clean_html_markup(raw_desc)

            raw_city = raw_record.get("city") or ""
            raw_loc = raw_record.get("location") or raw_city or "India"
            config_country = raw_record.get("country_code") or "IND"

            # In Amazon India search, location format is "IN, {StateCode}, {City}" (e.g. IN, TN, Tiruvallur)
            if raw_loc.startswith("IN,") or raw_record.get("country_code") == "IND" or config_country == "IND":
                parts = [p.strip() for p in raw_loc.split(",") if p.strip()]
                extracted_city = raw_city
                if (not extracted_city or extracted_city == "IN") and len(parts) >= 3:
                    extracted_city = parts[2]
                elif (not extracted_city or extracted_city == "IN") and len(parts) == 2:
                    extracted_city = parts[1]

                clean_loc, city, region, _, _, remote_type = normalize_location_full(
                    extracted_city or raw_loc, title
                )
                country = "India"
                country_code = "IN"
                city = city or extracted_city or (parts[-1] if parts else "Bengaluru")
            else:
                clean_loc, city, region, country, country_code, remote_type = normalize_location_full(
                    raw_loc, title
                )
                if not country:
                    country = "India"
                    country_code = "IN"

            # Parse posting date
            posted_dt = None
            posted_str = raw_record.get("posted_date")
            if posted_str:
                for fmt in ("%B %d, %Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ"):
                    try:
                        posted_dt = datetime.strptime(posted_str.split("T")[0], "%Y-%m-%d")
                        break
                    except Exception:
                        pass

            # Department / Job Category
            dept = raw_record.get("job_category") or raw_record.get("business_category")

            return NormalizedJob(
                external_job_id=external_id,
                title=title,
                description=clean_desc,
                company_name="Amazon",
                department=dept,
                location=clean_loc or "Bengaluru, India",
                city=city or raw_city or "Bengaluru",
                region=region,
                country=country or "India",
                country_code=country_code or "IN",
                remote_type=remote_type,
                employment_type="FULL_TIME",
                posting_date=posted_dt,
                application_url=app_url,
                raw_data=raw_record,
            )
        except Exception:
            return None

    def classify_error(self, exc: Exception) -> str:
        if isinstance(exc, httpx.HTTPStatusError):
            code = exc.response.status_code
            if code in (429, 502, 503, 504):
                return "TRANSIENT"
            if code in (401, 403):
                return "AUTH"
            if code == 404:
                return "NOT_FOUND"
        if isinstance(exc, (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.NetworkError)):
            return "TRANSIENT"
        return "UNKNOWN"
