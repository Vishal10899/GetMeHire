import httpx
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from bs4 import BeautifulSoup
from app.ingestion.base import SourceAdapter, NormalizedJob
from app.ingestion.normalizer import normalize_location_and_country

class AshbyAdapter(SourceAdapter):
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        return bool(config.get("board_name") or config.get("board_url"))

    def fetch_page(self, source_url: str, config: Dict[str, Any], checkpoint: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any], bool]:
        board_name = config.get("board_name")
        if not board_name and source_url:
            parts = source_url.rstrip("/").split("/")
            board_name = parts[-1]

        api_url = f"https://api.ashbyhq.com/posting-api/job-board/{board_name}"
        headers = {"User-Agent": "JobDiscoveryPlatform/2.0"}

        with httpx.Client(timeout=15.0) as client:
            resp = client.get(api_url, headers=headers)
            if resp.status_code == 429:
                raise Exception("Rate limit exceeded (HTTP 429)")
            resp.raise_for_status()
            data = resp.json()

        jobs_list = data.get("jobs", [])
        return jobs_list, {"completed": True}, False

    def parse_and_normalize(self, raw_record: Dict[str, Any]) -> Optional[NormalizedJob]:
        try:
            external_id = str(raw_record.get("id"))
            title = raw_record.get("title", "").strip()
            if not external_id or not title:
                return None

            html_desc = raw_record.get("descriptionHtml", "")
            soup = BeautifulSoup(html_desc, "html.parser")
            clean_desc = soup.get_text(separator="\n").strip()

            location_str = raw_record.get("location")
            is_remote = raw_record.get("isRemote", False)
            norm_loc, city, region, country, detected_remote = normalize_location_and_country(location_str, title)
            remote_type = "REMOTE" if is_remote or detected_remote == "REMOTE" else detected_remote

            department = raw_record.get("department")
            app_url = raw_record.get("jobUrl") or f"https://jobs.ashbyhq.com/{external_id}"

            published_at = raw_record.get("publishedAt")
            posting_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00")) if published_at else datetime.utcnow()

            # Compensation if provided
            comp = raw_record.get("compensation", {})
            salary_min = comp.get("minValue")
            salary_max = comp.get("maxValue")
            currency = comp.get("currency", "USD")

            keywords_to_check = ["python", "react", "typescript", "golang", "ruby", "next.js", "kubernetes", "cloud", "ai", "machine learning"]
            matched_skills = [k.capitalize() for k in keywords_to_check if k in clean_desc.lower() or k in title.lower()]

            return NormalizedJob(
                external_job_id=external_id,
                title=title,
                description=clean_desc if clean_desc else title,
                department=department,
                location=norm_loc,
                city=city,
                region=region,
                country=country,
                remote_type=remote_type,
                employment_type="FULL_TIME",
                experience_level="LEAD" if "lead" in title.lower() else ("SENIOR" if "senior" in title.lower() else "MID"),
                skills=matched_skills,
                salary_min=salary_min,
                salary_max=salary_max,
                salary_currency=currency,
                posting_date=posting_dt,
                application_url=app_url,
                raw_data=raw_record
            )
        except Exception:
            return None
