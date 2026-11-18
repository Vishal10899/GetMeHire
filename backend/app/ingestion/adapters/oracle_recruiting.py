"""
Oracle Recruiting Cloud (ORC) Candidate Experience Adapter.

Ingests authentic vacancies from enterprise employers operating Oracle Cloud HCM recruitment portals.
Supported endpoints:
- REST API: https://{tenant}.fa.{region}.ocs.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions?expand=all&limit={limit}&offset={offset}
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

class OracleRecruitingAdapter(SourceAdapter):
    """Adapter for Oracle Recruiting Cloud (ORC) career portals."""

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        endpoint = config.get("api_url") or config.get("endpoint") or config.get("tenant")
        return bool(endpoint)

    def fetch_page(
        self, source_url: str, config: Dict[str, Any], checkpoint: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], bool]:
        api_url = config.get("api_url")
        if not api_url and source_url:
            if "hcmRestApi" in source_url:
                api_url = source_url
            else:
                match = re.search(r"https?://([a-zA-Z0-9_\-]+)\.(fa\.[a-zA-Z0-9_\-]+\.ocs\.oraclecloud\.com)", source_url)
                if match:
                    tenant = match.group(1)
                    host = match.group(2)
                    api_url = f"https://{tenant}.{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"

        if not api_url:
            tenant = config.get("tenant") or config.get("board_id")
            region = config.get("region", "us2")
            if tenant:
                api_url = f"https://{tenant}.fa.{region}.ocs.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
            else:
                raise ValueError(f"Oracle Recruiting API URL or tenant must be configured (url={source_url})")

        checkpoint = checkpoint or {}
        offset = int(checkpoint.get("offset", 0))
        limit = min(int(config.get("limit", 25)), 50)

        query_url = f"{api_url}?expand=all&limit={limit}&offset={offset}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }

        try:
            with httpx.Client(timeout=20.0, follow_redirects=True) as client:
                resp = client.get(query_url, headers=headers)
                if resp.status_code == 404:
                    return [], {"offset": offset, "completed": True}, True
                resp.raise_for_status()

                data = resp.json()
                raw_jobs = data.get("items", [])
                has_more = data.get("hasMore", len(raw_jobs) >= limit)

                new_checkpoint = {
                    "offset": offset + len(raw_jobs),
                    "completed": not has_more,
                    "total_found": data.get("count", len(raw_jobs)),
                }
                return raw_jobs, new_checkpoint, not has_more

        except httpx.HTTPStatusError as e:
            if e.response.status_code in (404, 410):
                return [], {"offset": offset, "completed": True}, True
            raise

    def parse_and_normalize(self, raw_record: Dict[str, Any]) -> Optional[NormalizedJob]:
        title = raw_record.get("Title") or raw_record.get("title") or "Unknown Title"
        title = html.unescape(title).strip()

        ext_id = str(raw_record.get("Id") or raw_record.get("JobRequisitionId") or "")
        app_url = raw_record.get("ExternalURL") or raw_record.get("application_url") or ""

        loc_str = raw_record.get("PrimaryLocation") or raw_record.get("Location") or ""
        norm_loc, city, region, country, c_code, remote_type = normalize_location_full(loc_str)

        desc = raw_record.get("ShortDescriptionStr") or raw_record.get("Description") or f"{title} vacancy."
        desc = clean_html_markup(desc)

        return NormalizedJob(
            external_job_id=ext_id or f"oracle-{abs(hash(title + app_url))}",
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
            application_url=app_url or f"https://oracle.cloud/jobs/{ext_id}",
            posting_date=datetime.now(timezone.utc),
            raw_data=raw_record,
        )

    def normalize(self, raw_job: Dict[str, Any], company_name: str, source_id: int) -> NormalizedJob:
        raw_job["company_name"] = company_name
        return self.parse_and_normalize(raw_job)
