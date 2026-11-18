"""
Workday Candidate Experience Service (CXS) Adapter.

Ingests authentic vacancies from enterprise employers operating public Workday career sites.
Supported endpoints:
POST https://{tenant}.{wd_num}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs

Extracts:
- Requisition identifier & job title
- Workday externalPath application destination
- Standardized city, state, and country
- Pagination offset and total postings count
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

class WorkdayAdapter(SourceAdapter):
    """Adapter for Workday public candidate experience (CXS) search endpoints."""

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        tenant = config.get("tenant") or config.get("board_id")
        site = config.get("site") or config.get("career_site")
        return bool(tenant and site)

    def fetch_page(
        self, source_url: str, config: Dict[str, Any], checkpoint: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], bool]:
        tenant = config.get("tenant") or config.get("board_id")
        wd_num = config.get("wd_num", "wd1")
        site = config.get("site") or config.get("career_site")

        # Parse from source_url if not explicitly configured
        # e.g. https://salesforce.wd12.myworkdayjobs.com/External_Career_Site
        if source_url and (not tenant or not site):
            match = re.search(r"https?://([a-zA-Z0-9_\-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:en-US/)?([a-zA-Z0-9_\-]+)", source_url)
            if match:
                tenant = tenant or match.group(1)
                wd_num = match.group(2)
                site = site or match.group(3)

        if not tenant or not site:
            raise ValueError(f"Workday tenant and site must be configured (tenant={tenant}, site={site})")

        checkpoint = checkpoint or {}
        offset = int(checkpoint.get("offset", 0))
        limit = min(int(config.get("limit", 20)), 50)
        search_text = config.get("search_text", "India")

        api_url = f"https://{tenant}.{wd_num}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
        payload = {
            "appliedFacets": config.get("appliedFacets", {}),
            "limit": limit,
            "offset": offset,
            "searchText": search_text,
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": f"https://{tenant}.{wd_num}.myworkdayjobs.com",
            "Referer": f"https://{tenant}.{wd_num}.myworkdayjobs.com/{site}",
        }

        client_timeout = httpx.Timeout(30.0, connect=10.0)
        data = None

        with httpx.Client(timeout=client_timeout) as client:
            for attempt in range(3):
                try:
                    resp = client.post(api_url, json=payload, headers=headers)
                    if resp.status_code == 429:
                        # Workday rate limit encountered; back off
                        time.sleep(3.0 * (attempt + 1))
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    break
                except httpx.HTTPStatusError as e:
                    if e.response.status_code in (429, 502, 503, 504) and attempt < 2:
                        time.sleep(3.0 * (attempt + 1))
                        continue
                    raise

        if not data:
            return [], checkpoint, False

        jobs = data.get("jobPostings", [])
        total = data.get("total", 0)
        next_offset = offset + len(jobs)
        has_more = next_offset < total and len(jobs) > 0

        # Attach tenant/site metadata to raw records for URL construction
        for j in jobs:
            j["_tenant"] = tenant
            j["_wd_num"] = wd_num
            j["_site"] = site

        next_checkpoint = {
            "offset": next_offset,
            "total": total,
            "last_crawled_at": datetime.now(timezone.utc).isoformat(),
        }

        return jobs, next_checkpoint, has_more

    def parse_and_normalize(self, raw_record: Dict[str, Any]) -> Optional[NormalizedJob]:
        try:
            external_path = raw_record.get("externalPath") or ""
            # Extract req id from externalPath (e.g. /job/.../Title_JR12345 -> JR12345)
            external_id = None
            if "_" in external_path:
                external_id = external_path.split("_")[-1].strip("/")
            if not external_id and raw_record.get("bulletFields"):
                external_id = str(raw_record["bulletFields"][0])
            if not external_id:
                external_id = external_path.strip("/").replace("/", "-")
            if not external_id:
                return None

            title = (raw_record.get("title") or "").strip()
            if not title:
                return None

            tenant = raw_record.get("_tenant", "workday")
            wd_num = raw_record.get("_wd_num", "wd1")
            site = raw_record.get("_site", "External")

            app_url = f"https://{tenant}.{wd_num}.myworkdayjobs.com/en-US/{site}{external_path}"
            is_valid, _ = is_valid_application_url(app_url)
            if not is_valid:
                return None

            raw_loc = raw_record.get("locationsText") or "India"
            clean_loc, city, region, country, country_code, remote_type = normalize_location_full(
                raw_loc, title
            )
            if not country and "india" in raw_loc.lower():
                country = "India"
                country_code = "IN"

            posted_str = raw_record.get("postedOn") or ""

            return NormalizedJob(
                external_job_id=external_id,
                title=title,
                description=f"Authentic posting from {tenant.title()} enterprise career portal. Location: {raw_loc}.",
                company_name=tenant.title(),
                location=clean_loc or raw_loc,
                city=city,
                region=region,
                country=country or "India",
                country_code=country_code or "IN",
                remote_type=remote_type,
                employment_type="FULL_TIME",
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
