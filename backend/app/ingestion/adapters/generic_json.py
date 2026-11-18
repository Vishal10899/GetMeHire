import httpx
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from app.ingestion.base import SourceAdapter, NormalizedJob

class GenericJsonAdapter(SourceAdapter):
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        return True

    def fetch_page(self, source_url: str, config: Dict[str, Any], checkpoint: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any], bool]:
        url = config.get("endpoint_url") or source_url
        headers = {"User-Agent": "JobDiscoveryPlatform/2.0"}

        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        jobs_list = []
        if isinstance(data, list):
            jobs_list = data
        elif isinstance(data, dict):
            # check common keys
            for key in ["jobs", "data", "postings", "items", "results"]:
                if key in data and isinstance(data[key], list):
                    jobs_list = data[key]
                    break

        return jobs_list, {"completed": True}, False

    def parse_and_normalize(self, raw_record: Dict[str, Any]) -> Optional[NormalizedJob]:
        try:
            external_id = str(raw_record.get("id") or raw_record.get("job_id") or raw_record.get("slug"))
            title = (raw_record.get("title") or raw_record.get("position") or "").strip()
            if not external_id or not title:
                return None

            desc = raw_record.get("description") or raw_record.get("summary") or title
            
            loc_data = raw_record.get("location")
            if isinstance(loc_data, dict):
                loc = loc_data.get("name") or loc_data.get("city") or "Worldwide"
            else:
                loc = loc_data or raw_record.get("city") or "Worldwide"

            app_url = (
                raw_record.get("url") or 
                raw_record.get("application_url") or 
                raw_record.get("apply_url") or 
                raw_record.get("absolute_url") or 
                raw_record.get("link") or 
                raw_record.get("hostedUrl") or
                f"https://example.com/jobs/{external_id}"
            )
            
            remote = "ONSITE"
            if raw_record.get("remote") or "remote" in title.lower() or "remote" in str(loc).lower():
                remote = "REMOTE"

            return NormalizedJob(
                external_job_id=external_id,
                title=title,
                description=desc,
                location=str(loc),
                remote_type=remote,
                employment_type=raw_record.get("employment_type", "FULL_TIME"),
                skills=raw_record.get("skills", []),
                application_url=app_url,
                raw_data=raw_record
            )
        except Exception:
            return None
